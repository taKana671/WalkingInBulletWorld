from enum import Enum, auto
from typing import NamedTuple

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, LColor

from utils import create_line_node
from mask_manager import Mask, MultiMask


class Motions(Enum):

    FORWARD = auto()
    BACKWARD = auto()
    LEFT = auto()
    RIGHT = auto()
    TURN = auto()
    STOP = auto()


class Status(Enum):

    MOVING = auto()
    GOING_UP = auto()
    GOING_DOWN = auto()
    TRANSFER = auto()
    SLIP = auto()
    WATCH_STEPS = auto()


class Lift:

    __slots__ = ('lift', 'dest', 'lift_original_z', 'dest_z', 'speed')

    def __init__(self, lift, dest):
        self.lift = lift
        self.dest = dest
        self.lift_original_z = self.lift.get_z()
        self.dest_z = self.dest.get_z()
        self.speed = 5

    def up(self, dt):
        if (z := self.lift.get_z() + dt * self.speed) > self.dest_z:
            self.lift.set_z(self.dest_z)
            return True
        self.lift.set_z(z)

    def down(self):
        self.lift.set_z(self.lift_original_z)

    def get_angular_difference(self):
        return abs(self.dest.get_h() - self.lift.get_h())


class Steps(NamedTuple):

    fall_start_z: float
    start: NodePath
    dest: NodePath = None

    def get_angular_difference(self):
        if self.dest is not None:
            return abs(self.start.get_h() - self.dest.get_h())


class Walker(NodePath):

    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        super().__init__(BulletRigidBodyNode('character'))
        self.world = world

        h, w = 6, 1.2
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        self.node().add_shape(shape)
        self.node().set_kinematic(True)

        self.node().set_ccd_motion_threshold(1e-7)
        self.node().set_ccd_swept_sphere_radius(0.6)
        self.set_collide_mask(MultiMask.walker)
        self.set_pos(Point3(25, -10, 0.5))
        self.set_scale(0.5)

        self.reparent_to(base.render)
        self.world.attach(self.node())

        self.direction_nd = NodePath(PandaNode('direction'))
        self.direction_nd.set_h(180)
        self.direction_nd.reparent_to(self)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))
        self.actor.set_name('ralph')
        self.actor.reparent_to(self.direction_nd)
        self.actor_h = 1.4

        self.front = NodePath('front')
        self.front.reparent_to(self.direction_nd)
        self.front.set_pos(0, -1, 1)

        self.back = NodePath('back')
        self.back.reparent_to(self.direction_nd)
        self.back.set_pos(0, 1, 1)

        self.state = Status.MOVING
        self.elapsed_time = 0
        self.draw_debug_lines()
        self.test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.2))

    def draw_debug_lines(self):
        """Draw ray cast lines for dubug.
        """
        red = LColor(1, 0, 0, 1)
        blue = LColor(0, 0, 1, 1)

        self.debug_lines = [
            create_line_node(pos := self.front.get_pos(), Point3(pos.xy, -10), blue),
            create_line_node(Point3(0, 0, 0), Point3(0, 0, -10), red),
            create_line_node(pos := self.back.get_pos(), Point3(pos.xy, -10), blue),
        ]

    def toggle_debug(self):
        for line in self.debug_lines:
            if line.has_parent():
                line.detach_node()
                continue
            line.reparent_to(self.direction_nd)

    def navigate(self):
        """Return a relative point to enable camera to follow the character
           when the camera's view is blocked by an object like wall.
        """
        return self.get_relative_point(self.direction_nd, Vec3(0, 10, 2))

    def detect_collision(self):
        if self.world.contact_test(
                self.node(), use_filter=True).get_num_contacts() > 0:
            return True

    def predict_collision(self, from_pos, to_pos, mask):
        ts_from = TransformState.make_pos(from_pos + Vec3(0, 0, 0.1))
        ts_to = TransformState.make_pos(to_pos + Vec3(0, 0, 0.1))

        if (result := self.world.sweep_test_closest(
                self.test_shape, ts_from, ts_to, mask, 0.0)).has_hit():
            return result

    def move(self, forward_vector, direction, dt):
        current_pos = self.get_pos()

        # Cannot move, if out of terrain.
        if not (forward := self.check_forward(direction, current_pos)) or \
                not (below := self.check_below(current_pos)):
            return None

        # Change just z, if no key input. 
        if not direction:
            z = below.get_hit_pos().z + self.actor_h
            self.set_z(z)
            return None

        f_hit_pos = forward.get_hit_pos()
        b_hit_pos = below.get_hit_pos()
        diff_z = abs(b_hit_pos.z - f_hit_pos.z)

        # Go up, if up stairs is found in the direction of movement and lift is embedded just below.
        if f_hit_pos.z > b_hit_pos.z and 0.3 < diff_z < 1.2:
            if lift := self.can_use_lift(f_hit_pos, current_pos):
                self.lift = Lift(NodePath(lift.get_node()), NodePath(forward.get_node()))
                return Status.GOING_UP

        speed = 10 if direction < 0 else 5
        next_pos = current_pos + forward_vector * direction * speed * dt

        # Cannot move if collision with something in the direction of movement is detected, or
        # go down if that with dynamic body is detected.
        if self.detect_collision():
            if result := self.predict_collision(current_pos, next_pos, Mask.predict):
                if result.get_node().get_mass() > 0:
                    self.steps = Steps(current_pos.z, NodePath(below.get_node()))
                    return Status.SLIP
                return None

        if f_hit_pos.z < b_hit_pos.z:
            forward_pos = f_hit_pos + Vec3(0, 0, self.actor_h)

            # Go down, if down stairs and embedded lift are found in the direction of movement.
            if 0.5 <= diff_z < 1.2 and self.check_below(forward_pos, Mask.lift):
                self.steps = Steps(current_pos.z, NodePath(below.get_node()), NodePath(forward.get_node()))
                return Status.WATCH_STEPS
            # Fall
            elif diff_z >= 1.:
                self.steps = Steps(current_pos.z, NodePath(below.get_node()))
                self.set_pos(next_pos)
                return Status.WATCH_STEPS

        next_hit = self.check_below(next_pos)
        next_pos.z = next_hit.get_hit_pos().z + self.actor_h
        self.set_pos(next_pos)

    def can_use_lift(self, f_hit_pos, current_pos):
        if lift := self.check_below(current_pos, Mask.lift):
            from_pos = Point3(current_pos.xy, f_hit_pos.z + self.actor_h)
            to_pos = Point3(f_hit_pos.xy, f_hit_pos.z + self.actor_h)

            if not self.predict_collision(from_pos, to_pos, Mask.sweep):
                return lift

    def parse_inputs(self, inputs):
        direction = 0
        angle = 0
        motion = Motions.STOP

        if Motions.LEFT in inputs:
            angle += 100
            motion = Motions.TURN
        if Motions.RIGHT in inputs:
            angle -= 100
            motion = Motions.TURN
        if Motions.FORWARD in inputs:
            direction += -1
            motion = Motions.FORWARD
        if Motions.BACKWARD in inputs:
            direction += 1
            motion = Motions.BACKWARD

        return direction, angle, motion

    def update(self, dt, inputs):
        forward_vector = self.direction_nd.get_quat(base.render).get_forward()

        match self.state:
            case Status.MOVING:
                direction, angle, motion = self.parse_inputs(inputs)

                if angle:
                    self.turn(angle * dt)

                if status := self.move(forward_vector, direction, dt):
                    self.last_direction = direction
                    self.state = status

            case Status.GOING_UP:
                motion = None
                if self.go_up(dt):
                    self.state = Status.TRANSFER

            case Status.TRANSFER:
                motion = None
                if self.transfer(forward_vector, dt):
                    self.state = Status.MOVING

            case Status.WATCH_STEPS:
                motion = None
                if status := self.watch_steps(forward_vector, dt):
                    self.state = status

            case Status.GOING_DOWN:
                motion = None
                if self.go_down(dt):
                    self.state = Status.MOVING

            case Status.SLIP:
                motion = Motions.STOP
                if self.go_down(dt, upside_down=True):
                    self.state = Status.MOVING

        self.play_anim(motion)

    def check_below(self, from_pos, mask=Mask.ground, upside_down=False):
        to_pos = from_pos + Vec3(0, 0, -20)

        if upside_down:
            from_pos, to_pos = to_pos, from_pos

        if (result := self.world.ray_test_closest(from_pos, to_pos, mask)).has_hit():
            return result

    def check_forward(self, direction, pos, mask=Mask.ground):
        np = self.front if direction < 0 else self.back
        from_pos = np.get_pos(self) + pos
        return self.check_below(from_pos, mask)

    def check_backward(self, direction, mask=Mask.ground):
        np = self.back if direction < 0 else self.front
        from_pos = np.get_pos(self) + self.get_pos()
        return self.check_below(from_pos, mask)

    def turn(self, angle):
        self.direction_nd.set_h(self.direction_nd.get_h() + angle)

    def go_up(self, dt):
        """Raise a lift embedded in the step to help Ralph to go up stairs.
        """
        result = self.lift.up(dt)
        below = self.check_below(self.get_pos(), Mask.lift)
        self.set_z(below.get_hit_pos().z + self.actor_h)
        return result

    def transfer(self, forward_vector, dt):
        current_pos = self.get_pos()
        below = self.check_below(current_pos)

        if below.get_node() == self.lift.dest.node():
            # change angle, for when going up spiral stairs.
            if 0 < (diff := self.lift.get_angular_difference()) <= 30:
                h = self.direction_nd.get_h() + diff
                self.direction_nd.set_h(h)

            self.lift.down()
            return True

        next_pos = current_pos + forward_vector * self.last_direction * 4 * dt
        self.set_pos(next_pos)

    def watch_steps(self, forward_vector, dt):
        current_pos = self.get_pos()
        next_pos = current_pos + forward_vector * self.last_direction * 5 * dt

        if self.predict_collision(current_pos, next_pos, Mask.sweep):
            return Status.MOVING

        self.set_pos(next_pos)

        if self.world.contact_test_pair(
                self.node(), self.steps.start.node()).get_num_contacts():
            return None

        if self.steps.dest:
            if 0 < (diff := self.steps.get_angular_difference()) <= 30:
                self.direction_nd.set_h(self.direction_nd.get_h() - diff)
            return Status.GOING_DOWN
        return Status.SLIP

    def go_down(self, dt, upside_down=False):
        next_z = 0.25 * -9.81 * (self.elapsed_time ** 2) + self.steps.fall_start_z
        below = self.check_below(self.get_pos(), upside_down=upside_down)

        if abs(next_z - (dest_z := below.get_hit_pos().z)) < self.actor_h:
            self.set_z(dest_z + self.actor_h)
            self.elapsed_time = 0
            return True

        self.set_z(next_z)
        self.elapsed_time += dt

    def play_anim(self, motion):
        """Play animation. If motion is None,
           the animation depends on self.last_direction.
        """
        match motion:
            case Motions.FORWARD:
                anim = Walker.RUN
                rate = 1

            case Motions.BACKWARD:
                anim = Walker.WALK
                rate = -1

            case Motions.TURN:
                anim = Walker.WALK
                rate = 1

            case Motions.STOP:
                if self.actor.get_current_anim() is not None:
                    self.actor.stop()
                    self.actor.pose(Walker.WALK, 5)
                return

            case _:
                if self.last_direction < 0:
                    anim = Walker.RUN
                    rate = 1
                elif self.last_direction > 0:
                    anim = Walker.WALK
                    rate = -1

        if self.actor.get_current_anim() != anim:
            self.actor.loop(anim)
            self.actor.set_play_rate(rate, anim)
from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode, BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, LColor, BitMask32

from utils import create_line_node


class Status(Enum):

    MOVING = auto()
    LIFTING = auto()
    LANDING = auto()


class Walker(NodePath):
    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        # h, w = 6, 1.5
        h, w = 6, 1.2
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 1.0, 'character'))  # 0.4
        self.world = world
        self.set_collide_mask(BitMask32.allOn())
        self.set_pos(Point3(25, -10, 1))
        # self.set_pos(Point3(-94.305, 68.8304, 0.23398))
        self.set_scale(0.5)
        self.reparent_to(base.render)
        self.world.attach_character(self.node())

        self.direction_node = NodePath(PandaNode('direction'))
        self.direction_node.reparent_to(self)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))  # -3
        self.actor.set_name('ralph')
        self.actor.reparent_to(self.direction_node)
        self.direction_node.set_h(180)

        self.front = NodePath('front')
        self.front.reparent_to(self.direction_node)
        # self.front.set_pos(0, -1.5, 1)
        self.front.set_pos(0, -1.2, 1)

        self.under = NodePath('under')
        self.under.reparent_to(self.direction_node)
        # self.under.set_pos(0, -1.5, -10)
        self.under.set_pos(0, -1.2, -10)

        self.shape = shape
        self.state = Status.MOVING
        self.frame_cnt = 0

        blue_line = create_line_node(self.front.get_pos(), self.under.get_pos(), LColor(0, 0, 1, 1))
        self.debug_line_front = NodePath(blue_line)
        red_line = create_line_node(Point3(0, 0, 0), Point3(0, 0, -10), LColor(1, 0, 0, 1))
        self.debug_line_center = NodePath(red_line)

    def toggle_debug(self):
        if self.debug_line_front.has_parent():
            self.debug_line_front.detach_node()
            self.debug_line_center.detach_node()
        else:
            self.debug_line_front.reparent_to(self.direction_node)
            self.debug_line_center.reparent_to(self)

    def navigate(self):
        """Return a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.get_relative_point(self.direction_node, Vec3(0, 10, 2))

    def current_location(self, mask=BitMask32.all_on()):
        """Cast a ray vertically from the center of Ralph to return BulletRayHit.
        """
        below = base.render.get_relative_point(self, Vec3(0, 0, -10))
        ray_result = self.world.ray_test_closest(self.get_pos(), below, mask)

        if ray_result.has_hit():
            return ray_result
        return None

    def watch_steps(self, mask):
        """Cast a ray vertically from the front of Ralph's face to find steps.
           If found, BulletRayHit is returned.
        """
        from_pos = self.front.get_pos(self) + self.get_pos()
        to_pos = self.under.get_pos(self) + self.get_pos()
        ray_result = self.world.ray_test_closest(from_pos, to_pos, mask)

        if ray_result.has_hit():
            # contact_result = self.world.contact_test_pair(self.node(), ray_result.get_node())
            # if contact_result.get_num_contacts() > 0:
                # return ray_result
            return ray_result
        return None

    # def find_obstacles(self, next_pos, mask=BitMask32.bit(2)):
        # ts_from = TransformState.make_pos(self.get_pos())
        # ts_to = TransformState.make_pos(next_pos)
        # result = self.world.sweep_test_closest(self.node().get_shape(), ts_from, ts_to, mask, 0.0)

        # if result.hasHit():
        #     print(result.get_node().get_name(), 'pos', self.get_pos(), 'next', next_pos)
        #     if result.get_node() != self.node():
        #         return True

    def move(self, dt, distance, angle):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        next_pos = self.get_pos() + orientation * distance

        # if self.find_obstacles(next_pos):
        #     pass
        #     # return

        match self.state:
            case Status.MOVING:
                if angle:
                    self.turn(angle)
                if distance < 0:
                    if not self.go_forward(next_pos):
                        self.state = Status.LIFTING
                if distance > 0:
                    self.go_back(next_pos)

            case Status.LIFTING:
                if self.lift_up(dt):
                    self.state = Status.LANDING

            case Status.LANDING:
                if self.land(orientation, dt):
                    self.frame_cnt = 0
                    self.state = Status.MOVING

        # anim = None
        # rate = 1

        # if self.state == StatusinputState.is_set('forward'):
        #     anim = self.walker.RUN
        # elif inputState.is_set('backward'):
        #     anim, rate = self.walker.WALK, -1
        # elif inputState.is_set('left') or inputState.is_set('right'):
        #     anim = self.walker.WALK

        # self.walker.play_anim(anim, rate)

    def go_forward(self, next_pos):
        """Make Ralph go forward.
           Args:
                next_pos: Vec3
        """
        if (below := self.current_location(BitMask32.bit(1))) and \
                (front := self.watch_steps(BitMask32.bit(1))):

            diff = (front.get_hit_pos() - below.get_hit_pos()).z

            if 0.3 < diff < 1.2:
                if lift := self.current_location(BitMask32.bit(4)):
                    self.lift = NodePath(lift.get_node())
                    self.lift_original_z = self.lift.get_z()
                    self.dest = NodePath(front.get_node())
                    return False

        if self.node().is_on_ground():
            self.setPos(next_pos)
        return True

    def go_back(self, next_pos):
        if self.node().is_on_ground():
            self.set_pos(next_pos)

    def turn(self, angle):
        self.direction_node.set_h(self.direction_node.get_h() + angle)

    def lift_up(self, dt):
        """Raise an invisible lift embedded in the steps.
        """
        if (next_z := self.lift.get_z() + dt * 5) > self.dest.get_z():
            self.lift.set_z(self.dest.get_z())
            return True
        else:
            self.lift.set_z(next_z)

    def land(self, orientation, dt):
        """Make Ralph move from the invisible lift to the destination.
           Args:
                orientation: LVector3f
                dt: float
        """
        self.frame_cnt += 1
        if self.frame_cnt >= 4:
            print('time out')
            self.lift.set_z(self.lift_original_z)
            return True

        next_pos = self.get_pos() + orientation * -20 * dt
        self.set_pos(next_pos)

        if below := self.current_location(BitMask32.bit(1)):
            if below.get_node() == self.dest.node():
                self.lift.set_z(self.lift_original_z)

                # # print('lift_hpr', self.lift.get_hpr(), 'dest_hpr', self.dest.get_hpr())
                # diff = self.dest.get_h() - self.lift.get_h()
                # if diff:
                #     self.direction_node.set_h(self.direction_node.get_h() + diff)

                return True

    def play_anim(self, command, rate=1):
        if not command:
            self.stop_anim()
        else:
            if self.actor.get_current_anim() != command:
                self.actor.loop(command)
                self.actor.set_play_rate(rate, command)

    def stop_anim(self):
        if self.actor.get_current_anim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)
from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, LColor, BitMask32

from utils import create_line_node


class Status(Enum):

    MOVING = auto()
    GOING_UP = auto()
    GETTING_OFF = auto()
    GOING_DOWN = auto()
    COMMING_TO_EDGE = auto()


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

        self.state = Status.MOVING
        self.frame_cnt = 0

        self.debug_line_front = create_line_node(self.front.get_pos(), self.under.get_pos(), LColor(0, 0, 1, 1))
        self.debug_line_center = create_line_node(Point3(0, 0, 0), Point3(0, 0, -10), LColor(1, 0, 0, 1))

    def toggle_debug(self):
        if self.debug_line_front.has_parent():
            self.debug_line_front.detach_node()
            self.debug_line_center.detach_node()
        else:
            self.debug_line_front.reparent_to(self.direction_node)
            self.debug_line_behind.reparent_to(self.direction_node)

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

    def watch_front(self, mask):
        """Cast a ray vertically from the front of Ralph's face to find steps.
           If found, BulletRayHit is returned.
        """
        from_pos = self.front.get_pos(self) + self.get_pos()
        to_pos = self.under.get_pos(self) + self.get_pos()
        ray_result = self.world.ray_test_closest(from_pos, to_pos, mask)

        if ray_result.has_hit():
            return ray_result
        return None

    def watch_behind(self, mask):
        from_pos = self.behind.get_pos(self) + self.get_pos()
        to_pos = base.render.get_relative_point(self, Vec3(0, 1.2, -10))
        ray_result = self.world.ray_test_closest(from_pos, to_pos, mask)

        if ray_result.has_hit():
            return ray_result
        return None

    def update(self, dt, direction, angle):
        orientation = self.direction_node.get_quat(base.render).get_forward()

        if self.state == Status.MOVING:
            if angle:
                self.turn(angle)

            if direction < 0:
                if not self.find_steps():
                    self.move(orientation, direction * 10 * dt)
            if direction > 0:
                self.move(orientation, direction * 5 * dt)

        if self.state == Status.GOING_UP:
            self.go_up_on_lift(5 * dt)

        if self.state == Status.GETTING_OFF:
            self.get_off_lift(orientation, -20 * dt)

        if self.state == Status.COMMING_TO_EDGE:
            self.come_to_edge(orientation, -20 * dt)

        if self.state == Status.GOING_DOWN:
            self.go_down(orientation, 5 * dt)

    def find_steps(self):
        if (below := self.current_location(BitMask32.bit(1))) and \
                (front := self.watch_front(BitMask32.bit(1))):

            z_diff = (front.get_hit_pos() - below.get_hit_pos()).z

            # Ralph is likely to go down stairs.
            if -1.2 <= z_diff <= -0.5:
                self.start = NodePath(below.get_node())
                self.dest = NodePath(front.get_node())
                self.state = Status.COMMING_TO_EDGE
                return True

            # Ralph is likely to go up stairs.
            if 0.3 < z_diff < 1.2:
                if lift := self.current_location(BitMask32.bit(4)):
                    self.lift = NodePath(lift.get_node())
                    self.lift_original_z = self.lift.get_z()
                    self.dest = NodePath(front.get_node())
                    self.state = Status.GOING_UP
                    return True

    def move(self, orientation, distance):
        if self.node().is_on_ground():
            next_pos = self.get_pos() + orientation * distance
            self.set_pos(next_pos)

    def turn(self, angle):
        self.direction_node.set_h(self.direction_node.get_h() + angle)

    def go_up_on_lift(self, distance):
        """Raise a lift embedded in the step on which Ralph is to the height of the next step.
        """
        if (next_z := self.lift.get_z() + distance) > self.dest.get_z():
            self.lift.set_z(self.dest.get_z())
            self.state = Status.GETTING_OFF
        else:
            self.lift.set_z(next_z)

    def get_off_lift(self, orientation, distance):
        """Make Ralph on the invisible lift move to the destination.
           Args:
                orientation: (LVector3f)
                distance: (float)
        """
        get_off = False
        next_pos = self.get_pos() + orientation * distance
        self.set_pos(next_pos)
        self.frame_cnt += 1

        if below := self.current_location(BitMask32.bit(1)):
            if below.get_node() == self.dest.node():
                get_off = True

                # change direction right after get off the lift, for when going up spiral stairs.
                if 0 < (diff := self.dest.get_h() - self.lift.get_h()) <= 30:
                    self.direction_node.set_h(self.direction_node.get_h() + diff)

        if get_off or self.frame_cnt >= 5:
            self.lift.set_z(self.lift_original_z)
            self.frame_cnt = 0
            self.state = Status.MOVING

    def come_to_edge(self, orientation, distance):
        """Make Ralph move to the edge of steps.
           Args:
                orientation: (LVector3f)
                distance: (float)
        """
        next_pos = self.get_pos() + orientation * distance
        self.set_pos(next_pos)
        self.frame_cnt += 1
        on_edge = False

        if below := self.current_location(BitMask32.bit(1)):
            if below.get_node() == self.dest.node():
                on_edge = True

                # change direction right  before the start of falling, for when going down spiral stairs.
                if -30 <= (diff := self.dest.get_h() - self.start.get_h()) < 0:
                    self.direction_node.set_h(self.direction_node.get_h() + diff)

        if on_edge or self.frame_cnt >= 5:
            self.frame_cnt = 0
            self.state = Status.GOING_DOWN

    def go_down(self, orientation, distance):
        """Wait that Ralph gravitates downwards to collide the destination.
        """
        self.set_z(self.get_z() - distance)
        self.frame_cnt += 1

        if self.frame_cnt >= 20 or \
                self.world.contact_test_pair(self.node(), self.dest.node()).get_num_contacts() > 0:
            self.frame_cnt = 0
            self.state = Status.MOVING

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
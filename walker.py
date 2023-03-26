from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, BitMask32

from utils import Cube


class DebugCube(NodePath):

    def __init__(self, name, cube, color):
        super().__init__(PandaNode(name))
        self.cube = cube.copy_to(self)
        self.cube.reparent_to(self)
        self.set_scale(0.15, 0.15, 0.15)
        self.set_hpr(45, 45, 45)
        self.set_color(color)


class Walker(NodePath):
    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
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

        self.right_eye = self.actor.expose_joint(None, 'modelRoot', 'RightEyeLid')
        self.left_eye = self.actor.expose_joint(None, 'modelRoot', 'LeftEyeLid')

        # the point at which the right eye looks
        self.front_right = NodePath('frontRight')
        self.front_right.reparent_to(self.direction_node)
        self.front_right.set_pos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparent_to(self.direction_node)
        self.front_left.set_pos(0.3, -2, -2.7)

        self.debug_right = None
        self.debug_left = None

    def toggle_debug(self):
        if not self.debug_right:
            cube = Cube.make()
            self.debug_right = DebugCube('right', cube, (1, 0, 0, 1))  # Red
            self.debug_left = DebugCube('left', cube, (0, 0, 1, 1))  # Blue

        if self.debug_right.has_parent():
            self.debug_right.detach_node()
            self.debug_left.detach_node()
        else:
            self.debug_right.reparent_to(self.front_right)
            self.debug_left.reparent_to(self.front_left)

    def navigate(self):
        """Returns a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.get_relative_point(self.direction_node, Vec3(0, 10, 2))

    def get_rayhit(self, result):
        for hit in result.get_hits():
            if hit.get_node() != self.node():
                return hit
        return None

    def current_location(self):
        below = base.render.get_relative_point(self, Vec3(0, 0, -3))
        result = self.world.ray_test_all(self.get_pos(), below)
        return self.get_rayhit(result)

    def watch_steps(self):
        right_eye = self.right_eye.get_pos() + self.get_pos()
        front_right = self.front_right.get_pos(self) + self.get_pos()
        right_result = self.world.ray_test_all(right_eye, front_right, BitMask32.bit(2))

        left_eye = self.left_eye.get_pos() + self.get_pos()
        front_left = self.front_left.get_pos(self) + self.get_pos()
        left_result = self.world.ray_test_all(left_eye, front_left, BitMask32.bit(2))

        if (right_hit := self.get_rayhit(right_result)) and \
                (lelt_hit := self.get_rayhit(left_result)):
            if right_hit.get_node() == lelt_hit.get_node():
                return right_hit
        return None

    def go_forward(self, dist):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        next_pos = self.get_pos() + orientation * dist

        if below_hit := self.current_location():
            if forward_hit := self.watch_steps():
                below_height = below_hit.get_hit_pos().z
                forward_height = forward_hit.get_hit_pos().z

                if 0.5 < (diff := forward_height - below_height) < 1.2:
                    next_pos.z += diff
        self.set_pos(next_pos)

    def go_back(self, dist):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        self.set_pos(self.get_pos() + orientation * dist)

    def turn(self, angle):
        self.direction_node.set_h(self.direction_node.get_h() + angle)

    def play_anim(self, command, rate=1):
        if self.actor.get_current_anim() != command:
            self.actor.loop(command)
            self.actor.set_play_rate(rate, command)

    def stop_anim(self):
        if self.actor.get_current_anim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)
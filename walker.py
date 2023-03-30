from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, BitMask32

from utils import Cube


class Status(Enum):

    MOVING = auto()
    LIFT_UP = auto()
    LIFT_DOWN = auto()


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
        # h, w = 6, 1.5
        h, w = 6, 1.2
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 1.0, 'character'))
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
        # self.front_right.set_pos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparent_to(self.direction_node)
        # self.front_left.set_pos(0.3, -2, -2.7)

        self.front = NodePath('front')
        self.front.reparent_to(self.direction_node)
        # self.front.set_pos(0, -1.5, 1)
        self.front.set_pos(0, -1.2, 1)

        self.under = NodePath('under')
        self.under.reparent_to(self.direction_node)
        # self.under.set_pos(0, -1.5, -10)
        self.under.set_pos(0, -1.2, -10)

        self.state = Status.MOVING
        self.is_jumping = False
        self.debug_right = None
        self.debug_left = None

    def toggle_debug(self):
        if not self.debug_right:
            cube = Cube.make()
            self.debug_right = DebugCube('right', cube, (1, 0, 0, 1))  # Red
            self.debug_left = DebugCube('left', cube, (0, 0, 1, 1))    # Blue
            self.debug_front = DebugCube('front', cube, (0, 0, 1, 1))    # Blue

        if self.debug_right.has_parent():
            self.debug_right.detach_node()
            self.debug_left.detach_node()
            self.debug_front.detach_node()
        else:
            self.debug_right.reparent_to(self.front_right)
            self.debug_left.reparent_to(self.front_left)
            self.debug_front.reparent_to(self.front)

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

    # def current_location(self):
    #     below = base.render.get_relative_point(self, Vec3(0, 0, -3))
    #     result = self.world.ray_test_all(self.get_pos(), below)
    #     return self.get_rayhit(result)

    def current_location(self, mask=BitMask32.all_on()):
        below = base.render.get_relative_point(self, Vec3(0, 0, -10))
        ray_result = self.world.ray_test_all(self.get_pos(), below, mask)

        if ray_result.has_hits():
            below_hit = max((hit for hit in ray_result.get_hits()), key=lambda x: x.get_hit_pos().z)
            return below_hit

    # def watch_steps(self):
        # right_eye = self.right_eye.get_pos() + self.get_pos()
        # front_right = self.front_right.get_pos(self) + self.get_pos()
        # right_result = self.world.ray_test_all(right_eye, front_right, BitMask32.bit(2))

        # left_eye = self.left_eye.get_pos() + self.get_pos()
        # front_left = self.front_left.get_pos(self) + self.get_pos()
        # left_result = self.world.ray_test_all(left_eye, front_left, BitMask32.bit(2))

        # if (right_hit := self.get_rayhit(right_result)) and \
        #         (lelt_hit := self.get_rayhit(left_result)):
        #     if right_hit.get_node() == lelt_hit.get_node():
        #         return right_hit
        # return None

    def watch_steps(self, mask=BitMask32.bit(2)):
        from_pos = self.front.get_pos(self) + self.get_pos()
        to_pos = self.under.get_pos(self) + self.get_pos()
        ray_result = self.world.ray_test_all(from_pos, to_pos, mask)

        if ray_result.has_hits():
            ray_hit = max((hit for hit in ray_result.get_hits()), key=lambda x: x.get_hit_pos().z)
            contact_result = self.world.contact_test_pair(self.node(), ray_hit.get_node())

            if contact_result.get_num_contacts() > 0:
                return ray_hit

        return None

    def watch_steps2(self, mask=BitMask32.bit(2)):
        from_pos = self.front.get_pos(self) + self.get_pos()
        to_pos = self.under.get_pos(self) + self.get_pos()
        ray_result = self.world.ray_test_all(from_pos, to_pos, mask)

        if ray_result.has_hits():
            ray_hit = max((hit for hit in ray_result.get_hits()), key=lambda x: x.get_hit_pos().z)
            return ray_hit

        return None


    def get_lift_nd(self, mask=BitMask32.bit(4)):
        below = base.render.get_relative_point(self, Vec3(0, 0, -10))
        ray_result = self.world.ray_test_closest(self.get_pos(), below, mask)

        if ray_result.has_hit():
            return ray_result.get_node()

    def move(self, dt, distance, angle):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        next_pos = self.get_pos() + orientation * distance

        if self.state == Status.MOVING:
            if angle:
                self.turn(angle)

            if distance < 0:
                if below_hit := self.current_location():
                    diff = (self.get_pos() - below_hit.get_hit_pos()).z
                    if 1.8 < diff < 2.5:
                        if hit := self.watch_steps2(BitMask32.bit(4)):
                            self.lift = NodePath(hit.get_node())
                            self.lift_original_z = self.lift.get_z()
                            self.lift.set_z(self.lift.get_z() + 1.)
                            self.state = Status.LIFT_DOWN


                if (front_hit := self.watch_steps()) and (below_hit := self.current_location()):
                    print(front_hit.get_node().get_name())
                    diff = front_hit.get_hit_pos().z - below_hit.get_hit_pos().z
                    if 0.3 < diff < 1.2:
                        if lift_nd := self.get_lift_nd():
                            self.lift = NodePath(lift_nd)
                            self.lift_original_z = self.lift.get_z()
                            self.next_step = NodePath(front_hit.get_node())
                            self.lifting_height = NodePath(front_hit.get_node()).get_z()
                            self.state = Status.LIFT_UP
                            # return
                self.setPos(next_pos)

            if distance > 0:
                if self.node().is_on_ground():
                    self.set_pos(next_pos)

        elif self.state == Status.LIFT_UP:

            if self.lift.get_z() == self.lifting_height:
                next_pos = self.get_pos() + orientation * -10 * dt
                self.set_pos(next_pos)

                if below_hit := self.current_location(BitMask32.bit(2)):
                    print(below_hit.get_node(), self.next_step.node())
                    if below_hit.get_node() == self.next_step.node():
                        self.lift.set_z(self.lift_original_z)
                        self.state = Status.MOVING
            elif (next_z := self.lift.get_z() + dt * 5) > self.lifting_height:
                self.lift.set_z(self.lifting_height)
            else:
                self.lift.set_z(next_z)
        elif self.state == Status.LIFT_DOWN:

            if self.lift.get_z() == self.lift_original_z:
                self.state = Status.MOVING
            elif (next_z := self.lift.get_z() - dt * 5) < self.lift_original_z:
                self.lift.set_z(self.lift_original_z)
            else:
                self.lift.set_z(next_z)


    def go_forward(self, dist):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        next_pos = self.get_pos() + orientation * dist

        if not self.is_jumping:
            if (front_hit := self.watch_steps()) and (below_hit := self.current_location()):
                diff = front_hit.get_hit_pos().z - below_hit.get_hit_pos().z

                if 0.5 < diff < 1.2:
                    if lift_nd := self.get_lift_nd():
                        self.lift = NodePath(lift_nd)
                        self.lift_original_z = self.lift.get_z()
                        self.lifting_height = NodePath(front_hit.get_node()).get_z()
                        self.is_jumping = True
                        return
            self.setPos(next_pos)
        else:
            if self.lift.get_z() == self.lifting_height:
                self.lift.set_z(self.lift_original_z)
                self.is_jumping = False
            elif (next_z := self.lift.get_z() + 0.2) > self.lifting_height:
                self.lift.set_z(self.lifting_height)
            else:
                self.lift.set_z(next_z)
      
    # def go_forward(self, dist):
    #     orientation = self.direction_node.get_quat(base.render).get_forward()
    #     next_pos = self.get_pos() + orientation * dist

    #     if not self.is_jumping:
    #         from_pos = self.front.get_pos(self) + self.get_pos()
    #         to_pos = self.under.get_pos(self) + self.get_pos()
    #         result = self.world.ray_test_all(from_pos, to_pos, BitMask32.bit(2))
            
    #         if front_hits := sorted((hit for hit in result.get_hits()), key=lambda x: x.get_hit_pos().z, reverse=True):
    #             front_hit = front_hits[0]
    #             pair_result = self.world.contact_test_pair(self.node(), front_hit.get_node())
    #             if pair_result.get_num_contacts() > 0:
    #                 # print('front_hit', front_hit.get_node().get_name())
                    
    #                 below = base.render.get_relative_point(self, Vec3(0, 0, -10))
    #                 result = self.world.ray_test_all(self.get_pos(), below)
    #                 if below_hits := sorted((hit for hit in result.get_hits()), key=lambda x: x.get_hit_pos().z, reverse=True):
    #                     below_hit = below_hits[0]
    #                     print('below_hit', below_hit.get_node().get_name())
                
    #                     below_height = below_hit.get_hit_pos().z
    #                     front_height = front_hit.get_hit_pos().z

    #                     if 0.5 < (diff := front_height - below_height) < 1.2:
    #                         result = self.world.ray_test_closest(self.get_pos(), below, BitMask32.bit(2))
    #                         if result.has_hit():
    #                             self.kinema_step = NodePath(result.get_node())
    #                             # self.kinema_step.hide()
    #                             print(result.get_node().get_name())
    #                             print('front_hit', front_hit.get_node().get_name())
                                
    #                             # self.max_height = self.kinema_step.get_z() + 1
    #                             self.max_height = NodePath(front_hit.get_node()).get_z()
    #                             print('jump')
    #                             self.is_jumping = True
    #                         # next_pos.z += diff
    #         print('--------------------')            
    #         self.setPos(next_pos)
    #     else:
    #         self.kinema_step.set_z(self.kinema_step.get_z() + 0.1)
    #         print(self.kinema_step.get_z(), self.max_height)
    #         if self.kinema_step.get_z() >= self.max_height:
    #             self.is_jumping = False

    # ******************** original *****************************************
    #     # orientation = self.direction_node.get_quat(base.render).get_forward()
    #     # next_pos = self.get_pos() + orientation * dist

    #     # if below_hit := self.current_location():
    #     #     if forward_hit := self.watch_steps():
    #     #         below_height = below_hit.get_hit_pos().z
    #     #         forward_height = forward_hit.get_hit_pos().z

    #     #         if 0.5 < (diff := forward_height - below_height) < 1.2:
    #     #             next_pos.z += diff
    #     # self.set_pos(next_pos)

    def go_back(self, dist):
        if self.node().is_on_ground():
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
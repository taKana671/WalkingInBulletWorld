from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape, ZUp
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletCharacterControllerNode, BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, LColor, BitMask32

from utils import create_line_node


class Status(Enum):

    MOVING = auto()
    GOING_UP = auto()
    GETTING_OFF = auto()
    GOING_DOWN = auto()
    COMMING_TO_EDGE = auto()
    COLLISION = auto()

    FALLING = auto()


# class CollisionDetection(NodePath):
#     """Intended to be parented to a character to prevent it from going through
#        walls and fences. CCD cannot be set to BulletCharacterControllerNode.
#     """

#     def __init__(self, name, pos):
#         super().__init__(BulletRigidBodyNode(name))
#         shape = BulletCylinderShape(0.5, 5, ZUp)
#         self.node().add_shape(shape)
#         self.set_collide_mask(BitMask32.bit(2))
#         self.node().set_kinematic(True)
#         self.node().set_ccd_motion_threshold(1e-7)
#         self.node().set_ccd_swept_sphere_radius(0.5)
#         self.set_pos(pos)


class TestShape(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('test'))
        test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.2))
        self.node().add_shape(test_shape)



class Walker(NodePath):

    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        super().__init__(BulletRigidBodyNode('character'))
        # name must start with 'character' because it's used in door safety system
        # super().__init__(BulletCharacterControllerNode(shape, 1.0, 'character'))
        self.world = world

        h, w = 6, 1.2
        # h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        self.node().add_shape(shape)
        self.node().set_kinematic(True)

        self.node().set_ccd_motion_threshold(1e-7)
        self.node().set_ccd_swept_sphere_radius(0.5)

        # bit(1): wall, floor and so on; bit(3): ignored by camera follwing the character;
        # bit(4): embedded objects like lift; bit(5): door sensors
        # self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(3) | BitMask32.bit(4) | BitMask32.bit(5))
        self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(5))

        # self.test_shape = TestShape()
        # self.test_shape.set_pos(Point3(25, -10, 1))
        # self.test_shape.reparent_to(base.render)
        # self.world.attach(self.test_shape.node())

        self.set_pos(Point3(25, -10, 1))
        self.node().set_linear_factor(Vec3(0, 0, 1))

        self.set_scale(0.5)
        self.reparent_to(base.render)
        # self.world.attach_character(self.node())
        self.world.attach(self.node())

        self.direction_nd = NodePath(PandaNode('direction'))
        self.direction_nd.set_h(180)
        self.direction_nd.reparent_to(self)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))  # -3
        self.actor.set_name('ralph')
        self.actor.reparent_to(self.direction_nd)

        self.front = NodePath('front')
        self.front.reparent_to(self.direction_nd)
        self.front.set_pos(0, -1.2, 1)

        self.under = NodePath('under')
        self.under.reparent_to(self.direction_nd)
        self.under.set_pos(0, -1.2, -10)

        self.state = Status.MOVING
        self.frame_cnt = 0
        self.elapsed_time = 0

        # make node having collision shape for preventing penetration.
        # self.detection_nd_f = CollisionDetection('detect_front', Point3(0, -1.2, 0))
        # self.detection_nd_f.reparent_to(self.direction_nd)
        # self.world.attach(self.detection_nd_f.node())

        # self.detection_nd_b = CollisionDetection('detect_back', Point3(0, 1.2, 0))
        # self.detection_nd_b.reparent_to(self.direction_nd)
        # self.world.attach(self.detection_nd_b.node())

        # draw ray cast lines for dubug
        self.debug_line_front = create_line_node(self.front.get_pos(), self.under.get_pos(), LColor(0, 0, 1, 1))
        self.debug_line_center = create_line_node(Point3(0, 0, 0), Point3(0, 0, -10), LColor(1, 0, 0, 1))

    def toggle_debug(self):
        if self.debug_line_front.has_parent():
            self.debug_line_front.detach_node()
            self.debug_line_center.detach_node()
        else:
            self.debug_line_front.reparent_to(self.direction_nd)
            self.debug_line_center.reparent_to(self.direction_nd)

    def navigate(self):
        """Return a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.get_relative_point(self.direction_nd, Vec3(0, 10, 2))

    def current_location(self, mask=BitMask32.all_on()):
        """Cast a ray vertically from the center of Ralph to return BulletRayHit.
        """
        below = base.render.get_relative_point(self, Vec3(0, 0, -10))
        # below = base.render.get_relative_point(self, Vec3(0, 0, -3.0))

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

    def detect_penetration(self, detection_nd):
        """Return True if Ralph collides with objects to which BitMask32.bit(2) has been set as collide mask.
           Arges:
                detection_nd (CollisionDetection)
        """
        if self.world.contact_test(detection_nd.node(), use_filter=True).get_num_contacts() > 0:
            # print('contact!')
            return True

    def detect_collision(self):
        for con in self.world.contact_test(self.node(), use_filter=True).get_contacts():
            print(con.get_node0(), con.get_node1())
            return True
        # if self.world.contact_test(self.node(), use_filter=True).get_num_contacts() > 0:
            # return True

    def predict_collision(self, next_pos):
        ts_from = TransformState.make_pos(self.get_pos())
        ts_to = TransformState.make_pos(next_pos)
        mask = BitMask32.bit(3)
        test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.2))
        result = self.world.sweep_test_closest(test_shape, ts_from, ts_to, mask, 0.0)
        if result.has_hit():
            print('predict_collision', result.get_node())
            return True

    def update(self, dt, direction, angle):
        # for con in self.world.contact_test(self.node(), use_filter=True).get_contacts():
        #     print('detected_collid', con.get_node0(), con.get_node1())
        #     mp = con.get_manifold_point()
        #     print(mp.get_local_point_a(), mp.get_local_point_b())
        # print('-----------------')
            

        orientation = self.direction_nd.get_quat(base.render).get_forward()

        if self.state == Status.MOVING:
            # if not (loc := self.current_location()):
            #     print('Starts falling')
            #     self.state = Status.FALLING
            #     return
            # print('diff ', self.get_z(), loc.get_hit_pos().z, loc.get_node().get_name())
            # if self.get_z() - loc.get_hit_pos().z >= 2.5:
            #     self.state = Status.FALLING
            #     return

            if angle:
                self.turn(angle)

            if direction < 0:
                distance = direction * 10 * dt
                if not self.find_steps():
                    self.move(orientation, direction * 10 * dt)
                    # if not self.detect_collision():
                    #     self.move(orientation, direction * 10 * dt)
                    # else:
                    #     self.state = Status.COLLISION
            if direction > 0:
                distance = direction * 5 * dt
                # if not self.detect_penetration(self.detection_nd_b):
                self.move(orientation, direction * 5 * dt)

        if self.state == Status.GOING_UP:
            self.go_up_on_lift(5 * dt)
            loc = self.current_location()
            self.set_z(loc.get_hit_pos().z + 1.5)

        if self.state == Status.GETTING_OFF:
            self.get_off_lift(orientation, -20 * dt)

        if self.state == Status.COMMING_TO_EDGE:
            self.come_to_edge(orientation, -20 * dt)

        if self.state == Status.GOING_DOWN:
            self.go_down(orientation, 5 * dt)

        if self.state == Status.FALLING:
            z = 0.25 * -9.81 * (self.elapsed_time ** 2)
            self.set_z(self.falling_pos + z)

            if hit := self.current_location():
                if (self.get_z() - hit.get_hit_pos().z) <= 1.5:
                    self.set_z(hit.get_hit_pos().z + 1.5)
                    self.falling_pos = 0
                    self.state = Status.MOVING

            self.elapsed_time += dt
            print('Falling')

    def find_steps(self):
        if (below := self.current_location(BitMask32.bit(1))) and \
                (front := self.watch_front(BitMask32.bit(1))):

            z_diff = (front.get_hit_pos() - below.get_hit_pos()).z
            print('diff', z_diff)
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
        print('move')
        next_pos = self.get_pos() + orientation * distance
        hit = self.world.ray_test_closest(next_pos, next_pos + Vec3(0, 0, -10), BitMask32.bit(1))
        next_pos.z = hit.get_hit_pos().z + 1.5

        print('move_diff', self.get_z() - next_pos.z)
        # if self.get_z() - next_pos.z >= 2.5:
        if self.get_z() - next_pos.z >= 1.5:
            if not self.detect_collision():
                self.falling_pos = self.get_z()
                self.state = Status.FALLING
            else:
                self.set_x(next_pos.x)
                self.set_y(next_pos.y)
            return

        if self.detect_collision():
            if self.predict_collision(next_pos):
                return

        self.set_pos(next_pos)  

    def turn(self, angle):
        self.direction_nd.set_h(self.direction_nd.get_h() + angle)

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
                    self.direction_nd.set_h(self.direction_nd.get_h() + diff)

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
                    self.direction_nd.set_h(self.direction_nd.get_h() + diff)

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

# class CollisionDetection(NodePath):
#     """Intended to be parented to a character to prevent it from going through
#        walls and fences. CCD cannot be set to BulletCharacterControllerNode.
#     """

#     def __init__(self, name, pos):
#         super().__init__(BulletRigidBodyNode(name))
#         shape = BulletCylinderShape(0.5, 5, ZUp)
#         self.node().add_shape(shape)
#         self.set_collide_mask(BitMask32.bit(2))
#         self.node().set_kinematic(True)
#         self.node().set_ccd_motion_threshold(1e-7)
#         self.node().set_ccd_swept_sphere_radius(0.5)
#         self.set_pos(pos)


# class Walker(NodePath):

#     RUN = 'run'
#     WALK = 'walk'

#     def __init__(self, world):
#         h, w = 6, 1.2
#         shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
#         # name must start with 'character' because it's used in door safety system
#         super().__init__(BulletCharacterControllerNode(shape, 1.0, 'character'))
#         self.world = world
#         # bit(1): wall, floor and so on; bit(3): ignored by camera follwing the character;
#         # bit(4): embedded objects like lift; bit(5): door sensors
#         self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(3) | BitMask32.bit(4) | BitMask32.bit(5))
#         self.set_pos(Point3(25, -10, 1))

#         self.set_scale(0.5)
#         self.reparent_to(base.render)
#         self.world.attach_character(self.node())

#         self.direction_nd = NodePath(PandaNode('direction'))
#         self.direction_nd.set_h(180)
#         self.direction_nd.reparent_to(self)

#         self.actor = Actor(
#             'models/ralph/ralph.egg',
#             {self.RUN: 'models/ralph/ralph-run.egg',
#              self.WALK: 'models/ralph/ralph-walk.egg'}
#         )
#         self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))  # -3
#         self.actor.set_name('ralph')
#         self.actor.reparent_to(self.direction_nd)

#         self.front = NodePath('front')
#         self.front.reparent_to(self.direction_nd)
#         self.front.set_pos(0, -1.2, 1)

#         self.under = NodePath('under')
#         self.under.reparent_to(self.direction_nd)
#         self.under.set_pos(0, -1.2, -10)

#         self.state = Status.MOVING
#         self.frame_cnt = 0

#         # make node having collision shape for preventing penetration.
#         self.detection_nd_f = CollisionDetection('detect_front', Point3(0, -1.2, 0))
#         self.detection_nd_f.reparent_to(self.direction_nd)
#         self.world.attach(self.detection_nd_f.node())

#         self.detection_nd_b = CollisionDetection('detect_back', Point3(0, 1.2, 0))
#         self.detection_nd_b.reparent_to(self.direction_nd)
#         self.world.attach(self.detection_nd_b.node())

#         # draw ray cast lines for dubug
#         self.debug_line_front = create_line_node(self.front.get_pos(), self.under.get_pos(), LColor(0, 0, 1, 1))
#         self.debug_line_center = create_line_node(Point3(0, 0, 0), Point3(0, 0, -10), LColor(1, 0, 0, 1))

#     def toggle_debug(self):
#         if self.debug_line_front.has_parent():
#             self.debug_line_front.detach_node()
#             self.debug_line_center.detach_node()
#         else:
#             self.debug_line_front.reparent_to(self.direction_nd)
#             self.debug_line_center.reparent_to(self.direction_nd)

#     def navigate(self):
#         """Return a relative point to enable camera to follow a character
#            when camera's view is blocked by an object like walls.
#         """
#         return self.get_relative_point(self.direction_nd, Vec3(0, 10, 2))

#     def current_location(self, mask=BitMask32.all_on()):
#         """Cast a ray vertically from the center of Ralph to return BulletRayHit.
#         """
#         below = base.render.get_relative_point(self, Vec3(0, 0, -10))
#         ray_result = self.world.ray_test_closest(self.get_pos(), below, mask)

#         if ray_result.has_hit():
#             return ray_result
#         return None

#     def watch_front(self, mask):
#         """Cast a ray vertically from the front of Ralph's face to find steps.
#            If found, BulletRayHit is returned.
#         """
#         from_pos = self.front.get_pos(self) + self.get_pos()
#         to_pos = self.under.get_pos(self) + self.get_pos()
#         ray_result = self.world.ray_test_closest(from_pos, to_pos, mask)

#         if ray_result.has_hit():
#             return ray_result
#         return None

#     def detect_penetration(self, detection_nd):
#         """Return True if Ralph collides with objects to which BitMask32.bit(2) has been set as collide mask.
#            Arges:
#                 detection_nd (CollisionDetection)
#         """
#         if self.world.contact_test(detection_nd.node(), use_filter=True).get_num_contacts() > 0:
#             # print('contact!')
#             return True

#     def update(self, dt, direction, angle):
#         orientation = self.direction_nd.get_quat(base.render).get_forward()

#         if self.state == Status.MOVING:
#             if angle:
#                 self.turn(angle)

#             if direction < 0:
#                 if not self.detect_penetration(self.detection_nd_f):
#                     if not self.find_steps():
#                         self.move(orientation, direction * 10 * dt)
#             if direction > 0:
#                 if not self.detect_penetration(self.detection_nd_b):
#                     self.move(orientation, direction * 5 * dt)

#         if self.state == Status.GOING_UP:
#             self.go_up_on_lift(5 * dt)

#         if self.state == Status.GETTING_OFF:
#             self.get_off_lift(orientation, -20 * dt)

#         if self.state == Status.COMMING_TO_EDGE:
#             self.come_to_edge(orientation, -20 * dt)

#         if self.state == Status.GOING_DOWN:
#             self.go_down(orientation, 5 * dt)

#     def find_steps(self):
#         if (below := self.current_location(BitMask32.bit(1))) and \
#                 (front := self.watch_front(BitMask32.bit(1))):

#             z_diff = (front.get_hit_pos() - below.get_hit_pos()).z

#             # Ralph is likely to go down stairs.
#             if -1.2 <= z_diff <= -0.5:
#                 self.start = NodePath(below.get_node())
#                 self.dest = NodePath(front.get_node())
#                 self.state = Status.COMMING_TO_EDGE
#                 return True

#             # Ralph is likely to go up stairs.
#             if 0.3 < z_diff < 1.2:
#                 if lift := self.current_location(BitMask32.bit(4)):
#                     self.lift = NodePath(lift.get_node())
#                     self.lift_original_z = self.lift.get_z()
#                     self.dest = NodePath(front.get_node())
#                     self.state = Status.GOING_UP
#                     return True

#     def move(self, orientation, distance):
#         if self.node().is_on_ground():
#             next_pos = self.get_pos() + orientation * distance
#             self.set_pos(next_pos)

#     def turn(self, angle):
#         self.direction_nd.set_h(self.direction_nd.get_h() + angle)

#     def go_up_on_lift(self, distance):
#         """Raise a lift embedded in the step on which Ralph is to the height of the next step.
#         """
#         if (next_z := self.lift.get_z() + distance) > self.dest.get_z():
#             self.lift.set_z(self.dest.get_z())
#             self.state = Status.GETTING_OFF
#         else:
#             self.lift.set_z(next_z)

#     def get_off_lift(self, orientation, distance):
#         """Make Ralph on the invisible lift move to the destination.
#            Args:
#                 orientation: (LVector3f)
#                 distance: (float)
#         """
#         get_off = False
#         next_pos = self.get_pos() + orientation * distance
#         self.set_pos(next_pos)
#         self.frame_cnt += 1

#         if below := self.current_location(BitMask32.bit(1)):
#             if below.get_node() == self.dest.node():
#                 get_off = True

#                 # change direction right after get off the lift, for when going up spiral stairs.
#                 if 0 < (diff := self.dest.get_h() - self.lift.get_h()) <= 30:
#                     self.direction_nd.set_h(self.direction_nd.get_h() + diff)

#         if get_off or self.frame_cnt >= 5:
#             self.lift.set_z(self.lift_original_z)
#             self.frame_cnt = 0
#             self.state = Status.MOVING

#     def come_to_edge(self, orientation, distance):
#         """Make Ralph move to the edge of steps.
#            Args:
#                 orientation: (LVector3f)
#                 distance: (float)
#         """
#         next_pos = self.get_pos() + orientation * distance
#         self.set_pos(next_pos)
#         self.frame_cnt += 1
#         on_edge = False

#         if below := self.current_location(BitMask32.bit(1)):
#             if below.get_node() == self.dest.node():
#                 on_edge = True

#                 # change direction right  before the start of falling, for when going down spiral stairs.
#                 if -30 <= (diff := self.dest.get_h() - self.start.get_h()) < 0:
#                     self.direction_nd.set_h(self.direction_nd.get_h() + diff)

#         if on_edge or self.frame_cnt >= 5:
#             self.frame_cnt = 0
#             self.state = Status.GOING_DOWN

#     def go_down(self, orientation, distance):
#         """Wait that Ralph gravitates downwards to collide the destination.
#         """
#         self.set_z(self.get_z() - distance)
#         self.frame_cnt += 1

#         if self.frame_cnt >= 20 or \
#                 self.world.contact_test_pair(self.node(), self.dest.node()).get_num_contacts() > 0:
#             self.frame_cnt = 0
#             self.state = Status.MOVING

#     def play_anim(self, command, rate=1):
#         if not command:
#             self.stop_anim()
#         else:
#             if self.actor.get_current_anim() != command:
#                 self.actor.loop(command)
#                 self.actor.set_play_rate(rate, command)

#     def stop_anim(self):
#         if self.actor.get_current_anim() is not None:
#             self.actor.stop()
#             self.actor.pose(self.WALK, 5)
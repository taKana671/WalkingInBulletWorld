from enum import Enum, auto

from direct.actor.Actor import Actor
from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape, ZUp
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletCharacterControllerNode, BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, LColor, BitMask32

from utils import create_line_node
from mask_manager import Mask


class Motions(Enum):

    FORWARD = auto()
    BACKWARD = auto()
    LEFT = auto()
    RIGHT = auto()
    TURN = auto()


class Status(Enum):

    MOVING = auto()
    GOING_UP = auto()
    TRANSFER = auto()
    FALLING = auto()
    GOING_DOWN = auto()


class TestShape(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('test'))
        # ts_from = TransformState.make_pos(self.get_pos() + Vec3(0, 0, 0.5))
        # ts_to = TransformState.make_pos(next_pos + Vec3(0, 0, 0.5))
        # mask = BitMask32.bit(3)
        # test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.2))
        test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.5))
        self.node().add_shape(test_shape)
        self.set_pos(Point3(25, -10, 0.5) + Vec3(0, 0, 0.3))
        self.reparent_to(base.render)


class Lift:

    __slots__ = ('get_off_pt', 'lift', 'dest', 'lift_original_z', 'dest_z', 'speed')

    def __init__(self, ray_hit_lift, ray_hit_dest, get_off_pt):
        self.get_off_pt = get_off_pt
        self.lift = NodePath(ray_hit_lift.get_node())
        self.dest = NodePath(ray_hit_dest.get_node())
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

    def can_go_down(self, target_nd):
        return target_nd == self.dest.node()

    def get_angular_difference(self):
        return abs(self.dest.get_h() - self.lift.get_h())


class Steps:

    __slots__ = ('start', 'dest', 'fall_start_z')

    def __init__(self, ray_hit_upper, ray_hit_lower, standing_pt):
        self.start = NodePath(ray_hit_upper.get_node())
        self.dest = NodePath(ray_hit_lower.get_node())
        self.fall_start_z = standing_pt.get_z()

    def can_go_down(self, target_nd):
        return target_nd == self.dest.node()

    def get_angular_difference(self):
        return abs(self.start.get_h() - self.dest.get_h())


class Walker(NodePath):

    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        super().__init__(BulletRigidBodyNode('character'))
        # name must start with 'character' because it's used in door safety system
        self.world = world

        h, w = 6, 1.2
        # h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        self.node().add_shape(shape)
        self.node().set_kinematic(True)

        self.node().set_ccd_motion_threshold(1e-7)
        self.node().set_ccd_swept_sphere_radius(0.8)

        # bit(1): wall, floor and so on; bit(3): ignored by camera follwing the character;
        # bit(4): embedded objects like lift; bit(5): door sensors
        # self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(3) | BitMask32.bit(4) | BitMask32.bit(5))
        self.set_collide_mask(BitMask32.bit(2) | BitMask32.bit(5) | BitMask32.bit(6))

        # self.test_shape = TestShape()
        # self.test_shape.set_pos(Point3(25, -10, 1))
        # self.test_shape.reparent_to(base.render)
        # self.world.attach(self.test_shape.node())

        # self.set_pos(Point3(25, -10, 1))
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
        self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))  # -3
        self.actor.set_name('ralph')
        self.actor.reparent_to(self.direction_nd)
        self.actor_h = 1.5

        self.front = NodePath('front')
        self.front.reparent_to(self.direction_nd)
        # self.front.set_pos(0, -1.2, 1)
        self.front.set_pos(0, -1, 1)

        self.back = NodePath('back')
        self.back.reparent_to(self.direction_nd)
        # self.back.set_pos(0, 1.2, 1)
        self.back.set_pos(0, 1, 1)

        self.under = NodePath('under')
        self.under.reparent_to(self.direction_nd)
        self.under.set_pos(0, -1.2, -10)

        self.state = Status.MOVING
        self.elapsed_time = 0
        self.fall_start_z = None

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

    def detect_collision(self):
        if self.world.contact_test(
                self.node(), use_filter=True).get_num_contacts() > 0:
            return True

    def predict_collision(self, from_pos, to_pos, mask):
        ts_from = TransformState.make_pos(from_pos + Vec3(0, 0, 0.3))
        ts_to = TransformState.make_pos(to_pos + Vec3(0, 0, 0.3))
        test_shape = BulletBoxShape(Vec3(0.3, 0.3, 1.5))

        if (result := self.world.sweep_test_closest(
                test_shape, ts_from, ts_to, mask, 0.0)).has_hit():
            print('predicted collision: ', result.get_node())
            return result

    def move(self, forward_vector, direction, dt):
        speed = 10 if direction < 0 else 5
        next_pos = self.get_pos() + forward_vector * direction * speed * dt
        current_pos = self.get_pos()

        if not (forward := self.check_forward(direction, current_pos)) or \
                not (below := self.check_below(current_pos)):
            return

        f_hit_pos = forward.get_hit_pos()
        b_hit_pos = below.get_hit_pos()
        diff_z = abs(b_hit_pos.z - f_hit_pos.z)
        self.last_direction = direction
        print('diff: ', diff_z, 'below', b_hit_pos.z, 'forward: ', f_hit_pos.z)

        if f_hit_pos.z > b_hit_pos.z and 0.3 < diff_z < 1.2:
            if lift := self.check_below(current_pos, Mask.lift):
                if self.can_go_up(f_hit_pos, current_pos):
                    self.lift = Lift(lift, forward, f_hit_pos)
                    return Status.GOING_UP

        if self.detect_collision():
            if self.predict_collision(current_pos, next_pos, Mask.predict):
                print('Cannot go forward.')
                return

        if f_hit_pos.z < b_hit_pos.z:
            forward_pos = f_hit_pos + Vec3(0, 0, self.actor_h)
            if 0.5 <= diff_z < 1.2 and self.check_below(forward_pos, Mask.lift):
                if not self.predict_collision(current_pos, forward_pos, Mask.sweep):
                    print('Go down steps')
                    self.steps = Steps(below, forward, current_pos)
                    return Status.GOING_DOWN
            else:
                if diff_z >= 1.:
                    print('Jump')
                    self.steps = Steps(below, forward, current_pos)
                    self.set_pos(next_pos)
                    return Status.FALLING

        next_hit = self.check_below(next_pos)
        next_pos.z = next_hit.get_hit_pos().z + self.actor_h
        self.set_pos(next_pos)

    def can_go_up(self, f_hit_pos, current_pos):
        from_pos = Point3(current_pos.xy, f_hit_pos.z + self.actor_h)
        to_pos = Point3(f_hit_pos.xy, f_hit_pos.z + self.actor_h)

        if not self.predict_collision(from_pos, to_pos, Mask.sweep):
            return True
        print('Cannot go up stairs')

    def detect_stairs_going_up(self, forward, current_pos):

        if below := self.check_below(current_pos, Mask.lift):
            print('Found lift.')
            forward_hit_pos = forward.get_hit_pos()
            from_pos = Point3(current_pos.xy, forward_hit_pos.z)
            to_pos = forward_hit_pos + Vec3(0, 0, self.actor_h)

            if not self.predict_collision(from_pos, to_pos, Mask.sweep):
                self.lift = NodePath(below.get_node())
                self.hit_pos = forward.get_hit_pos()
                self.lift_original_z = self.lift.get_z()
                self.dest = NodePath(forward.get_node())
                return True

    def update(self, dt, motions):
        direction = 0
        angle = 0
        motion = None

        if Motions.LEFT in motions:
            angle += 100 * dt
            motion = Motions.TURN
        if Motions.RIGHT in motions:
            angle -= 100 * dt
            motion = Motions.TURN
        if Motions.FORWARD in motions:
            direction += -1
            motion = Motions.FORWARD
        if Motions.BACKWARD in motions:
            direction += 1
            motion = Motions.BACKWARD

        forward_vector = self.direction_nd.get_quat(base.render).get_forward()

        match self.state:
            case Status.MOVING:
                if angle:
                    self.turn(angle)

                if direction != 0:
                    if status := self.move(forward_vector, direction, dt):
                        self.state = status

            case Status.GOING_UP:
                if self.go_up(dt):
                    self.state = Status.TRANSFER

            case Status.TRANSFER:
                if self.transfer(forward_vector, dt):
                    self.state = Status.MOVING

            case Status.FALLING:
                motion = None
                if self.fall(forward_vector, dt):
                    self.state = Status.MOVING

            case Status.GOING_DOWN:
                motion = Motions.FORWARD if self.last_direction < 0 else Motions.BACKWARD
                if self.go_down(forward_vector, dt):
                    self.state = Status.MOVING

        self.play_anim(motion)

    def check_below(self, from_pos, mask=Mask.ground):
        to_pos = from_pos + Vec3(0, 0, -10)

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
        nd = self.check_below(current_pos).get_node()

        if self.lift.can_go_down(nd):
            # change angle, for when going up spiral stairs.
            if 0 < (diff := self.lift.get_angular_difference()) <= 30:
                h = self.direction_nd.get_h() + diff
                self.direction_nd.set_h(h)

            self.set_pos(self.lift.get_off_pt + Vec3(0, 0, self.actor_h))  # need it?
            self.lift.down()
            return True

        distance = self.last_direction * 4 * dt
        next_pos = current_pos + forward_vector * distance
        self.set_pos(next_pos)

    def fall(self, forward_vector, dt):
        behind = self.check_backward(self.last_direction)

        if not self.steps.can_go_down(behind.get_node()):
            distance = self.last_direction * 5 * dt
            next_pos = self.get_pos() + forward_vector * distance
            self.set_pos(next_pos)

        next_z = 0.25 * -9.81 * (self.elapsed_time ** 2) + self.steps.fall_start_z
        below = self.check_below(self.get_pos())

        if abs(next_z - (dest_z := below.get_hit_pos().z)) < 1.5:
            self.set_z(dest_z + self.actor_h)
            self.fall_start_z = 0
            self.elapsed_time = 0
            return True

        self.elapsed_time += dt
        self.set_z(next_z)

    def go_down(self, forward_vector, dt):
        next_z = 0.4 * -9.81 * (self.elapsed_time ** 2) + self.steps.fall_start_z
        below = self.check_below(self.get_pos())

        if not self.steps.can_go_down(below.get_node()):
            distance = self.last_direction * 5 * dt
            next_pos = self.get_pos() + forward_vector * distance
            self.set_pos(next_pos)
        else:
            if abs(next_z - (dest_z := below.get_hit_pos().z)) < 1.5:
                print('go down the stairs')
                # change angle, for when going down spiral stairs.
                if 0 < (diff := self.steps.get_angular_difference()) <= 30:
                    self.direction_nd.set_h(self.direction_nd.get_h() - diff)

                self.set_z(dest_z + self.actor_h)
                self.fall_start_z = 0
                self.elapsed_time = 0
                return True

        self.set_z(next_z)
        self.elapsed_time += dt

    def play_anim(self, motion):
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
            case _:
                if self.actor.get_current_anim() is not None:
                    self.actor.stop()
                    self.actor.pose(Walker.WALK, 5)
                return

        if self.actor.get_current_anim() != anim:
            self.actor.loop(anim)
            self.actor.set_play_rate(rate, anim)

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
#         forward_vector = self.direction_nd.get_quat(base.render).get_forward()

#         if self.state == Status.MOVING:
#             if angle:
#                 self.turn(angle)

#             if direction < 0:
#                 if not self.detect_penetration(self.detection_nd_f):
#                     if not self.find_steps():
#                         self.move(forward_vector, direction * 10 * dt)
#             if direction > 0:
#                 if not self.detect_penetration(self.detection_nd_b):
#                     self.move(forward_vector, direction * 5 * dt)

#         if self.state == Status.GOING_UP:
#             self.go_up_on_lift(5 * dt)

#         if self.state == Status.GETTING_OFF:
#             self.get_off_lift(forward_vector, -20 * dt)

#         if self.state == Status.COMMING_TO_EDGE:
#             self.come_to_edge(forward_vector, -20 * dt)

#         if self.state == Status.GOING_DOWN:
#             self.go_down(forward_vector, 5 * dt)

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

#     def move(self, forward_vector, distance):
#         if self.node().is_on_ground():
#             next_pos = self.get_pos() + forward_vector * distance
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

#     def get_off_lift(self, forward_vector, distance):
#         """Make Ralph on the invisible lift move to the destination.
#            Args:
#                 forward_vector: (LVector3f)
#                 distance: (float)
#         """
#         get_off = False
#         next_pos = self.get_pos() + forward_vector * distance
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

#     def come_to_edge(self, forward_vector, distance):
#         """Make Ralph move to the edge of steps.
#            Args:
#                 forward_vector: (LVector3f)
#                 distance: (float)
#         """
#         next_pos = self.get_pos() + forward_vector * distance
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

#     def go_down(self, forward_vector, distance):
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
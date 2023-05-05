from enum import Enum, auto

from panda3d.bullet import BulletConvexHullShape
from panda3d.bullet import BulletGhostNode
from panda3d.bullet import BulletConeTwistConstraint, BulletSliderConstraint
from panda3d.core import Vec3, Quat
from panda3d.core import NodePath


class SensorStatus(Enum):

    WAITING = auto()
    OPEN = auto()
    CLOSE = auto()
    KEEP_TIME = auto()
    CHECKING = auto()


class SlidingDoor(BulletSliderConstraint):
    """Args:
            door (BulletRigidBodyNode)
            wall (BulletRigidBodyNode)
            door_frame_ts (TransformState)
            wall_frame_ts (TransformState)
            movement_range (float) the range of slider movement; cannot be 0;
                positive: door moves leftward when opens.; negative: door moves rightward when opens.
            direction (int) must be 1 or -1; 1: door moves leftward when opens; -1: door moves rightward when opens.
    """
    def __init__(self, door_nd, wall_nd, ts_door_frame, ts_wall_frame, movement_range, direction):
        super().__init__(door_nd, wall_nd, ts_door_frame, ts_wall_frame, True)
        self.set_debug_draw_size(2.0)
        # self.set_powered_linear_motor(True)
        # self.set_target_linear_motor_velocity(0.1)
        self.door_nd = door_nd
        self.movement_range = movement_range
        self.direction = direction
        self.opened_pos = self.movement_range * self.direction
        self.closed_pos = 0
        self.amount = 0
        self.rate = 0.02

    def slide(self, distance):
        self.set_lower_linear_limit(distance)
        self.set_upper_linear_limit(distance)

    def open(self):
        if self.get_linear_pos() * self.direction >= self.opened_pos:
            self.amount = 0
            return True

        self.amount += 1
        distance = self.amount * self.rate * self.direction
        self.slide(distance)

    def close(self):
        if self.get_linear_pos() * self.direction <= self.closed_pos:
            # prevents doors from colliding with each other to break.
            self.amount = 0
            self.slide(0)
            return True

        self.amount += 1
        distance = self.movement_range - self.amount * self.rate * self.direction
        self.slide(distance)


class ConeTwistDoor(BulletConeTwistConstraint):
    """Args:
            door (BulletRigidBodyNode)
            wall (BulletRigidBodyNode)
            door_frame_ts (TransformState)
            wall_frame_ts (TransformState)
            direction (int) must be 1 or -1; 1: Door opens inward.; -1: Door opens outward.;
    """

    def __init__(self, door_nd, wall_nd, ts_door_frame, ts_wall_frame, direction):
        super().__init__(door_nd, wall_nd, ts_door_frame, ts_wall_frame)
        self.setDebugDrawSize(2.0)
        # self.setLimit(0, 120, 0, softness=0.9, bias=0.3, relaxation=4.0)
        self.setLimit(0, 120, 0)
        self.door_nd = door_nd
        self.direction = direction
        self.max_angle = 90
        self.min_angle = 0
        self.rot_axis = Vec3.up()  # Vec3(0, 0, 1)
        self.current_angle = 0
        self.rot = Quat()

    def rotate(self, angle):
        self.rot.set_from_axis_angle(angle * self.direction, self.rot_axis)
        self.set_limit(self.min_angle, angle)
        self.set_motor_target(self.rot)

    def open(self):
        if self.current_angle >= self.max_angle:
            return True

        self.current_angle += 1
        self.rotate(self.current_angle)
        return False

    def close(self):
        if self.current_angle <= self.min_angle:
            return True

        self.current_angle -= 1
        self.rotate(self.current_angle)

    def activate_twist(self):
        self.enable_motor(True)
        self.rotate(0)

    def deactivate_twist(self):
        self.enable_motor(False)


class AutoDoorSensor(NodePath):

    def __init__(self, name, world, geom_np, pos, scale, bitmask):
        super().__init__(BulletGhostNode(name))
        geom_np = geom_np.copy_to(self)
        nd = geom_np.node()
        geom = nd.get_geom(0)
        shape = BulletConvexHullShape()
        shape.add_geom(geom)
        self.node().add_shape(shape)
        self.set_scale(scale)
        self.set_pos(pos)
        self.set_collide_mask(bitmask)

        self.world = world
        self.state = SensorStatus.WAITING
        self.timer = 0

    def detect_person(self):
        for node in self.node().get_overlapping_nodes():
            # print(node.get_name())
            if all(node != door for door in self.doors):
                return True

    def detect_collision(self):
        for door in self.doors:
            for con in self.world.contact_test(door).get_contacts():
                # print(con.get_node0().get_name(), con.get_node1().get_name())
                if con.get_node1().get_name().startswith(('character', 'detect')):
                    return True

    def sensing(self, task):
        match self.state:
            case SensorStatus.WAITING:
                self.wait()
            case SensorStatus.OPEN:
                self.open()
            case SensorStatus.CHECKING:
                self.check()
            case SensorStatus.KEEP_TIME:
                self.keep_time()
            case SensorStatus.CLOSE:
                self.close()

        return task.cont

    def wait(self):
        """Override in subclasses."""
        raise NotImplementedError()

    def open(self):
        """Override in subclasses."""
        raise NotImplementedError()

    def check(self):
        """Override in subclasses if needed."""
        if not self.detect_person():
            self.state = SensorStatus.KEEP_TIME

    def keep_time(self):
        """Override in subclasses."""
        raise NotImplementedError()

    def close(self):
        """Override in subclasses."""
        raise NotImplementedError()


class SlidingDoorSensor(AutoDoorSensor):

    def __init__(self, name, world, geom_np, pos, scale, bitmask, *sliders):
        super().__init__(name, world, geom_np, pos, scale, bitmask)
        self.sliders = sliders
        self.doors = [slider.door_nd for slider in sliders]
        self.time_interval = 10

    def wait(self):
        if self.detect_person():
            self.state = SensorStatus.OPEN

    def open(self):
        result = True
        for slider in self.sliders:
            if not slider.open():
                result = False
        if result:
            self.state = SensorStatus.CHECKING

    def keep_time(self):
        self.timer += 1
        if self.timer >= self.time_interval:
            self.timer = 0
            self.state = SensorStatus.CLOSE

    def close(self):
        if self.detect_person():
            self.state = SensorStatus.OPEN
        else:
            result = True
            for slider in self.sliders:
                if not slider.close():
                    result = False
            if result:
                self.state = SensorStatus.WAITING


class ConeTwistDoorSensor(AutoDoorSensor):

    def __init__(self, name, world, geom_np, pos, scale, bitmask, *twists):
        super().__init__(name, world, geom_np, pos, scale, bitmask)
        self.twists = twists
        self.doors = set(twist.door_nd for twist in twists)
        self.time_interval = 20

    def wait(self):
        if self.detect_person():
            for twist in self.twists:
                twist.activate_twist()
            self.state = SensorStatus.OPEN

    def open(self):
        if not self.detect_collision():
            result = True
            for twist in self.twists:
                if not twist.open():
                    result = False
            if result:
                self.state = SensorStatus.CHECKING

    def keep_time(self):
        self.timer += 1
        if self.timer >= self.time_interval:
            self.timer = 0
            self.state = SensorStatus.CLOSE

    def close(self):
        if self.detect_person():
            self.state = SensorStatus.OPEN
        if not self.detect_collision():
            result = True
            for twist in self.twists:
                if not twist.close():
                    result = False
            if result:
                for twist in self.twists:
                    twist.deactivate_twist()
                self.state = SensorStatus.WAITING

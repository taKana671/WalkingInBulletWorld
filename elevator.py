from enum import Enum, auto

from direct.showbase.ShowBaseGlobal import globalClock
from direct.interval.IntervalGlobal import ProjectileInterval, Parallel, Sequence, Func, Wait
from panda3d.bullet import BulletCharacterControllerNode

from automatic_doors import MotionSensor, SensorStatus


class ElevatorStatus(Enum):

    RIDE = auto()
    MOVE = auto()
    ARRIVE = auto()
    CALL = auto()
    GETOFF = auto()

    DISPATCH = auto()

    WAITING = auto()
    OPEN = auto()
    CLOSE = auto()
    KEEP_TIME = auto()
    CHECKING = auto()



class Elevator:
    """Control the elevator that carries character from the first floor to the roof top.
       Args:
            cage (BulletRigidBodyNode): the cage which charactier ride; must be kinematic.
            self.door_sensor_1 (ElevatorDoorSensor)
            # direction (int): the direcion to which the cage moves; up: 1, down: -1
    """

    def __init__(self, world, cage, door_sensor_1, door_sensor_2):
        self.world = world
        self.cage = cage
        self.sensor_1 = door_sensor_1
        self.sensor_2 = door_sensor_2
        # self.direction = None
        self.state = ElevatorStatus.WAITING
        self.active_sensor = self.sensor_1

        # self.start_sensor = self.sensor_1
        # self.dest_sensor = self.sensor_2

    # def detect(self):
    #     if self.door_sensor_1.detect_person():
    #         self.start_sensor = self.door_sensor_1
    #         self.dest_sensor = self.door_sensor_2
    #         print('detect door_sensor_1')
    #         return True

    #     if self.door_sensor_2.detect_person():
    #         self.start_sensor = self.door_sensor_2
    #         self.dest_sensor = self.door_sensor_1
    #         print('detect door_sensor_2')
    #         return True

    def wait(self):
        for sensor in [self.sensor_1, self.sensor_2]:
            if sensor.detect_person():
                self.start_sensor = sensor
                self.dest_sensor = self.sensor_1 if sensor == self.sensor_2 else self.sensor_2
                self.active_sensor = sensor
                self.state = ElevatorStatus.DISPATCH
                break

        # if self.door_sensor_1.detect_person():
        #     self.start_sensor = self.door_sensor_1
        #     self.dest_sensor = self.door_sensor_2
        #     print('detect door_sensor_1')
        # elif self.door_sensor_2.detect_person():
        #     self.start_sensor = self.door_sensor_2
        #     self.dest_sensor = self.door_sensor_1
        #     print('detect door_sensor_2')

        # if self.detect():
        #     if self.dest_sensor.stop_pos.z > self.start_sensor.stop_pos.z:
        #         self.direction = 1
        #     else:
        #         self.direction = -1

        #     if self.cage.get_z() != self.start_sensor.stop_pos.z and \
        #             self.dest_sensor.state == ElevatorStatus.CLOSE:
        #         self.cage.set_z(self.start_sensor.stop_pos.z)

        #     self.state = ElevatorStatus.RIDE

    def call_cage(self):
        if self.cage.get_z() != self.start_sensor.stop_pos.z:
            self.cage.set_z(self.start_sensor.stop_pos.z)

        self.active_sensor.state = SensorStatus.OPEN
        self.state = ElevatorStatus.RIDE

    def start(self):
        if self.active_sensor.state == SensorStatus.WAITING:
            for con in self.world.contact_test(self.cage.node()).get_contacts():
                if isinstance(con.get_node1(), BulletCharacterControllerNode):
                    self.cage.posInterval(3, self.dest_sensor.stop_pos).start()
                    self.state = ElevatorStatus.MOVE
                    break

    def arrive(self):
        if self.cage.get_z() == self.dest_sensor.stop_pos.z:
            self.dest_sensor.state = SensorStatus.OPEN
            self.active_sensor = self.dest_sensor

    def update(self, task):
        self.active_sensor.sensing()

        match self.state:
            case ElevatorStatus.WAITING:
                self.wait()
            case ElevatorStatus.DISPATCH:
                self.call_cage()
            case ElevatorStatus.RIDE:
                self.start()
            case ElevatorStatus.MOVE:
                self.arrive()

        return task.cont



    # def update(self, task):
    #     self.door_sensor_1.sensing()
    #     self.door_sensor_2.sensing()

    #     match self.state:
    #         case ElevatorStatus.WAITING:
    #             self.wait()
    #         case ElevatorStatus.RIDE:
    #             if self.cage.get_z() != self.start_sensor.stop_pos.z:
    #                 self.cage.set_z(self.start_sensor.stop_pos.z)
    #             self.start_sensor.state = ElevatorStatus.OPEN
    #             self.state = ElevatorStatus.MOVE

    #         case ElevatorStatus.MOVE:
    #             if self.start_sensor.state == ElevatorStatus.CLOSE:
    #                 for con in self.world.contact_test(self.cage.node()).get_contacts():
    #                     if isinstance(con.get_node1(), BulletCharacterControllerNode):
    #                         Sequence(
    #                             self.cage.posInterval(3, self.dest_sensor.stop_pos)
    #                         ).start()
    #                         self.state = ElevatorStatus.ARRIVE
    #                         break
    #         case ElevatorStatus.ARRIVE:
    #             if self.cage.get_z() == self.dest_sensor.stop_pos.z:
    #                 self.dest_sensor.state = ElevatorStatus.OPEN

    #     return task.cont


class ElevatorDoorSensor(MotionSensor):

    def __init__(self, name, world, geom_np, pos, scale, bitmask, stop_pos, *sliders):
        super().__init__(name, world, geom_np, pos, scale, bitmask)
        self.sliders = sliders
        self.doors = [slider.door_nd for slider in sliders]
        self.time_interval = 10

        self.state = SensorStatus.WAITING
        self.timer = 0
        self.stop_pos = stop_pos

    def sensing(self):
        match self.state:
            # case ElevatorStatus.WAITING:
            #     self.wait()
            case SensorStatus.OPEN:
                # print('called!!')
                self.open()
            case SensorStatus.CHECKING:
                self.check()
            case SensorStatus.KEEP_TIME:
                self.keep_time()
            case SensorStatus.CLOSE:
                self.close()

    # def wait(self):
    #     if self.detect_person():
    #         self.state = ElevatorStatus.OPEN

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

    def check(self):
        if not self.detect_person():
            self.state = SensorStatus.KEEP_TIME
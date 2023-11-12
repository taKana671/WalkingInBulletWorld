from enum import Enum, auto

from panda3d.bullet import BulletCharacterControllerNode

from automatic_doors import MotionSensor


class ElevatorStatus(Enum):

    WAITING = auto()
    DISPATCH = auto()
    OPEN = auto()
    ENSURE = auto()
    CLOSE = auto()
    MOVE = auto()
    ARRIVE = auto()


class Elevator:
    """Control the elevator that carries a character from the 1st floor to the top floor.
       Args:
            world (BulletWorld): bullet world
            cage (BulletRigidBodyNode): the cage which the charactier rides; must be kinematic.
            self.door_sensor_1 (ElevatorDoorSensor): the door sensor on the 1st floor.
            self.door_sensor_2 (ElevatorDoorSensor): the door sensor on the top floor.
    """

    def __init__(self, world, cage, door_sensor_1, door_sensor_2):
        self.world = world
        self.cage = cage
        self.sensor_1 = door_sensor_1
        self.sensor_2 = door_sensor_2
        self.sensors = {
            1: self.sensor_1,
            2: self.sensor_2
        }
        self.stop_floor = None
        self.state = ElevatorStatus.WAITING
        self.lock_doors()

    def lock_doors(self):
        cage_z = self.cage.get_z()

        for floor, sensor in self.sensors.items():
            if sensor.stop_pos.z != cage_z:
                sensor.lock_door()

    def wait(self):
        for floor, sensor in self.sensors.items():
            if sensor.detect_person():
                # print(f'Ralph is detected by {sensor}')
                self.start_sensor = sensor
                self.dest_sensor = self.sensor_1 if sensor == self.sensor_2 else self.sensor_2
                self.stop_floor = floor
                self.state = ElevatorStatus.DISPATCH
                break

    def call_cage(self):
        if (z := self.start_sensor.stop_pos.z) != self.cage.get_z():
            self.cage.set_z(z)
            self.start_sensor.unlock_door()

        self.state = ElevatorStatus.OPEN

    def open_door(self):
        if self.sensors[self.stop_floor].open():
            self.state = ElevatorStatus.ENSURE

    def ensure_safety(self):
        if self.sensors[self.stop_floor] == self.start_sensor:
            if not self.start_sensor.keep_time():
                self.state = ElevatorStatus.CLOSE
        else:
            # When arrives the destination, leave the door open while Ralph is in the elevator.
            for con in self.world.contact_test(self.cage.node()).get_contacts():
                if isinstance(con.get_node1(), BulletCharacterControllerNode):
                    return
            self.state = ElevatorStatus.CLOSE

    def move(self):
        for con in self.world.contact_test(self.cage.node()).get_contacts():
            if isinstance(con.get_node1(), BulletCharacterControllerNode):

                # Replace start floor with destination one, if Ralph rashes into the elevator before the door closes.
                if self.sensors[self.stop_floor] == self.dest_sensor:
                    self.start_sensor, self.dest_sensor = self.dest_sensor, self.start_sensor

                self.start_sensor.lock_door()
                self.cage.posInterval(3, self.dest_sensor.stop_pos).start()
                self.state = ElevatorStatus.ARRIVE
                return

        self.state = ElevatorStatus.WAITING

    def close_door(self):
        if self.sensors[self.stop_floor].close():
            self.state = ElevatorStatus.MOVE

    def check_arrival(self):
        if self.cage.get_z() == self.dest_sensor.stop_pos.z:
            self.stop_floor = [k for k, v in self.sensors.items() if v == self.dest_sensor][0]
            base.messenger.send('elevator_arrive', sentArgs=[self.stop_floor])
            # print(f'Ralph is now on the {self.stop_floor} floor')
            self.dest_sensor.unlock_door()
            self.state = ElevatorStatus.OPEN

    def control(self, task):
        match self.state:
            case ElevatorStatus.WAITING:
                self.wait()
            case ElevatorStatus.DISPATCH:
                self.call_cage()
            case ElevatorStatus.OPEN:
                self.open_door()
            case ElevatorStatus.ENSURE:
                self.ensure_safety()
            case ElevatorStatus.CLOSE:
                self.close_door()
            case ElevatorStatus.MOVE:
                self.move()
            case ElevatorStatus.ARRIVE:
                self.check_arrival()

        return task.cont


class ElevatorDoorSensor(MotionSensor):

    def __init__(self, name, world, geom_np, pos, scale, bitmask, stop_pos, *sliders):
        super().__init__(name, world, geom_np, pos, scale, bitmask)
        self.sliders = sliders
        self.doors = [slider.door_nd for slider in sliders]
        self.time_interval = 10
        self.timer = 0
        self.stop_pos = stop_pos

    def open(self):
        result = True
        for slider in self.sliders:
            if not slider.open():
                result = False

        return result

    def keep_time(self):
        self.timer += 1
        if self.timer >= self.time_interval:
            self.timer = 0
            return False
        return True

    def close(self):
        result = True

        if self.detect_person() or self.detect_collision():
            self.open()
            result = False
        else:
            for slider in self.sliders:
                if not slider.close():
                    result = False
        return result

    def lock_door(self):
        for door_nd in self.doors:
            door_nd.set_mass(0)
            door_nd.deactivation_enabled = False

    def unlock_door(self):
        for door_nd in self.doors:
            door_nd.set_mass(1)
            door_nd.deactivation_enabled = True

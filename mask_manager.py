from panda3d.core import BitMask32


class MaskMeta(type):

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise TypeError(f'Cannot rebind ({name})')

        self.__setattr__(name, value)


class Mask(metaclass=MaskMeta):

    ground = BitMask32.bit(1)
    collision = BitMask32.bit(2)
    predict = BitMask32.bit(3)
    lift = BitMask32.bit(4)
    sensor = BitMask32.bit(5)
    camera = BitMask32.bit(6)
    sweep = BitMask32.bit(7)
    almighty = BitMask32.all_on()


class MultiMask(metaclass=MaskMeta):

    walker = Mask.collision | Mask.sensor | Mask.camera
    building = Mask.ground | Mask.collision | Mask.predict | Mask.camera
    fence = Mask.collision | Mask.predict | Mask.camera
    handrail = Mask.collision | Mask.predict | Mask.sweep
    staircase = Mask.collision | Mask.predict | Mask.camera | Mask.sweep
    dynamic_body = Mask.collision | Mask.predict
from panda3d.core import BitMask32


class MaskMeta(type):

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise TypeError(f'Cannot rebind ({name})')

        self.__setattr__(name, value)


class Mask(metaclass=MaskMeta):

    camera = BitMask32.bit(6)
    ground = BitMask32.bit(1)
    collision = BitMask32.bit(2)
    predict = BitMask32.bit(3)
    sweep = BitMask32.bit(7)
    lift = BitMask32.bit(4)
    sensor = BitMask32.bit(5)

    building = BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(3) | BitMask32.bit(6)
    fence = BitMask32.bit(2) | BitMask32.bit(3) | BitMask32.bit(6) | BitMask32.bit(7)
    poles = BitMask32.bit(2) | BitMask32.bit(3) | BitMask32.bit(7)
    door = BitMask32.all_on()
    dynamic_body = BitMask32.bit(2) | BitMask32.bit(3)
    walker = BitMask32.bit(2) | BitMask32.bit(5) | BitMask32.bit(6)
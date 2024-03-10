from panda3d.core import BitMask32


class MaskMeta(type):

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise TypeError(f'Cannot rebind ({name})')

        self.__setattr__(name, value)


class Masks(metaclass=MaskMeta):

    bit_1 = BitMask32.bit(1)
    bit_1_2 = BitMask32.bit(1) | BitMask32.bit(2)




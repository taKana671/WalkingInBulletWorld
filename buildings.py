import math
from enum import Enum
from itertools import product, chain

from panda3d.core import Vec3, Vec2, Point3
from panda3d.core import CardMaker, Texture, TextureStage
from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape
from panda3d.bullet import BulletTriangleMeshShape, BulletTriangleMesh
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletConeTwistConstraint

from utils import Cube, DecagonalPrism, make_tube, make_torus


class Images(Enum):

    FIELD_STONE = 'fieldstone.jpg'
    IRON = 'iron.jpg'
    BOARD = 'board.jpg'
    BRICK = 'brick.jpg'
    CONCRETE = 'concrete.jpg'
    LAYINGBROCK = 'layingrock.jpg'
    COBBLESTONES = 'cobblestones.jpg'
    METALBOARD = 'metalboard.jpg'
    CONCRETE2 = 'concrete2.jpg'

    @property
    def path(self):
        return f'textures/{self.value}'


class Block(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = model.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)
        end, tip = self.model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(bitmask)


class Plane(NodePath):

    def __init__(self, name, parent, model, pos):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = model
        self.model.reparentTo(self)
        self.setPos(pos)

        end, tip = self.model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(1))


class Cylinder(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = model.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)
        shape = BulletConvexHullShape()
        shape.addGeom(self.model.node().getGeom(0))
        self.node().addShape(shape)
        self.setCollideMask(bitmask)


class Ring(NodePath):

    def __init__(self, name, parent, geomnode, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = self.attachNewNode(geomnode)
        self.model.setTwoSided(True)

        mesh = BulletTriangleMesh()
        mesh.addGeom(geomnode.getGeom(0))
        shape = BulletTriangleMeshShape(mesh, dynamic=False)

        self.node().addShape(shape)
        self.setCollideMask(bitmask)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)


class Materials:

    _textures = dict()

    def __init__(self, world):
        self.world = world
        self.cube = Cube.make()
        self.cylinder = DecagonalPrism.make()

    def texture(self, image):
        if image not in self._textures:
            tex = base.loader.loadTexture(image.path)
            tex.setWrapU(Texture.WM_repeat)
            tex.setWrapV(Texture.WM_repeat)
            self._textures[image] = tex

        return self._textures[image]

    def block(self, name, parent, pos, scale, hpr=None, horizontal=True, active_always=False, bitmask=BitMask32.bit(1)):
        if not hpr:
            hpr = Vec3(0, 0, 0) if horizontal else Vec3(90, 0, 0)

        block = Block(name, parent, self.cube, pos, hpr, scale, bitmask)
        su = (scale.x * 2 + scale.y * 2) / 4
        sv = scale.z / 4
        block.setTexScale(TextureStage.getDefault(), su, sv)

        if active_always:
            block.node().setMass(1)
            block.node().setDeactivationEnabled(False)

        self.world.attachRigidBody(block.node())
        return block

    def knob(self, parent, left_hinge):
        x = 0.4 if left_hinge else -0.4
        pos = Point3(x, 0, 0)
        hpr = Vec3(90, 0, 0)
        scale = Vec3(1.5, 0.05, 0.05)
        knob = Block('knob', parent, self.cube, pos, hpr, scale, BitMask32.bit(1))
        knob.setColor(0, 0, 0, 1)

    def door(self, name, parent, pos, scale, static_body, hpr=None, horizontal=True, left_hinge=True):
        door = self.block(name, parent, pos, scale, hpr, horizontal, active_always=True, bitmask=BitMask32.allOn())
        self.knob(door, left_hinge)

        end, tip = door.getTightBounds()
        door_size = tip - end
        end, tip = static_body.getTightBounds()
        static_size = tip - end

        door_x = -(door_size.x / 2) if left_hinge else door_size.x / 2
        wall_x = static_size.x / 2 if left_hinge else -static_size.x / 2

        twist = BulletConeTwistConstraint(
            static_body.node(),
            door.node(),
            TransformState.makePos(Point3(wall_x, static_size.y / 2, 0)),
            TransformState.makePos(Point3(door_x, door_size.y / 2, 0)),
        )

        twist.setLimit(60, 60, 0, softness=0.1, bias=0.1, relaxation=8.0)
        self.world.attachConstraint(twist)

    def pole(self, name, parent, pos, scale, tex_scale, hpr=None, vertical=True, bitmask=BitMask32.bit(3)):
        if not hpr:
            hpr = Vec3(0, 0, 0) if vertical else Vec3(0, 90, 0)

        pole = Cylinder(name, parent, self.cylinder, pos, hpr, scale, bitmask)
        pole.setTexScale(TextureStage.getDefault(), tex_scale)

        self.world.attachRigidBody(pole.node())
        return pole

    def room_camera(self, name, parent, pos):
        room_camera = NodePath(name)
        room_camera.reparentTo(parent)
        room_camera.setPos(pos)
        return room_camera

    def plane(self, name, parent, pos, rows, cols, size=2):
        model = NodePath(PandaNode(f'{name}Model'))
        card = CardMaker('card')
        half = size / 2
        card.setFrame(-half, half, -half, half)

        for r in range(rows):
            for c in range(cols):
                g = model.attachNewNode(card.generate())
                g.setP(-90)
                x = (c - cols / 2) * size
                y = (r - rows / 2) * size
                g.setPos(x, y, 0)

        plane = Plane(name, parent, model, pos)
        self.world.attachRigidBody(plane.node())

        return plane

    def point_on_circumference(self, angle, radius):
        rad = math.radians(angle)
        x = math.cos(rad) * radius
        y = math.sin(rad) * radius

        return x, y

    def tube(self, name, parent, pos, scale, hpr=None, horizontal=True, **kwargs):
        if not hpr:
            hpr = Vec3(0, 90, 0) if horizontal else Vec3(90, 0, 0)

        geomnode = make_tube(**kwargs)
        tube = Ring(name, parent, geomnode, pos, hpr, scale, BitMask32.allOn())
        self.world.attachRigidBody(tube.node())

        return tube

    def torus(self, name, parent, pos, scale, tex_scale, hpr=None, horizontal=True, **kwargs):
        if not hpr:
            hpr = Vec3(0, 90, 0) if horizontal else Vec3(90, 0, 0)

        geomnode = make_torus(**kwargs)
        torus = Ring(name, parent, geomnode, pos, hpr, scale, BitMask32.allOn())
        torus.setTexScale(TextureStage.getDefault(), tex_scale)
        self.world.attachRigidBody(torus.node())

        return torus


class StoneHouse(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('stoneHouse'))
        self.house.reparentTo(parent)
        self.house.setPos(center)
        self.house.setH(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.FIELD_STONE)    # for walls
        self.floor_tex = self.texture(Images.IRON)          # for floors, steps and roof
        self.door_tex = self.texture(Images.BOARD)          # for doors
        self.column_tex = self.texture(Images.CONCRETE)     # for columns

    def build(self):
        self.make_textures()
        walls = NodePath(PandaNode('walls'))
        walls.reparentTo(self.house)
        floors = NodePath(PandaNode('floors'))
        floors.reparentTo(self.house)
        doors = NodePath(PandaNode('doors'))
        doors.reparentTo(self.house)
        columns = NodePath(PandaNode('columns'))
        columns.reparentTo(self.house)

        # columns
        materials = (Point3(x, y, -3) for x, y in product((-15, 15), (-11, 11)))
        for i, pos in enumerate(materials):
            self.pole(f'column_{i}', columns, pos, Vec3(1, 1, 9), Vec2(1, 1))

        # the 1st outside floor
        materials = [
            [Point3(-11, 0, 0), Vec3(10, 1, 24)],          # left
            [Point3(11, 0, 0), Vec3(10, 1, 24)],           # right
            [Point3(0, -10, 0), Vec3(12, 1, 4)],           # front
            [Point3(0, 10, 0), Vec3(12, 1, 4)]             # back
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'floor1_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0))

        # room and room camera on the 1st floor
        self.block('room1', floors, Point3(0, 0, 0), Vec3(12, 1, 16), hpr=Vec3(0, 90, 0))
        self.room_camera('room1_camera', self.house, Point3(0, 0, 6.25))

        # right and left walls on the 1st floor
        materials = [
            [Point3(-5.75, 0, 3.5), Vec3(16, 0.5, 6)],          # left
            [Point3(5.75, 0, 1.5), Vec3(16, 0.5, 2)],           # right under
            [Point3(5.75, 3, 3.5), Vec3(10, 0.5, 2)],           # right middle back
            [Point3(5.75, -7, 3.5), Vec3(2, 0.5, 2)],           # right front
            [Point3(5.75, 0, 5.5), Vec3(16, 0.5, 2)],           # right top
            [Point3(-13.75, -4.25, 7), Vec3(8.5, 0.5, 13)]      # left side of the steps
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_side{i}', walls, pos, scale, horizontal=False)

        # front and rear walls on the 1st floor
        materials = [
            [Point3(0, 8.25, 3.5), Vec3(12, 0.5, 6)],           # rear
            [Point3(0, -8.25, 5.5), Vec3(12, 0.5, 2)],          # front top
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_fr{i}', walls, pos, scale)

        wall1_l = self.block('wall1_fl', walls, Point3(-4, -8.25, 2.5), Vec3(4, 0.5, 4))    # front left
        wall1_r = self.block('wall1_fr', walls, Point3(4, -8.25, 2.5), Vec3(4, 0.5, 4))     # front right

        # 2nd floor
        materials = [
            [Point3(4, -4.25, 6.75), Vec3(20, 0.5, 8.5), BitMask32.bit(1)],
            [Point3(-9.75, -1, 6.75), Vec3(7.5, 0.5, 2), BitMask32.bit(2)]
        ]
        for i, (pos, scale, mask) in enumerate(materials):
            self.block(f'floor2_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0), bitmask=mask)

        # room and room camera on the 2nd floor
        self.block('room2', floors, Point3(-4, 4.25, 6.75), Vec3(20, 0.5, 8.5), hpr=Vec3(0, 90, 0))
        self.room_camera('room2_camera', self.house, Point3(-10, 4, 13))

        # balcony fence
        materials = [
            [Point3(4, -8.25, 7.5), Vec3(0.5, 1, 20), Vec3(0, 90, 90)],
            [Point3(-5.75, -5, 7.5), Vec3(0.5, 1, 6), Vec3(0, 90, 0)],
            [Point3(13.75, -4, 7.5), Vec3(0.5, 1, 8), Vec3(0, 90, 0)],
            [Point3(10, 0.25, 7.25), Vec3(0.5, 1.5, 8), Vec3(0, 90, 90)]
        ]
        for i, (pos, scale, hpr) in enumerate(materials):
            self.block(f'balcony_{i}', floors, pos, scale, hpr=hpr)

        # left and right walls on the 2nd floor
        materials = [
            [Point3(-13.75, 4, 8), Vec3(8, 0.5, 2)],         # left
            [Point3(-13.75, 1.5, 10), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 6.5, 10), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 4, 12), Vec3(8, 0.5, 2)],        # left
            [Point3(5.75, 4.25, 10), Vec3(7.5, 0.5, 6)]      # right
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall2_side{i}', walls, pos, scale, horizontal=False)

        # front and rear walls on the 2nd floor
        wall2_l = self.block('wall2_l', walls, Point3(-12.5, 0.25, 9), Vec3(2, 0.5, 4))

        materials = [
            [Point3(-4, 8.25, 10), Vec3(20, 0.5, 6)],        # rear
            [Point3(-7.25, 0.25, 9), Vec3(2.5, 0.5, 4)],     # front
            [Point3(-9.75, 0.25, 12), Vec3(7.5, 0.5, 2)],    # front
            [Point3(0, 0.25, 8), Vec3(12, 0.5, 2)],          # front
            [Point3(-4, 0.25, 10), Vec3(4, 0.5, 2)],         # front
            [Point3(4, 0.25, 10), Vec3(4, 0.5, 2)],          # front
            [Point3(0, 0.25, 12), Vec3(12, 0.5, 2)]          # front
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall2_fr{i}', walls, pos, scale)

        # roof
        self.block('roof', floors, Point3(-4, 4.25, 13.25), Vec3(20, 8.5, 0.5))

        # steps
        steps = [
            ([Point3(-9.75, -7.5 + i, 1 + i), Vec3(7.5, 1, 1)] for i in range(6)),  # steps that leads to the 2nd floor
            ([Point3(0, 12.5 + i, 0 - i), Vec3(32, 1, 1)] for i in range(4))        # steps that leade to the 1st floor
        ]
        for i, (pos, scale) in enumerate(chain(*steps)):
            self.block(f'step_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0), bitmask=BitMask32.bit(2))

        # doors
        materials = [
            [Point3(-1, -8.25, 2.5), Vec3(2, 0.5, 4), wall1_l, True],    # left door of the room on the 1st floor
            [Point3(1, -8.25, 2.5), Vec3(2, 0.5, 4), wall1_r, False],    # left door of the room on the 1st floor
            [Point3(-10, 0.25, 9), Vec3(3, 0.5, 4), wall2_l, True]       # foor ofr the room on the 2nd floor
        ]
        for i, (pos, scale, body, hinge) in enumerate(materials):
            self.door(f'door_{i}', doors, pos, scale, body, horizontal=True, left_hinge=hinge)

        doors.setTexture(self.door_tex)
        walls.setTexture(self.wall_tex)
        floors.setTexture(self.floor_tex)
        columns.setTexture(self.column_tex)


class BrickHouse(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('brickHouse'))
        self.house.reparentTo(parent)
        self.house.setPos(center)
        self.house.setH(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.BRICK)      # for walls
        self.floor_tex = self.texture(Images.CONCRETE)  # for floors
        self.roof_tex = self.texture(Images.IRON)       # for roofs
        self.door_tex = self.texture(Images.BOARD)      # for doors

    def build(self):
        self.make_textures()
        floors = NodePath('foundation')
        floors.reparentTo(self.house)
        walls = NodePath('wall')
        walls.reparentTo(self.house)
        roofs = NodePath('roof')
        roofs.reparentTo(self.house)
        doors = NodePath('door')
        doors.reparentTo(self.house)

        # floors
        materials = [
            [Point3(0, 0, 0), Vec3(13, 9, 3)],     # big room
            [Point3(3, -6.5, 0), Vec3(7, 4, 3)],   # small room
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'room_brick{i}', floors, pos, scale)

        # room_camera
        self.room_camera('room_brick1_camera', self.house, Point3(3, 3, 5.5))

        # steps
        steps = ([Point3(3, -9.5 - i * 2, 0 - 0.5 * i), Vec3(4, 2, 3 - i)] for i in range(3))
        for i, (pos, scale) in enumerate(steps):
            self.block(f'step_{i}', floors, pos, scale, bitmask=BitMask32.bit(2))

        # rear and front walls
        wall1_l = self.block('wall1_l', walls, Point3(1, -8.25, 3.25), Vec3(2, 0.5, 3.5))
        materials = [
            [Point3(0, 4.25, 5.5), Vec3(12, 0.5, 8)],        # rear
            [Point3(5, -8.25, 3.25), Vec3(2, 0.5, 3.5)],     # front right
            [Point3(3, -8.25, 5.25), Vec3(6, 0.5, 0.5)],     # front_top
            [Point3(-1.5, -4.25, 5.5), Vec3(2, 0.5, 8)],     # back room front right
            [Point3(-5.25, -4.25, 5.5), Vec3(1.5, 0.5, 8)],  # back room front left
            [Point3(-3.5, -4.25, 3.0), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(-3.5, -4.25, 8.0), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(3, -4.25, 7.5), Vec3(7, 0.5, 4)],        # back room front
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_fr{i}', walls, pos, scale)

        # side walls
        materials = [
            [Point3(-0.25, -6.25, 3.5), Vec3(4.5, 0.5, 4)],    # left
            [Point3(-6.25, -3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 0, 3.0), Vec3(3, 0.5, 3)],
            [Point3(-6.25, 0, 8.0), Vec3(3, 0.5, 3)],
            [Point3(6.25, -6.25, 3.5), Vec3(4.5, 0.5, 4)],     # right
            [Point3(6.25, -2.75, 5.5), Vec3(2.5, 0.5, 8)],
            [Point3(6.25, 3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(6.25, 0, 3.0), Vec3(3, 0.5, 3)],
            [Point3(6.25, 0, 8.0), Vec3(3, 0.5, 3)]
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_side{i}', walls, pos, scale, horizontal=False)

        # roofs
        materials = [
            [Point3(3, -6.5, 5.75), Vec3(7, 4, 0.5)],       # small room
            [Point3(3, -6.5, 6.0), Vec3(6, 3, 0.5)],        # small room
            [Point3(0, 0, 9.75), Vec3(13, 9, 0.5)],         # big room
            [Point3(0, 0, 10.0), Vec3(12, 8, 0.5)],         # big room
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'roof_{i}', roofs, pos, scale)

        # doors
        self.door('door_1', doors, Point3(3, -8.25, 3.25), Vec3(2, 0.5, 3.5), wall1_l)

        floors.setTexture(self.floor_tex)
        walls.setTexture(self.wall_tex)
        roofs.setTexture(self.roof_tex)
        doors.setTexture(self.door_tex)


class Terrace(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.terrace = NodePath(PandaNode('terrace'))
        self.terrace.reparentTo(parent)
        self.terrace.setPos(center)
        self.terrace.setH(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.LAYINGBROCK)    # for walls
        self.floor_tex = self.texture(Images.COBBLESTONES)  # for floor
        self.roof_tex = self.texture(Images.IRON)           # for roofs
        self.steps_tex = self.texture(Images.METALBOARD)    # for steps

    def build(self):
        self.make_textures()
        floors = NodePath('floors')
        floors.reparentTo(self.terrace)
        walls = NodePath('walls')
        walls.reparentTo(self.terrace)
        roofs = NodePath('roofs')
        roofs.reparentTo(self.terrace)
        steps = NodePath('steps')
        steps.reparentTo(self.terrace)

        # the 1st floor
        self.block('floor1', floors, Point3(0, 0, 0), Vec3(16, 0.5, 12), hpr=Vec3(0, 90, 0), bitmask=BitMask32.bit(2))

        # walls
        self.block('wall1_r', walls, Point3(-5.5, 5.75, 3.25), Vec3(5, 0.5, 6))                       # rear
        self.block('wall1_r', walls, Point3(-7.75, 3.25, 3.25), Vec3(4.5, 0.5, 6), horizontal=False)  # side

        materials = (Point3(x, y, 2) for x, y in product((-7.5, 7.5), (-5.5, 5.5)))
        for i, pos in enumerate(materials):
            self.pole(f'column_{i}', walls, pos, Vec3(0.25, 0.25, 16), Vec2(1, 3))

        # roof
        self.block('roof', roofs, Point3(0, 0, 6.5), Vec3(16, 0.5, 12), hpr=Vec3(0, 90, 0))

        # fall prevention blocks
        materials = [
            [Point3(0, 5.75, 7.25), Vec3(16, 0.5, 1), True],        # rear
            [Point3(0, -5.75, 7.25), Vec3(16, 0.5, 1), True],       # front
            [Point3(-7.75, 0, 7.25), Vec3(11, 0.5, 1), False],      # left
            [Point3(7.75, -1.75, 7.25), Vec3(7.5, 0.5, 1), False]   # right
        ]
        for i, (pos, scale, hor) in enumerate(materials):
            self.block(f'prevention_{i}', roofs, pos, scale, horizontal=hor)

        # spiral staircase
        center = Point3(9, 1.5, 3.5)
        self.pole('center_pole', steps, center, Vec3(0.15, 0.15, 16), Vec2(1, 3))

        for i in range(7):
            angle = -90 + 30 * i
            x, y = self.point_on_circumference(angle, 2.5)
            pos = Point3(center.x + x, center.y + y, i + 0.5)
            self.block(f'step_{i}', steps, pos, Vec3(4, 0.5, 2), hpr=Vec3(angle, 90, 0), bitmask=BitMask32.bit(2))

        # handrail
        for i in range(21):
            if i % 3 == 0:
                h = 1.7 + i // 3

            angle = -100 + 10 * i
            x, y = self.point_on_circumference(angle, 4.3)
            rail_h = h + (i % 3 * 0.1)
            pos = Point3(center.x + x, center.y + y, rail_h)
            self.pole(f'fence_{i}', steps, pos, Vec3(0.05, 0.05, 3.5 + i % 3), Vec2(1, 2))

        walls.setTexture(self.wall_tex)
        floors.setTexture(self.floor_tex)
        roofs.setTexture(self.roof_tex)
        steps.setTexture(self.steps_tex)
        self.terrace.flatten_strong()


class Observatory(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.observatory = NodePath(PandaNode('observatory'))
        self.observatory.reparentTo(parent)
        self.observatory.setPos(center)
        self.observatory.setH(h)

    def make_textures(self):
        self.steps_tex = self.texture(Images.METALBOARD)   # for steps
        self.landing_tex = self.texture(Images.CONCRETE2)  # for floors
        self.posts_tex = self.texture(Images.IRON)         # for posts

    def build(self):
        self.make_textures()
        steps = NodePath('steps')
        steps.reparentTo(self.observatory)
        landings = NodePath('landings')
        landings.reparentTo(self.observatory)
        posts = NodePath('posts')
        posts.reparentTo(self.observatory)

        # spiral staircase
        center = Point3(10, 0, 9)
        self.pole('center_pole', posts, center, Vec3(0.15, 0.15, 32), Vec2(1, 3))

        for i in range(19):
            angle = -90 + 30 * i
            x, y = self.point_on_circumference(angle, 2.5)
            pos = Point3(center.x + x, center.y + y, i + 0.5)
            self.block(f'step_{i}', steps, pos, Vec3(4, 0.5, 2), hpr=Vec3(angle, 90, 0), bitmask=BitMask32.bit(2))

        # handrail
        for i in range(57):
            if i % 3 == 0:
                h = 1.7 + i // 3

            angle = -100 + 10 * i
            x, y = self.point_on_circumference(angle, 4.3)
            rail_h = h + (i % 3 * 0.1)
            pos = Point3(center.x + x, center.y + y, rail_h)
            self.pole(f'handrail_{i}', steps, pos, Vec3(0.05, 0.05, 3.5 + i % 3), Vec2(1, 2))

        # stair landings
        materials = [
            Point3(7, 2.5, 18.5),
            Point3(7, 9.5, 15.5),
            Point3(0, 9.5, 12.5),
            Point3(-7, 9.5, 9.5),
            Point3(-7, 2.5, 6.5),
            Point3(-14, 2.5, 3.5)
        ]
        for i, pos in enumerate(materials):
            self.block(f'floor_{i}', landings, pos, Vec3(4, 0.5, 4), hpr=Vec3(0, 90, 0), bitmask=BitMask32.bit(2))

        # support post
        materials = [
            [Point3(-14, 2.5, 1.5), Vec3(0.15, 0.15, 6)],
            [Point3(-7, 2.5, 3), Vec3(0.15, 0.15, 12)],
            [Point3(-7, 9.5, 4), Vec3(0.15, 0.15, 18)],
            [Point3(0, 9.5, 5), Vec3(0.15, 0.15, 24)],
            [Point3(7, 9.5, 6), Vec3(0.15, 0.15, 30)],

        ]
        for i, (pos, scale) in enumerate(materials):
            self.pole(f'support_{i}', posts, pos, scale, Vec2(1, 3))

        # steps
        materials = [
            ([Point3(7, 5 + i, 18.25 - i), True] for i in range(3)),
            ([Point3(4.5 - i, 9.5, 15.25 - i), False] for i in range(3)),
            ([Point3(-2.5 - i, 9.5, 12.25 - i), False] for i in range(3)),
            ([Point3(-7, 7 - i, 9.25 - i), True] for i in range(3)),
            ([Point3(-9.5 - i, 2.5, 6.25 - i), False] for i in range(3)),
            ([Point3(-16.5 - i, 2.5, 3.25 - i), False] for i in range(3))
        ]
        for i, (pos, hor) in enumerate(chain(*materials)):
            self.block(f'step_{i}', steps, pos, Vec3(4, 1, 1), horizontal=hor, bitmask=BitMask32.bit(2))

            # falling preventions
            for f in [1.875, -1.875]:
                diff = Vec3(f, 0, 1.5) if hor else Vec3(0, f, 1.5)
                fence_pos = pos + diff
                self.pole(f'fence_{i}', steps, fence_pos, Vec3(0.05, 0.05, 3.5), Vec2(1, 2))

        materials = [
            (Point3(-15.5 + i, 4.375, 4.6) for i in range(4)),
            (Point3(-15.5 + i, 0.625, 4.6) for i in range(4)),
            (Point3(-8.5 + i, 0.625, 7.6) for i in range(4)),
            (Point3(-5.125, 4 - i, 7.6) for i in range(4)),
            (Point3(-8.5 + i, 11.375, 10.6) for i in range(4)),
            (Point3(-8.875, 8 + i, 10.6) for i in range(4)),
            (Point3(-1.5 + i, 7.625, 13.6) for i in range(4)),
            (Point3(-1.5 + i, 11.375, 13.6) for i in range(4)),
            (Point3(5.5 + i, 11.375, 16.6) for i in range(4)),
            (Point3(8.875, 8 + i, 16.6) for i in range(4)),
            (Point3(5.5 + i, 0.625, 19.6) for i in range(6)),
            (Point3(5.125, 1 + i, 19.6) for i in range(4))
        ]
        for i, pos in enumerate(chain(*materials)):
            self.pole(f'fence_landing_{i}', steps, pos, Vec3(0.05, 0.05, 4), Vec2(1, 2))

        steps.setTexture(self.steps_tex)
        landings.setTexture(self.landing_tex)
        posts.setTexture(self.posts_tex)
        self.observatory.flatten_strong()


class Bridge(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.bridge = NodePath(PandaNode('bridge'))
        self.bridge.reparentTo(parent)
        self.bridge.setPos(center)
        self.bridge.setH(h)

    def make_textures(self):
        self.bridge_tex = self.texture(Images.IRON)         # for bridge girder
        self.column_tex = self.texture(Images.CONCRETE)     # for columns
        self.fence_tex = self.texture(Images.METALBOARD)    # for fences

    def build(self):
        self.make_textures()
        girder = NodePath('girder')
        girder.reparentTo(self.bridge)
        columns = NodePath('columns')
        columns.reparentTo(self.bridge)
        fences = NodePath('fences')
        fences.reparentTo(self.bridge)

        # columns supporting bridge girder
        materials = [
            (Point3(x, y, -3) for x, y in product((3, -3), (3, -3))),
            (Point3(0, y, -3) for y in (12, -12))
        ]
        for i, pos in enumerate(chain(*materials)):
            self.pole(f'column_{i}', columns, pos, Vec3(1, 1, 9), Vec2(1, 1))

        # bridge girder
        materials = [
            [Point3(0, 0, 0), Vec3(8, 1, 8)],
            [Point3(0, 12, 0), Vec3(4, 1, 16)],
            [Point3(0, -12, 0), Vec3(4, 1, 16)],
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'girder_{i}', girder, pos, scale, hpr=Vec3(0, 90, 0))

        # steps
        materials = (Point3(0, -20.5 - i, 0 - i) for i in range(5))
        for i, pos in enumerate(materials):
            self.block(f'step_{i}', girder, pos, Vec3(4, 1, 1), bitmask=BitMask32.bit(2))

        # fences
        materials = [
            (Point3(x, y + i, 1) for i in range(16) for x, y in product((1.9, -1.9), (4.5, -19.5))),
            (Point3(x + i, y, 1) for i in range(2) for x, y in product((-3.5, 2.5), (-3.9, 3.9))),
            (Point3(x, -3.5 + i, 1) for i in range(8) for x in (-3.9, 3.9)),
            (Point3(x, -20.5 - i, 1 - i) for i in range(5) for x in (1.9, -1.9))
        ]
        for i, pos in enumerate(chain(*materials)):
            self.pole(f'fence_{i}', fences, pos, Vec3(0.05, 0.05, 3), Vec2(1, 2))

        girder.setTexture(self.bridge_tex)
        columns.setTexture(self.column_tex)
        fences.setTexture(self.fence_tex)
        self.bridge.flatten_strong()


class Tunnel(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.tunnel = NodePath(PandaNode('tunnel'))
        self.tunnel.reparentTo(parent)
        self.tunnel.setPos(center)
        self.tunnel.setH(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.IRON)           # for tunnel
        self.metal_tex = self.texture(Images.METALBOARD)
        self.pedestal_tex = self.texture(Images.FIELD_STONE)

    def build(self):
        self.make_textures()
        walls = NodePath('wall')
        walls.reparentTo(self.tunnel)
        metal = NodePath('rings')
        metal.reparentTo(self.tunnel)
        pedestals = NodePath('pedestals')
        pedestals.reparentTo(self.tunnel)

        # tunnel
        self.tube('tunnel', walls, Point3(0, 0, 0), Vec3(4, 4, 4), height=20)

        positions = [Point3(0, 0, 0), Point3(0, -80, 0)]
        for i, pos in enumerate(positions):
            self.torus(f'edge_{i}', walls, pos, Vec3(4, 4, 4), Vec2(2, 2), ring_radius=0.5, section_radius=0.05)

        # steps
        materials = [
            (Point3(0, 0.75 + i, -2.5 - i) for i in range(5)),
            (Point3(0, -80.75 - i, -2.5 - i) for i in range(5))
        ]
        for i, pos in enumerate(chain(*materials)):
            self.block(f'step_{i}', walls, pos, Vec3(4, 1, 1), bitmask=BitMask32.bit(2))

        # falling preventions
        materials = [
            (Point3(x, 0.75 + i, -1.5 - i) for i in range(5) for x in [1.9, -1.9]),
            (Point3(x, -80.75 - i, -1.5 - i) for i in range(5) for x in [1.9, -1.9]),
        ]
        for i, pos in enumerate(chain(*materials)):
            self.pole(f'fence_{i}', metal, pos, Vec3(0.05, 0.05, 3), Vec2(1, 2))

        # rings supporting tunnel
        positions = (Point3(0, -20 * i, 0) for i in range(5))
        for i, pos in enumerate(positions):
            self.torus(f'edge_{i}', metal, pos, Vec3(5, 5, 5), Vec2(2, 4), ring_radius=0.8, section_radius=0.1)

        # poles of rings
        materials = [
            (Point3(0, -20 * i, z) for i in range(5) for z in [3, -3]),
            (Point3(x, -20 * i, 0) for i in range(5) for x in [3, -3])
        ]
        for i, pos in enumerate(chain(*materials)):
            kwargs = dict(vertical=True) if pos.x == 0 else dict(hpr=Vec3(90, 90, 0))
            self.pole(f'pole_{i}', metal, pos, Vec3(0.5, 0.5, 3), Vec2(1, 1), **kwargs)

        # culumns supporting rings
        positions = (Point3(0, -20 * i, -7.3) for i in range(5))
        for i, pos in enumerate(positions):
            self.block(f'column_{i}', pedestals, pos, Vec3(2, 2, 6))

        walls.setTexture(self.wall_tex)
        metal.setTexture(self.metal_tex)
        pedestals.setTexture(self.pedestal_tex)
        self.tunnel.flatten_strong()
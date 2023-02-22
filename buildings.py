import array
import math

from panda3d.core import Vec3, Vec2, LColor, Point3, Point2
from panda3d.core import Geom, GeomNode, GeomTriangles
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat
from panda3d.core import CardMaker, Texture, TextureStage

from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape, BulletPlaneShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletConeTwistConstraint

import numpy as np


def get_prim_indices(start, n):
    match n:
        case 3:
            yield (start, start + 1, start + 2)
        case 4:
            for x, y, z in [(0, 1, 3), (1, 2, 3)]:
                yield (start + x, start + y, start + z)
        case _:
            for i in range(2, n):
                if i == 2:
                    yield (start, start + i - 1, start + i)
                else:
                    yield (start + i - 1, start, start + i)


def calc_uv(vertices):
    """
    vertices: list of Vec3
    """
    total = Vec3()
    length = len(vertices)
    for vertex in vertices:
        total += vertex
    center = total / length

    pt = vertices[0]
    vec = pt - center
    radius = sum(v ** 2 for v in vec) ** 0.5

    for vertex in vertices:
        nm = (vertex - center) / radius
        phi = np.arctan2(nm.z, nm.x)
        theta = np.arcsin(nm.y)
        u = (phi + np.pi) / (2 * np.pi)
        v = (theta + np.pi / 2) / np.pi
        yield Vec2(u, v)


# def make_geomnode(faces, texcoords, normal_vecs):
def make_geomnode(faces, texcoords):
    arr_format = GeomVertexArrayFormat()
    arr_format.addColumn('vertex', 3, Geom.NTFloat32, Geom.CPoint)
    arr_format.addColumn('color', 4, Geom.NTFloat32, Geom.CColor)
    # arr_format.addColumn('normal', 3, Geom.NTFloat32, Geom.CNormal)
    arr_format.addColumn('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
    format_ = GeomVertexFormat.registerFormat(arr_format)

    vdata_values = array.array('f', [])
    prim_indices = array.array('H', [])
    start = 0

    # for face, coords, vecs in zip(faces, texcoords, normal_vecs):
    for face, coords in zip(faces, texcoords):
        for pt, uv in zip(face, coords):
            vdata_values.extend(pt)
            vdata_values.extend(LColor(1, 1, 1, 1))
            # vdata_values.extend(pt.normalized())
            # vdata_values.extend(vec)
            # vdata_values.extend((0, 0, 0))
            vdata_values.extend(uv)

        for indices in get_prim_indices(start, len(face)):
            prim_indices.extend(indices)
        start += len(face)

    vdata = GeomVertexData('cube', format_, Geom.UHStatic)
    num_rows = sum(len(face) for face in faces)
    vdata.uncleanSetNumRows(num_rows)
    vdata_mem = memoryview(vdata.modifyArray(0)).cast('B').cast('f')
    vdata_mem[:] = vdata_values

    prim = GeomTriangles(Geom.UHStatic)
    prim_array = prim.modifyVertices()
    prim_array.uncleanSetNumRows(len(prim_indices))
    prim_mem = memoryview(prim_array).cast('B').cast('H')
    prim_mem[:] = prim_indices

    node = GeomNode('geomnode')
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node.addGeom(geom)

    return node


class Block(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask=1):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = model.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)
        end, tip = self.model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(bitmask))


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
        # self.node().addShape(BulletPlaneShape(Vec3.up(), 0))


class Cylinder(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask=1):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = model.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)
        shape = BulletConvexHullShape()
        shape.addGeom(self.model.node().getGeom(0))
        self.node().addShape(shape)
        self.setCollideMask(BitMask32.bit(bitmask))


# class TriangularPrism(NodePath):

#     def __init__(self, name, parent, np, pos, hpr, scale, bitmask=1):
#         super().__init__(name, parent, np, pos, hpr, scale)
#         shape = BulletConvexHullShape()
#         shape.addGeom(self.model.node().getGeom(0))
#         self.node().addShape(shape)
#         self.setCollideMask(BitMask32.bit(bitmask))


class CubeModel(NodePath):

    def __new__(cls, *args, **kargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(CubeModel, cls).__new__(cls)
        return cls._instance

    def __init__(self, nd):
        super().__init__(nd)
        self.setTwoSided(True)


class Materials:

    def __init__(self, world):
        self.world = world
        self.cube = self.make_cube()
        self.cylinder = self.make_cylinder()

    def make_cylinder(self):
        vertices = DECAGONAL_PRISM['vertices']
        idx_faces = DECAGONAL_PRISM['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]
        uv = DECAGONAL_PRISM['uv']

        geomnode = make_geomnode(faces, uv)
        cylinder = NodePath(geomnode)
        cylinder.setTwoSided(True)
        return cylinder

    def make_cube(self):
        vertices = CUBE['vertices']
        idx_faces = CUBE['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]
        uv = CUBE['uv']

        normal_vecs = [
            [Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0)],
            [Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0)],
            [Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1)],
            [Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0)],
            [Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0)],
            [Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1)]
        ]

        geomnode = make_geomnode(faces, uv)
        # cube = CubeModel(geomnode) # copyto -> NodePathを継承して作った自作クラスのメソッドはコピーされない
        cube = NodePath(geomnode)
        cube.setTwoSided(True)
        return cube

    def block(self, name, parent, pos, scale, hpr=None, horizontal=True, active_always=False, bitmask=1):
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
        knob = Block('knob', parent, self.cube, pos, hpr, scale)
        knob.setColor(0, 0, 0, 1)

    def door(self, name, parent, pos, scale, static_body, hpr=None, horizontal=True, left_hinge=True):
        door = self.block(name, parent, pos, scale, hpr, horizontal, active_always=True)
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

    def pole(self, name, parent, pos, scale, tex_scale, hpr=None, vertical=True, bitmask=1):
        if not hpr:
            hpr = Vec3(0, 0, 0) if vertical else Vec3(0, 90, 0)

        pole = Cylinder(name, parent, self.cylinder, pos, hpr, scale, bitmask=1)
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


class StoneHouse(Materials):

    def __init__(self, world, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('stoneHouse'))
        self.house.reparentTo(base.render)
        self.house.setPos(center)
        self.house.setH(h)

    def make_textures(self):
        # for walls
        self.wall_tex = base.loader.loadTexture('textures/fieldstone.jpg')
        self.wall_tex.setWrapU(Texture.WM_repeat)
        self.wall_tex.setWrapV(Texture.WM_repeat)
        # for floors, steps and roof
        self.floor_tex = base.loader.loadTexture('textures/iron.jpg')
        self.floor_tex.setWrapU(Texture.WM_repeat)
        self.floor_tex.setWrapV(Texture.WM_repeat)

        # for doors
        self.door_tex = base.loader.loadTexture('textures/board.jpg')
        self.door_tex.setWrapU(Texture.WM_repeat)
        self.door_tex.setWrapV(Texture.WM_repeat)

    def build(self):
        self.make_textures()
        walls = NodePath(PandaNode('walls'))
        walls.reparentTo(self.house)
        floors = NodePath(PandaNode('floors'))
        floors.reparentTo(self.house)
        doors = NodePath(PandaNode('doors'))
        doors.reparentTo(self.house)

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
            [Point3(4, -4.25, 6.75), Vec3(20, 0.5, 8.5), 1],
            [Point3(-9.75, -1, 6.75), Vec3(7.5, 0.5, 2), 2]
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
        steps = [Point3(-9.75, -7.5 + i, 1 + i) for i in range(6)]
        for i, pos in enumerate(steps):
            self.block(f'step_{i}', floors, pos, Vec3(7.5, 1, 1), hpr=Vec3(0, 90, 0), bitmask=2)

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


class BrickHouse(Materials):

    def __init__(self, world, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('brickHouse'))
        self.house.reparentTo(base.render)
        self.house.setPos(center)
        self.house.setH(h)

    def make_textures(self):
        # for walls
        self.wall_tex = base.loader.loadTexture('textures/brick.jpg')
        self.wall_tex.setWrapU(Texture.WM_repeat)
        self.wall_tex.setWrapV(Texture.WM_repeat)

        # for floors
        self.floor_tex = base.loader.loadTexture('textures/concrete.jpg')
        self.floor_tex.setWrapU(Texture.WM_repeat)
        self.floor_tex.setWrapV(Texture.WM_repeat)

        # for roofs
        self.roof_tex = base.loader.loadTexture('textures/iron.jpg')
        self.roof_tex.setWrapU(Texture.WM_repeat)
        self.roof_tex.setWrapV(Texture.WM_repeat)

        # for doors
        self.door_tex = base.loader.loadTexture('textures/board.jpg')
        self.door_tex.setWrapU(Texture.WM_repeat)
        self.door_tex.setWrapV(Texture.WM_repeat)

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
            [Point3(0, 0, 0), Vec3(13, 9, 2)],     # big room
            [Point3(3, -6.5, 0), Vec3(7, 4, 2)],   # small room
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'room_brick{i}', floors, pos, scale)

        # room_camera
        self.room_camera('room_brick1_camera', self.house, Point3(3, 3, 5))

        # steps
        steps = [
            [Point3(3, -9.5, 0), Vec3(4, 2, 2)],
            [Point3(3, -11.5, -0.5), Vec3(4, 2, 1)],
        ]
        for i, (pos, scale) in enumerate(steps):
            self.block(f'step_{i}', floors, pos, scale, bitmask=2)

        # rear and front walls
        wall1_l = self.block('wall1_l', walls, Point3(1, -8.25, 2.75), Vec3(2, 0.5, 3.5))

        materials = [
            [Point3(0, 4.25, 5), Vec3(12, 0.5, 8)],          # rear
            [Point3(5, -8.25, 2.75), Vec3(2, 0.5, 3.5)],     # front right
            [Point3(3, -8.25, 4.75), Vec3(6, 0.5, 0.5)],     # front_top
            [Point3(-1.5, -4.25, 5), Vec3(2, 0.5, 8)],       # back room front right
            [Point3(-5.25, -4.25, 5), Vec3(1.5, 0.5, 8)],    # back room front left
            [Point3(-3.5, -4.25, 2.5), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(-3.5, -4.25, 7.5), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(3, -4.25, 7), Vec3(7, 0.5, 4)],          # back room front
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_fr{i}', walls, pos, scale)

        # side walls
        materials = [
            [Point3(-0.25, -6.25, 3), Vec3(4.5, 0.5, 4)],    # left
            [Point3(-6.25, -3, 5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 3, 5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 0, 2.5), Vec3(3, 0.5, 3)],
            [Point3(-6.25, 0, 7.5), Vec3(3, 0.5, 3)],
            [Point3(6.25, -6.25, 3), Vec3(4.5, 0.5, 4)],     # right
            [Point3(6.25, -2.75, 5), Vec3(2.5, 0.5, 8)],
            [Point3(6.25, 3, 5), Vec3(3, 0.5, 8)],
            [Point3(6.25, 0, 2.5), Vec3(3, 0.5, 3)],
            [Point3(6.25, 0, 7.5), Vec3(3, 0.5, 3)]
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_side{i}', walls, pos, scale, horizontal=False)

        # roofs
        materials = [
            [Point3(3, -6.5, 5.25), Vec3(7, 4, 0.5)],       # small room
            [Point3(3, -6.5, 5.5), Vec3(6, 3, 0.5)],        # small room
            [Point3(0, 0, 9.25), Vec3(13, 9, 0.5)],         # big room
            [Point3(0, 0, 9.5), Vec3(12, 8, 0.5)],          # big room
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'roof_{i}', roofs, pos, scale)

        # doors
        self.door('door_1', doors, Point3(3, -8.25, 2.75), Vec3(2, 0.5, 3.5), wall1_l, )

        floors.setTexture(self.floor_tex)
        walls.setTexture(self.wall_tex)
        roofs.setTexture(self.roof_tex)
        doors.setTexture(self.door_tex)


class Terrace(Materials):

    def __init__(self, world, center, h=0):
        super().__init__(world)
        self.terrace = NodePath(PandaNode('terrace'))
        self.terrace.reparentTo(base.render)
        self.terrace.setPos(center)
        self.terrace.setH(h)

    def make_textures(self):
        # for walls
        self.wall_tex = base.loader.loadTexture('textures/layingrock.jpg')
        self.wall_tex.setWrapU(Texture.WM_repeat)
        self.wall_tex.setWrapV(Texture.WM_repeat)

        # for floor
        self.floor_tex = base.loader.loadTexture('textures/cobblestones.jpg')
        self.floor_tex.setWrapU(Texture.WM_repeat)
        self.floor_tex.setWrapV(Texture.WM_repeat)

        # for roofs
        self.roof_tex = base.loader.loadTexture('textures/iron.jpg')
        self.roof_tex.setWrapU(Texture.WM_repeat)
        self.roof_tex.setWrapV(Texture.WM_repeat)

        # for steps
        self.steps_tex = base.loader.loadTexture('textures/metalboard.jpg ')
        self.steps_tex.setWrapU(Texture.WM_repeat)
        self.steps_tex.setWrapV(Texture.WM_repeat)

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
        self.block('floor1', floors, Point3(0, 0, 0), Vec3(16, 0.5, 12), hpr=Vec3(0, 90, 0))

        # walls
        self.block('wall1_r', walls, Point3(-5.5, 5.75, 3.25), Vec3(5, 0.5, 6))                       # rear
        self.block('wall1_r', walls, Point3(-7.75, 3.25, 3.25), Vec3(4.5, 0.5, 6), horizontal=False)  # side

        # columns
        materials = [
            [Point3(-7.5, -5.5, 3.25), Vec3(0.25, 0.25, 10.5)],
            [Point3(7.5, -5.5, 3.25), Vec3(0.25, 0.25, 10.5)],
            [Point3(7.5, 5.5, 3.25), Vec3(0.25, 0.25, 10.5)],
        ]
        for i, (pos, scale) in enumerate(materials):
            self.pole(f'column_{i}', walls, pos, scale, Vec2(1, 3))

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
        self.pole('center_pole', steps, center, Vec3(0.15, 0.15, 13), Vec2(1, 3))

        for i in range(7):
            angle = -90 + 30 * i
            x, y = self.point_on_circumference(angle, 2.5)
            pos = Point3(center.x + x, center.y + y, i + 0.5)
            self.block(f'step_{i}', steps, pos, Vec3(4, 0.5, 2), hpr=Vec3(angle, 90, 0), bitmask=2)

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


class Observatory(Materials):

    def __init__(self, world, center, h=0):
        super().__init__(world)
        self.observatory = NodePath(PandaNode('observatory'))
        self.observatory.reparentTo(base.render)
        self.observatory.setPos(center)
        self.observatory.setH(h)

    def make_textures(self):
        # for steps
        self.steps_tex = base.loader.loadTexture('textures/metalboard.jpg')
        self.steps_tex.setWrapU(Texture.WM_repeat)
        self.steps_tex.setWrapV(Texture.WM_repeat)

        # for floors
        self.landing_tex = base.loader.loadTexture('textures/concrete2.jpg')
        self.landing_tex.setWrapU(Texture.WM_repeat)
        self.landing_tex.setWrapV(Texture.WM_repeat)

        # for posts
        self.posts_tex = base.loader.loadTexture('textures/iron.jpg')
        self.posts_tex.setWrapU(Texture.WM_repeat)
        self.posts_tex.setWrapV(Texture.WM_repeat)

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
            self.block(f'step_{i}', steps, pos, Vec3(4, 0.5, 2), hpr=Vec3(angle, 90, 0), bitmask=2)

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
            self.block(f'floor_{i}', landings, pos, Vec3(4, 0.5, 4), hpr=Vec3(0, 90, 0), bitmask=2)

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
        materials = [[Point3(7, 5 + i, 18.25 - i), True] for i in range(3)]
        materials += [[Point3(4.5 - i, 9.5, 15.25 - i), False] for i in range(3)]
        materials += [[Point3(-2.5 - i, 9.5, 12.25 - i), False] for i in range(3)]
        materials += [[Point3(-7, 7 - i, 9.25 - i), True] for i in range(3)]
        materials += [[Point3(-9.5 - i, 2.5, 6.25 - i), False] for i in range(3)]
        materials += [[Point3(-16.5 - i, 2.5, 3.25 - i), False] for i in range(3)]

        for i, (pos, hor) in enumerate(materials):
            self.block(f'step_{i}', steps, pos, Vec3(4, 1, 1), horizontal=hor, bitmask=2)

            # falling preventions
            for f in [1.875, -1.875]:
                diff = Vec3(f, 0, 1.5) if hor else Vec3(0, f, 1.5)
                fence_pos = pos + diff
                self.pole(f'fence_{i}', steps, fence_pos, Vec3(0.05, 0.05, 3.5), Vec2(1, 2))

        # falling preventions for stair landings
        materials = [Point3(-15.5 + i, 4.375, 4.6) for i in range(4)]
        materials += [Point3(-15.5 + i, 0.625, 4.6) for i in range(4)]
        materials += [Point3(-8.5 + i, 0.625, 7.6) for i in range(4)]
        materials += [Point3(-5.125, 4 - i, 7.6) for i in range(4)]
        materials += [Point3(-8.5 + i, 11.375, 10.6) for i in range(4)]
        materials += [Point3(-8.875, 8 + i, 10.6) for i in range(4)]
        materials += [Point3(-1.5 + i, 7.625, 13.6) for i in range(4)]
        materials += [Point3(-1.5 + i, 11.375, 13.6) for i in range(4)]
        materials += [Point3(5.5 + i, 11.375, 16.6) for i in range(4)]
        materials += [Point3(8.875, 8 + i, 16.6) for i in range(4)]
        materials += [Point3(5.5 + i, 0.625, 19.6) for i in range(6)]
        materials += [Point3(5.125, 1 + i, 19.6) for i in range(4)]

        for i, pos in enumerate(materials):
            self.pole(f'fence_landing_{i}', steps, pos, Vec3(0.05, 0.05, 4), Vec2(1, 2))

        steps.setTexture(self.steps_tex)
        landings.setTexture(self.landing_tex)
        posts.setTexture(self.posts_tex)


CUBE = {
    'vertices': [
        (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
        (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)
    ],
    'faces': [
        (0, 1, 5, 4), (0, 4, 7, 3), (0, 3, 2, 1),
        (1, 2, 6, 5), (2, 3, 7, 6), (4, 5, 6, 7)
    ],
    'uv': [
        ((1, 1), (0.9, 1), (0.9, 0), (1, 0)),
        ((0, 1), (0, 0), (0.4, 0), (0.4, 1)),
        # [(0, 1), (0.4, 1), Vec2(0.5, 1), Vec2(0.9, 1)],
        ((0, 0), (1, 0), (1, 1), (0, 1)),
        ((0.9, 1), (0.5, 1), (0.5, 0), (0.9, 0)),
        ((0.5, 1), (0.4, 1), (0.4, 0), (0.5, 0)),
        # ((0, 0), (1, 0), (1, 1), (0, 1))
        ((1, 0), (0.9, 0), (0.5, 0), (0.4, 0))
    ]
}

DECAGONAL_PRISM = {
    'vertices': [
        (-0.29524181, -0.90866085, 0.29524181),
        (-0.77295309, -0.56158329, 0.29524181),
        (-0.95542256, 0.0, 0.29524181),
        (-0.77295309, 0.56158329, 0.29524181),
        (-0.29524181, 0.90866085, 0.29524181),
        (0.29524181, 0.90866085, 0.29524181),
        (0.77295309, 0.56158329, 0.29524181),
        (0.95542256, -0.0, 0.29524181),
        (0.77295309, -0.56158329, 0.29524181),
        (0.29524181, -0.90866085, 0.29524181),
        (-0.29524181, -0.90866085, -0.2952418),
        (-0.77295309, -0.56158329, -0.2952418),
        (-0.95542256, 0.0, -0.29524181),
        (-0.77295309, 0.56158329, -0.29524181),
        (-0.29524181, 0.90866085, -0.29524181),
        (0.29524181, 0.90866085, -0.29524181),
        (0.77295309, 0.56158329, -0.29524181),
        (0.95542256, -0.0, -0.29524181),
        (0.77295309, -0.56158329, -0.29524181),
        (0.29524181, -0.90866085, -0.29524181),
    ],
    'faces': [
        (0, 1, 11, 10),
        (0, 10, 19, 9),
        (0, 9, 8, 7, 6, 5, 4, 3, 2, 1),
        (1, 2, 12, 11),
        (2, 3, 13, 12),
        (3, 4, 14, 13),
        (4, 5, 15, 14),
        (5, 6, 16, 15),
        (6, 7, 17, 16),
        (7, 8, 18, 17),
        (8, 9, 19, 18),
        (10, 11, 12, 13, 14, 15, 16, 17, 18, 19),
    ],
    'uv': [
        ((0.9, 1), (0.8, 1), (0.8, 0), (0.9, 0)),
        ((0.9, 1), (0.9, 0), (1, 0), (1, 1)),
        ((0.9, 1), (1, 1), (0.1, 1), (0.2, 1), (0.3, 1), (0.4, 1), (0.5, 1), (0.6, 1), (0.7, 1), (0.8, 1)),
        ((0.8, 1), (0.7, 1), (0.7, 0), (0.8, 0)),
        ((0.7, 1), (0.6, 1), (0.6, 0), (0.7, 0)),
        ((0.6, 1), (0.5, 1), (0.5, 0), (0.6, 0)),
        ((0.5, 1), (0.4, 1), (0.4, 0), (0.5, 0)),
        ((0.4, 1), (0.3, 1), (0.3, 0), (0.4, 0)),
        ((0.3, 1), (0.2, 1), (0.2, 0), (0.3, 0)),
        ((0.2, 1), (0.1, 1), (0.1, 0), (0.2, 0)),
        ((0.1, 1), (0, 1), (0, 0), (0.1, 0)),
        ((0.9, 0), (1, 0), (0.1, 0), (0.2, 0), (0.3, 0), (0.4, 0), (0.5, 0), (0.6, 0), (0.7, 0), (0.8, 0)),
    ]
}

TRIANGULAR_PRISM = {
    'vertices': [
        (-0.65465367, -0.37796447, 0.65465367),
        (0.0, 0.75592895, 0.65465367),
        (0.65465367, -0.37796447, 0.65465367),
        (-0.65465367, -0.37796447, -0.65465367),
        (0.0, 0.75592895, -0.65465367),
        (0.65465367, -0.37796447, -0.65465367)
    ],
    'faces': [
        (0, 1, 4, 3),
        (0, 3, 5, 2),
        (0, 2, 1),
        (1, 2, 5, 4),
        (3, 4, 5)
    ]
}
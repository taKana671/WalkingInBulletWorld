import array

from panda3d.core import Vec3, Vec2, LColor, Point3, CardMaker, Point2, Texture, TextureStage
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat
from panda3d.core import GeomNode

from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint

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


class Materials(NodePath):

    def __init__(self, name, parent, np, pos, hpr, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)

        self.model = np
        self.model = np.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)


class Block(Materials):

    def __init__(self, name, parent, np, pos, hpr, scale, bitmask=1):
        super().__init__(name, parent, np, pos, hpr, scale)
        end, tip = self.model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(bitmask))


class Cylinder(Materials):

    def __init__(self, name, parent, np, pos, hpr, scale, bitmask=1):
        super().__init__(name, parent, np, pos, hpr, scale)
        shape = BulletConvexHullShape()
        shape.addGeom(self.model.node().getGeom(0))
        self.node().addShape(shape)
        self.setCollideMask(BitMask32.bit(bitmask))


class CubeModel(NodePath):

    def __new__(cls, *args, **kargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(CubeModel, cls).__new__(cls)
        return cls._instance

    def __init__(self, nd):
        super().__init__(nd)
        self.setTwoSided(True)


class Build:

    def __init__(self, world):
        self.world = world
        self.cube = self.make_cube()
        self.cylinder = self.make_cylinder()

    def make_cylinder(self):
        vertices = DECAGONAL_PRISM['vertices']
        idx_faces = DECAGONAL_PRISM['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]
        uv_list = [uv for uv in calc_uv(vertices)]
        uv = [[uv_list[i] for i in face] for face in idx_faces]

        geomnode = make_geomnode(faces, uv)
        cylinder = NodePath(geomnode)
        cylinder.setTwoSided(True)

        return cylinder

    def make_cube(self):
        vertices = CUBE['vertices']
        idx_faces = CUBE['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]

        uv = [
            [Vec2(1, 1), Vec2(0.9, 1), Vec2(0.9, 0), Vec2(1, 0)],
            [Vec2(0, 1), Vec2(0, 0), Vec2(0.4, 0), Vec2(0.4, 1)],
            # [Vec2(0, 1), Vec2(0.4, 1), Vec2(0.5, 1), Vec2(0.9, 1)],
            [Vec2(0, 0), Vec2(1, 0), Vec2(1, 1), Vec2(0, 1)],
            [Vec2(0.9, 1), Vec2(0.5, 1), Vec2(0.5, 0), Vec2(0.9, 0)],
            [Vec2(0.5, 1), Vec2(0.4, 1), Vec2(0.4, 0), Vec2(0.5, 0)],
            [Vec2(1, 0), Vec2(0.9, 0), Vec2(0.5, 0), Vec2(0.4, 0)]
        ]

        normal_vecs = [
            [Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0)],
            [Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0)],
            [Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1)],
            [Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0)],
            [Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0)],
            [Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1)]
        ]

        geomnode = make_geomnode(faces, uv)
        # cube = CubeModel(geomnode) copyto -> NodePathを継承して作った自作クラスのメソッドはコピーされない
        cube = NodePath(geomnode)
        cube.setTwoSided(True)
        return cube

    def set_tex_scale(self, np, x, z):
        su = x / 2
        sv = z / 3 if z > 1 else z
        np.setTexScale(TextureStage.getDefault(), su, sv)

    def get_hpr(self, horizontal, vertical, rotate):
        if horizontal:
            return Vec3(0, 0, 0)
        if vertical:
            return Vec3(90, 0, 0)
        if rotate:
            return rotate

        return None

    def floor(self, name, parent, pos, scale, bitmask=1):
        hpr = Vec3(0, 90, 0)
        floor = Block(name, parent, self.cube, pos, hpr, scale, bitmask)
        self.set_tex_scale(floor, scale.x, scale.z)
        self.world.attachRigidBody(floor.node())
        return floor

    def block(self, name, parent, pos, scale, horizontal=False, vertical=False, rotate=None, bitmask=1):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        block = Block(name, parent, self.cube, pos, hpr, scale, bitmask)
        self.set_tex_scale(block, scale.x, scale.z)
        self.world.attachRigidBody(block.node())
        return block

    def door_knob(self, parent, left_hinge):
        knob_x = 0.4 if left_hinge else -0.4
        pos = Point3(knob_x, 0, 0)
        hpr = Vec3(90, 0, 0)
        scale = Vec3(1.5, 0.05, 0.05)

        knob = Block('knob', parent, self.cube, pos, hpr, scale)
        knob.setColor(0, 0, 0, 1)

    def door(self, name, parent, pos, scale, wall, horizontal=False, vertical=False, rotate=None, left_hinge=True):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        door = Block(name, parent, self.cube, pos, hpr, scale)
        self.set_tex_scale(door, scale.x, scale.z)

        door.node().setMass(1)
        door.node().setDeactivationEnabled(False)
        self.door_knob(door, left_hinge)
        self.world.attachRigidBody(door.node())

        end, tip = door.getTightBounds()
        door_size = tip - end
        end, tip = wall.getTightBounds()
        wall_size = tip - end

        door_x = -(door_size.x / 2) if left_hinge else door_size.x / 2
        wall_x = wall_size.x / 2 if left_hinge else -wall_size.x / 2

        twist = BulletConeTwistConstraint(
            wall.node(),
            door.node(),
            TransformState.makePos(Point3(wall_x, wall_size.y / 2, 0)),
            TransformState.makePos(Point3(door_x, door_size.y / 2, 0)),
        )

        twist.setLimit(60, 60, 0, softness=0.1, bias=0.1, relaxation=8.0)
        self.world.attachConstraint(twist)


        # hinge = BulletHingeConstraint(
        #     wall.node(),
        #     door.node(),
        #     Vec3(wall_x, wall_size.y / 2, 0),
        #     Vec3(door_x, door_size.y / 2, 0),
        #     Vec3(0, 1, 0),
        #     Vec3(0, 1, 0),
        #     True,
        # )
        # hinge.setDebugDrawSize(2.0)
        # hinge.setLimit(-90, 120,) # softness=0.1, bias=0.1, relaxation=8.0)  # 1.0
        # self.world.attachConstraint(hinge)

    def pole(self, name, parent, pos, scale, tex_scale=False):
        hpr = Vec3(0, 0, 0)
        pole = Cylinder(name, parent, self.cylinder, pos, hpr, scale, bitmask=2)
        if tex_scale:
            self.set_tex_scale(pole, scale.x, scale.z)

        self.world.attachRigidBody(pole.node())

    def room_camera(self, name, parent, pos):
        room_camera = NodePath(name)
        room_camera.reparentTo(parent)
        room_camera.setPos(pos)
        return room_camera


class StoneHouse(Build):

    def __init__(self, world):
        super().__init__(world)
        self.house = NodePath(PandaNode('stoneHouse'))
        self.house.reparentTo(base.render)
        self.center = Point3(15, 10, -0.5)
        self.house.setPos(self.center)
        # self.house.setH(-45) <= 2階の部屋から出た時おかしくなる（カメラが階段のしたに入ってしまう？）
        self.build()

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
        self.door_tex = base.loader.loadTexture('textures/7-8-19a-300x300.jpg')
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
            [Point3(-11, 0, -3.5), Vec3(10, 1, 24)],          # left
            [Point3(11, 0, -3.5), Vec3(10, 1, 24)],           # right
            [Point3(0, -10, -3.5), Vec3(12, 1, 4)],           # front
            [Point3(0, 10, -3.5), Vec3(12, 1, 4)]             # back
        ]
        for i, (pos, scale) in enumerate(materials):
            self.floor(f'floor1_{i}', floors, pos, scale)

        # room and room camera on the 1st floor
        self.floor('room1', floors, Point3(0, 0, -3.5), Vec3(12, 1, 16))
        self.room_camera('room1_camera', self.house, Point3(0, 0, 2.75))

        # right and left walls on the 1st floor
        materials = [
            [Point3(-5.75, 0, 0), Vec3(16, 0.5, 6)],          # left
            [Point3(5.75, 0, -2), Vec3(16, 0.5, 2)],          # right under
            [Point3(5.75, 3, 0), Vec3(10, 0.5, 2)],           # right middle back
            [Point3(5.75, -7, 0), Vec3(2, 0.5, 2)],           # right front
            [Point3(5.75, 0, 2), Vec3(16, 0.5, 2)],           # right top
            [Point3(-13.75, -4.25, 3.5), Vec3(8.5, 0.5, 13)]  # left side of the steps
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_side{i}', walls, pos, scale, vertical=True)

        # front and rear walls on the 1st floor
        materials = [
            [Point3(0, 8.25, 0), Vec3(12, 0.5, 6)],           # rear
            [Point3(0, -8.25, 2.0), Vec3(12, 0.5, 2)],        # front top
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_fr{i}', walls, pos, scale, horizontal=True)

        wall1_l = self.block('wall1_fl', walls, Point3(-4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)    # front left
        wall1_r = self.block('wall1_fr', walls, Point3(4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)     # front right

        # 2nd floor
        materials = [
            [Point3(4, -4.25, 3.25), Vec3(20, 0.5, 8.5), 1],
            [Point3(-9.75, -1, 3.25), Vec3(7.5, 0.5, 2), 2]
        ]
        for i, (pos, scale, mask) in enumerate(materials):
            self.floor(f'floor2_{i}', floors, pos, scale, bitmask=mask)

        # room and room camera on the 2nd floor
        self.floor('room2', floors, Point3(-4, 4.25, 3.25), Vec3(20, 0.5, 8.5))
        self.room_camera('room2_camera', self.house, Point3(-10, 4, 9.5))

        # balcony fence
        materials = [
            [Point3(4, -8.25, 4), Vec3(0.5, 1, 20), Vec3(0, 90, 90)],
            [Point3(-5.75, -5, 4), Vec3(0.5, 1, 6), Vec3(0, 90, 0)],
            [Point3(13.75, -4, 4), Vec3(0.5, 1, 8), Vec3(0, 90, 0)],
            [Point3(10, 0.25, 3.75), Vec3(0.5, 1.5, 8), Vec3(0, 90, 90)]
        ]
        for i, (pos, scale, rotate) in enumerate(materials):
            self.block(f'balcony_{i}', floors, pos, scale, rotate=rotate)

        # left and right walls on the 2nd floor
        materials = [
            [Point3(-13.75, 4, 4.5), Vec3(8, 0.5, 2)],        # left
            [Point3(-13.75, 1.5, 6.5), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 6.5, 6.5), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 4, 8.5), Vec3(8, 0.5, 2)],        # left
            [Point3(5.75, 4.25, 6.5), Vec3(7.5, 0.5, 6)]      # right
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall2_side{i}', walls, pos, scale, vertical=True)

        # front and rear walls on the 2nd floor
        materials = [
            [Point3(-4, 8.25, 6.5), Vec3(20, 0.5, 6)],        # rear
            [Point3(-7.25, 0.25, 5.5), Vec3(2.5, 0.5, 4)],    # front
            [Point3(-9.75, 0.25, 8.5), Vec3(7.5, 0.5, 2)],    # front
            [Point3(0, 0.25, 4.5), Vec3(12, 0.5, 2)],         # front
            [Point3(-4, 0.25, 6.5), Vec3(4, 0.5, 2)],         # front
            [Point3(4, 0.25, 6.5), Vec3(4, 0.5, 2)],          # front
            [Point3(0, 0.25, 8.5), Vec3(12, 0.5, 2)]          # front
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall2_fr{i}', walls, pos, scale, horizontal=True)

        wall2_l = self.block('wall2_l', walls, Point3(-12.5, 0.25, 5.5), Vec3(2, 0.5, 4), horizontal=True)

        # roof
        self.floor('roof', floors, Point3(-4, 4.25, 9.75), Vec3(20, 0.5, 8.5))

        # steps
        steps = [Point3(-9.75, -7.5 + i, -2.5 + i) for i in range(6)]
        for i, pos in enumerate(steps):
            self.block(f'step_{i}', floors, pos, Vec3(7.5, 1, 1), rotate=Vec3(0, 90, 0), bitmask=2)

        # doors
        materials = [
            [Point3(-1, -8.25, -1), Vec3(2, 0.5, 4), wall1_l, True],    # left door of the room on the 1st floor
            [Point3(1, -8.25, -1), Vec3(2, 0.5, 4), wall1_r, False],    # left door of the room on the 1st floor
            [Point3(-10, 0.25, 5.5), Vec3(3, 0.5, 4), wall2_l, True]    # foor ofr the room on the 2nd floor
        ]
        for i, (pos, scale, body, hinge) in enumerate(materials):
            self.door(f'door_{i}', doors, pos, scale, body, horizontal=True, left_hinge=hinge)

        doors.setTexture(self.door_tex)
        walls.setTexture(self.wall_tex)
        floors.setTexture(self.floor_tex)


class BrickHouse(Build):

    def __init__(self, world):
        super().__init__(world)
        self.house = NodePath(PandaNode('brickHouse'))
        self.house.reparentTo(base.render)
        self.center = Point3(-15, 30, 0)
        self.house.setPos(self.center)
        self.build()

    def make_textures(self):
        # for walls
        self.wall_tex = base.loader.loadTexture('textures/brick.jpg')
        self.wall_tex.setWrapU(Texture.WM_repeat)
        self.wall_tex.setWrapV(Texture.WM_repeat)

        # for foundation
        self.foundation_tex = base.loader.loadTexture('textures/concrete2.jpg')
        self.foundation_tex.setWrapU(Texture.WM_repeat)
        self.foundation_tex.setWrapV(Texture.WM_repeat)

        # for roofs
        self.roof_tex = base.loader.loadTexture('textures/iron.jpg')
        self.roof_tex.setWrapU(Texture.WM_repeat)
        self.roof_tex.setWrapV(Texture.WM_repeat)

        # for doors
        self.door_tex = base.loader.loadTexture('textures/7-8-19a-300x300.jpg')
        self.door_tex.setWrapU(Texture.WM_repeat)
        self.door_tex.setWrapV(Texture.WM_repeat)

    def build(self):
        self.make_textures()
        foundations = NodePath('foundation')
        foundations.reparentTo(self.house)
        walls = NodePath('wall')
        walls.reparentTo(self.house)
        roofs = NodePath('roof')
        roofs.reparentTo(self.house)   

        # foundation
        materials = [
            [Point3(0, 0, -2.5), Vec3(13, 9, 2)],     # big room
            [Point3(3, -6.5, -2.5), Vec3(7, 4, 2)],   # small room
        ]
        # 天井ができたら、room_cameraをセットすること。
        for i, (pos, scale) in enumerate(materials):
            self.block(f'foundation_{i}', foundations, pos, scale, horizontal=True)

        # steps
        steps = [
            [Point3(3, -9.5, -2.5), Vec3(4, 2, 2)],
            [Point3(3, -11.5, -3), Vec3(4, 2, 1)],
        ]
        for i, (pos, scale) in enumerate(steps):
            self.block(f'step_{i}', foundations, pos, scale, horizontal=True, bitmask=2)

        # rear and front walls
        materials = [
            [Point3(0, 4.25, 2.5), Vec3(12, 0.5, 8)],        # rear
            [Point3(1, -8.25, 0.25), Vec3(2, 0.5, 3.5)],     # front left ****maybe hinge
            [Point3(5, -8.25, 0.25), Vec3(2, 0.5, 3.5)],     # front right
            [Point3(3, -8.25, 2.25), Vec3(6, 0.5, 0.5)],     # front_top
            [Point3(-1.5, -4.25, 2.5), Vec3(2, 0.5, 8)],     # back room front right
            [Point3(-5.25, -4.25, 2.5), Vec3(1.5, 0.5, 8)],  # back room front left
            [Point3(-3.5, -4.25, 0), Vec3(2, 0.5, 3)],       # back room front under
            [Point3(-3.5, -4.25, 5), Vec3(2, 0.5, 3)],       # back room front under
            [Point3(3, -4.25, 4.5), Vec3(7, 0.5, 4)],        # back room front
        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_fr{i}', walls, pos, scale, horizontal=True)

        # side walls
        materials = [
            [Point3(-0.25, -6.25, 0.5), Vec3(4.5, 0.5, 4)],   # left
            [Point3(-6.25, -3, 2.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 3, 2.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 0, 0), Vec3(3, 0.5, 3)],
            [Point3(-6.25, 0, 5), Vec3(3, 0.5, 3)],
            [Point3(6.25, -6.25, 0.5), Vec3(4.5, 0.5, 4)],    # right
            [Point3(6.25, -2.75, 2.5), Vec3(2.5, 0.5, 8)],
            [Point3(6.25, 3, 2.5), Vec3(3, 0.5, 8)],
            [Point3(6.25, 0, 0), Vec3(3, 0.5, 3)],
            [Point3(6.25, 0, 5), Vec3(3, 0.5, 3)],

        ]
        for i, (pos, scale) in enumerate(materials):
            self.block(f'wall1_side{i}', walls, pos, scale, vertical=True)

        # roofs
        materials = [
            [Point3(3, -6.5, 2.75), Vec3(7, 0.5, 4)],   # small room
            [Point3(3, -6.5, 3), Vec3(6, 0.5, 3)],      # small room
            [Point3(0, 0, 6.75), Vec3(13, 0.5, 9)],     # big room
            [Point3(0, 0, 7), Vec3(12, 0.5, 8)],        # big room
        ]
        for i, (pos, scale) in enumerate(materials):
            self.floor(f'roof_{i}', roofs, pos, scale)

        foundations.setTexture(self.foundation_tex)
        walls.setTexture(self.wall_tex)
        roofs.setTexture(self.roof_tex)


CUBE = {
    'vertices': [
        (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
        (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)
    ],
    'faces': [
        (0, 1, 5, 4), (0, 4, 7, 3), (0, 3, 2, 1),
        (1, 2, 6, 5), (2, 3, 7, 6), (4, 5, 6, 7)
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
    ]
}
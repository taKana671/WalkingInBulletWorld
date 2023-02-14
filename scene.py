from collections import namedtuple
from functools import partial

from panda3d.core import Vec3, Vec2, LColor, Point3, CardMaker, Point2, Texture, TextureStage
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import GeomNode

from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint

import numpy as np


def prim_vertices(faces):
    start = 0
    for face in faces:
        match num := len(face):
            case 3:
                yield (start, start + 1, start + 2)
            case 4:
                for x, y, z in [(0, 1, 3), (1, 2, 3)]:
                    yield (start + x, start + y, start + z)
            case _:
                for i in range(2, num):
                    if i == 2:
                        yield (start, start + i - 1, start + i)
                    else:
                        yield (start + i - 1, start, start + i)
        start += num





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


def make_geomnode(faces, uv_list):
    format_ = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('triangle', format_, Geom.UHStatic)
    vdata.setNumRows(len(faces))

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    # color = GeomVertexWriter(vdata, 'color')
    texcoord = GeomVertexWriter(vdata, 'texcoord')


    for face_pts, uv_pts in zip(faces, uv_list):
        for pt, uv in zip(face_pts, uv_pts):
            vertex.addData3(pt)
            normal.addData3(pt.normalized())
            # color.addData4f(LColor(1, 1, 1, 1))
            texcoord.addData2(uv)
    
    # for pts in faces:
    #     for pt, uv in zip(pts, [(0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]):
    #         vertex.addData3(pt)
    #         normal.addData3(pt.normalized())
    #         texcoord.addData2(*uv)

    node = GeomNode('geomnode')
    prim = GeomTriangles(Geom.UHStatic)

    for vertices in prim_vertices(faces):
        prim.addVertices(*vertices)

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
        # self.setCollideMask(BitMask32.bit(1))


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


Material = namedtuple('Material', 'pos hpr scale')


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
        # print(faces)
        # uv_list = [uv for uv in calc_uv(vertices)]
        # uv = [[uv_list[i] for i in face] for face in idx_faces]
        # print(uv)

        # uv = [Vec2(0, 2.0), Vec2(0, 0), Vec2(2.0, 0), Vec2(2.0, 2.0)]
        # uv = [Vec2(0, 1.0), Vec2(0, 0), Vec2(1.0, 0), Vec2(1.0, 1.0)]
        # uv = [uv for _ in range(6)]

        # uv = [
        #     [Vec2(1, 1), Vec2(0.75, 1), Vec2(0.75, 0), Vec2(1, 0)],
        #     [Vec2(0, 1), Vec2(0, 0), Vec2(0.25, 0), Vec2(0.25, 1)],
        #     [Vec2(0, 1), Vec2(0.25, 1), Vec2(0.5, 1), Vec2(0.75, 1)],
        #     [Vec2(0.75, 1), Vec2(0.5, 1), Vec2(0.5, 0), Vec2(0.75, 0)],
        #     [Vec2(0.5, 1), Vec2(0.25, 1), Vec2(0.25, 0), Vec2(0.5, 0)],
        #     [Vec2(1, 0), Vec2(0.75, 0), Vec2(0.5, 0), Vec2(0.25, 0)]
        # ]

        uv = [
            [Vec2(1, 1), Vec2(0.9, 1), Vec2(0.9, 0), Vec2(1, 0)],
            [Vec2(0, 1), Vec2(0, 0), Vec2(0.4, 0), Vec2(0.4, 1)],
            [Vec2(0, 1), Vec2(0.4, 1), Vec2(0.5, 1), Vec2(0.9, 1)],
            [Vec2(0.9, 1), Vec2(0.5, 1), Vec2(0.5, 0), Vec2(0.9, 0)],
            [Vec2(0.5, 1), Vec2(0.4, 1), Vec2(0.4, 0), Vec2(0.5, 0)],
            [Vec2(1, 0), Vec2(0.9, 0), Vec2(0.5, 0), Vec2(0.4, 0)]
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

    def wall(self, name, parent, pos, scale, horizontal=False, vertical=False, rotate=None, bitmask=1):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        wall = Block(name, parent, self.cube, pos, hpr, scale, bitmask)
        self.set_tex_scale(wall, scale.x, scale.z)
        self.world.attachRigidBody(wall.node())
        return wall

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

    def steps(self, steps, parent, scale, horizontal=False, vertical=False, rotate=None):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        for name, pos in steps:
            step = Block(name, parent, self.cube, pos, hpr, scale, bitmask=2)
            self.world.attachRigidBody(step.node())

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
            self.wall(f'wall1_side{i}', walls, pos, scale, vertical=True)

        # front and rear walls on the 1st floor
        materials = [
            [Point3(0, 8.25, 0), Vec3(12, 0.5, 6)],           # rear
            [Point3(0, -8.25, 2.0), Vec3(12, 0.5, 2)],        # front top
        ]
        for i, (pos, scale) in enumerate(materials):
            self.wall(f'wall1_fr{i}', walls, pos, scale, horizontal=True)

        wall1_l = self.wall('wall1_fl', walls, Point3(-4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)    # front left
        wall1_r = self.wall('wall1_fr', walls, Point3(4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)     # front right

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
            self.wall(f'balcony_{i}', floors, pos, scale, rotate=rotate)

        # left and right walls on the 2nd floor
        materials = [
            [Point3(-13.75, 4, 4.5), Vec3(8, 0.5, 2)],        # left
            [Point3(-13.75, 1.5, 6.5), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 6.5, 6.5), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 4, 8.5), Vec3(8, 0.5, 2)],        # left
            [Point3(5.75, 4.25, 6.5), Vec3(7.5, 0.5, 6)]      # right
        ]
        for i, (pos, scale) in enumerate(materials):
            self.wall(f'wall2_side{i}', walls, pos, scale, vertical=True)

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
            self.wall(f'wall2_fr{i}', walls, pos, scale, horizontal=True)

        wall2_l = self.wall('wall2_l', walls, Point3(-12.5, 0.25, 5.5), Vec3(2, 0.5, 4), horizontal=True)

        # roof
        self.floor('roof', floors, Point3(-4, 4.25, 9.75), Vec3(20, 0.5, 8.5))
        # steps
        steps = [(f'step_{i}', Point3(-9.75, -7.5 + i, -2.5 + i)) for i in range(6)]
        self.steps(steps, floors, Vec3(7.5, 1, 1), rotate=Vec3(0, 90, 0))

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
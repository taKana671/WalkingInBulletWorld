from collections import namedtuple
from functools import partial

from panda3d.core import Vec3, Vec2, LColor, Point3, CardMaker, Point2, Texture, TextureStage
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import GeomNode

from panda3d.core import BitMask32
from panda3d.core import NodePath, PandaNode
# from direct.showbase.ShowBase import ShowBase
# from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHingeConstraint

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


# class Block(NodePath):

#     def __init__(self, cube, name):
#         super().__init__(BulletRigidBodyNode(name))
#         model = cube.copyTo(self)
#         end, tip = model.getTightBounds()
#         self.node().addShape(BulletBoxShape((tip - end) / 2))
#         self.setCollideMask(BitMask32.bit(1))


# class Cylinder(NodePath):

#     def __init__(self, cylinder, name):
#         super().__init__(BulletRigidBodyNode(name))
#         model = cylinder.copyTo(self)
#         end, tip = model.getTightBounds()
#         self.node().addShape(BulletBoxShape((tip - end) / 2))
#         self.setCollideMask(BitMask32.bit(1))


class Materials(NodePath):

    def __init__(self, name, parent, np, pos, hpr, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(parent)
        self.model = np.copyTo(self)
        self.setPos(pos)
        self.setHpr(hpr)
        self.setScale(scale)


class Block(Materials):

    def __init__(self, name, parent, np, pos, hpr, scale):
        super().__init__(name, parent, np, pos, hpr, scale)
        end, tip = self.model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(1))


class Cylinder(Materials):

    def __init__(self, name, parent, np, pos, hpr, scale):
        super().__init__(name, parent, np, pos, hpr, scale)
        shape = BulletConvexHullShape()
        shape.addGeom(self.model.node().getGeom(0))
        self.node().addShape(shape)
        self.setCollideMask(BitMask32.bit(1))


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

    def floor(self, name, parent, pos, scale):
        hpr = Vec3(0, 90, 0)
        floor = Block(name, parent, self.cube, pos, hpr, scale)
        self.set_tex_scale(floor, scale.x, scale.z)
        self.world.attachRigidBody(floor.node())
        return floor

    def wall(self, name, parent, pos, scale, horizontal=False, vertical=False, rotate=None):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        wall = Block(name, parent, self.cube, pos, hpr, scale)
        self.set_tex_scale(wall, scale.x, scale.z)
        self.world.attachRigidBody(wall.node())
        return wall

    def door(self, name, parent, pos, scale, wall, horizontal=False, vertical=False, rotate=None, left_hinge=True):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        door = Block(name, parent, self.cube, pos, hpr, scale)
        self.set_tex_scale(door, scale.x, scale.z)

        door.node().setMass(1)
        door.node().setDeactivationEnabled(False)
        self.world.attachRigidBody(door.node())

        end, tip = door.getTightBounds()
        door_size = tip - end
        end, tip = wall.getTightBounds()
        wall_size = tip - end

        door_x = -(door_size.x / 2) if left_hinge else door_size.x / 2
        wall_x = wall_size.x / 2 if left_hinge else -wall_size.x / 2

        hinge = BulletHingeConstraint(
            wall.node(),
            door.node(),
            Vec3(wall_x, wall_size.y / 2, 0),
            Vec3(door_x, door_size.y / 2, 0),
            Vec3(0, 1, 0),
            Vec3(0, 1, 0),
            True,
        )
        hinge.setDebugDrawSize(2.0)
        hinge.setLimit(-90, 120, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(hinge)

    def steps(self, steps, parent, scale, horizontal=False, vertical=False, rotate=None):
        hpr = self.get_hpr(horizontal, vertical, rotate)
        for name, pos in steps:
            step = Block(name, parent, self.cube, pos, hpr, scale)
            self.world.attachRigidBody(step.node())

    def pole(self, name, parent, pos, scale, tex_scale=False):
        hpr = Vec3(0, 0, 0)
        pole = Cylinder(name, parent, self.cylinder, pos, hpr, scale)
        if tex_scale:
            self.set_tex_scale(pole, scale.x, scale.z)

        self.world.attachRigidBody(pole.node())


class StoneHouse(Build):

    def __init__(self, world):
        super().__init__(world)
        self.house = NodePath(PandaNode('stoneHouse'))
        self.house.reparentTo(base.render)
        self.center = Point3(-5, 10, 0)  # -5
        self.house.setPos(self.center)
        self.build()


    def make_textures(self):
        self.wall_tex = base.loader.loadTexture('textures/fieldstone.jpg')
        self.wall_tex.setWrapU(Texture.WM_repeat)
        self.wall_tex.setWrapV(Texture.WM_repeat)

        self.floor_tex = base.loader.loadTexture('textures/iron.jpg')
        self.floor_tex.setWrapU(Texture.WM_repeat)
        self.floor_tex.setWrapV(Texture.WM_repeat)

        self.fence_tex = base.loader.loadTexture('textures/concrete2.jpg')

        self.door_tex = base.loader.loadTexture('textures/7-8-19a-300x300.jpg')
        self.door_tex.setWrapU(Texture.WM_repeat)
        self.door_tex.setWrapV(Texture.WM_repeat)

    def build(self):
        self.make_textures()

        walls = NodePath(PandaNode('walls'))
        walls.reparentTo(self.house)
        floors = NodePath(PandaNode('floors'))
        floors.reparentTo(self.house)
        fences = NodePath(PandaNode('fences'))
        fences.reparentTo(self.house)
        doors = NodePath(PandaNode('doors'))
        doors.reparentTo(self.house)

        # the 1st floor
        self.floor('floor1', floors, Point3(0, 0, -3.5), Vec3(32, 1, 24))
        # rear wall on the lst floor
        self.wall('wall1_r1', walls, Point3(0, 8.25, 0), Vec3(12, 0.5, 6), horizontal=True)
        # left wall on the 1st floor
        self.wall('wall1_l1', walls, Point3(-5.75, 0, 0), Vec3(16, 0.5, 6), vertical=True)
        # right wall on the 1st floor
        self.wall('wall1_r1', walls, Point3(5.75, 0, -2), Vec3(16, 0.5, 2), vertical=True)   # under
        self.wall('wall1_r2', walls, Point3(5.75, 3, 0), Vec3(10, 0.5, 2), vertical=True)    # middle back
        self.wall('wall1_r3', walls, Point3(5.75, -7, 0), Vec3(2, 0.5, 2), vertical=True)    # middle front
        self.wall('wall1_r4', walls, Point3(5.75, 0, 2), Vec3(16, 0.5, 2), vertical=True)    # top
        # front wall on the 1st floor
        wall1_l = self.wall('wall1_f1', walls, Point3(-4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)    # front left
        wall1_r = self.wall('wall1_f2', walls, Point3(4, -8.25, -1), Vec3(4, 0.5, 4), horizontal=True)         # front right
        _ = self.wall('wall1_f3', walls, Point3(0, -8.25, 2.0), Vec3(12, 0.5, 2), horizontal=True)       # front top
        # 2nd floor
        self.floor('floor2_1', floors, Point3(-4, 4.25, 3.25), Vec3(20, 0.5, 8.5))  # back
        self.floor('floor2_2', floors, Point3(4, -4.25, 3.25), Vec3(20, 0.5, 8.5))  # flont
        self.floor('floor2_3', floors, Point3(-10, -1, 3.25), Vec3(8, 0.5, 2))      # front doors
        # balcony fence
        self.wall('balcony_1', floors, Point3(4, -8.25, 4), Vec3(0.5, 1, 20), rotate=Vec3(0, 90, 90))      # fence
        self.wall('balcony_2', floors, Point3(-5.75, -5, 4), Vec3(0.5, 1, 6), rotate=Vec3(0, 90, 0)),       # fence
        self.wall('balcony_3', floors, Point3(13.75, -4, 4), Vec3(0.5, 1, 8), rotate=Vec3(0, 90, 0))       # fence
        self.wall('balcony_4', floors, Point3(10, 0.25, 3.75), Vec3(0.5, 1.5, 8), rotate=Vec3(0, 90, 90))  # fence
        # rear wall on the 2nd floor
        self.wall('wall2_r1', walls, Point3(-4, 8.25, 6.5), Vec3(20, 0.5, 6), horizontal=True)
        # left wall on the 2nd floor
        self.wall('wall2_l1', walls, Point3(-13.75, 4, 4.5), Vec3(8, 0.5, 2), vertical=True)
        self.wall('wall2_l2', walls, Point3(-13.75, 1.5, 6.5), Vec3(3, 0.5, 2), vertical=True)
        self.wall('wall2_l3', walls, Point3(-13.75, 6.5, 6.5), Vec3(3, 0.5, 2), vertical=True)
        self.wall('wall2_l4', walls, Point3(-13.75, 4, 8.5), Vec3(8, 0.5, 2), vertical=True)
        # right wall on the 2nd floor
        self.wall('wall2_r1', walls, Point3(5.75, 4.25, 6.5), Vec3(7.5, 0.5, 6), vertical=True)
        # front wall on the 2nd floor
        wall2_l = self.wall('wall2_f1', walls, Point3(-12.5, 0.25, 5.5), Vec3(2, 0.5, 4), horizontal=True)
        self.wall('wall2_f2', walls, Point3(-7.25, 0.25, 5.5), Vec3(2.5, 0.5, 4), horizontal=True)
        self.wall('wall2_f3', walls, Point3(-9.75, 0.25, 8.5), Vec3(7.5, 0.5, 2), horizontal=True)
        self.wall('wall2_f4', walls, Point3(0, 0.25, 4.5), Vec3(12, 0.5, 2), horizontal=True)
        self.wall('wall2_f5', walls, Point3(-4, 0.25, 6.5), Vec3(4, 0.5, 2), horizontal=True)    # front left
        self.wall('wall2_f6', walls, Point3(4, 0.25, 6.5), Vec3(4, 0.5, 2), horizontal=True)
        self.wall('wall2_f7', walls, Point3(0, 0.25, 8.5), Vec3(12, 0.5, 2), horizontal=True)
        # roof
        self.floor('roof', floors, Point3(-4, 4.25, 9.75), Vec3(20, 0.5, 8.5))
        # steps
        steps = [(f'step_{i}', Point3(-10, -7.5 + i, -2.5 + i)) for i in range(6)]
        self.steps(steps, floors, Vec3(8, 1, 1), rotate=Vec3(0, 90, 0))
        # fences for steps
        h = 0
        for i in range(8):
            if i <= 6:
                h = i
            pos = Point3(-13.75, -7.5 + i, -1.5 + h)
            self.pole(f'fence_{i}', fences, pos, Vec3(0.1, 0.1, 5))

        # 1st floor doors
        self.door('door1_l', doors, Point3(-1, -8.25, -1), Vec3(2, 0.5, 4), wall1_l, horizontal=True, left_hinge=True)
        self.door('door1_r', doors, Point3(1, -8.25, -1), Vec3(2, 0.5, 4), wall1_r, horizontal=True, left_hinge=False)
        self.door('door2_f', doors, Point3(-10, 0.25, 5.5), Vec3(3, 0.5, 4), wall2_l, horizontal=True, left_hinge=True)

        doors.setTexture(self.door_tex)
        fences.setTexture(self.fence_tex)
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



# >>> from panda3d.core import Vec3
# >>> li = [(-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)]
# >>> li = [Vec3(item) for item in li]
# >>> li
# [LVector3f(-0.5, -0.5, 0.5), LVector3f(-0.5, 0.5, 0.5), LVector3f(0.5, 0.5, 0.5), LVector3f(0.5, -0.5, 0.5), LVector3f(-0.5, -0.5, -0.5), LVector3f(-0.5, 0.5, -0.5), LVector3f(0.5, 0.5, -0.5), LVector3f(0.5, -0.5, -0.5)]
# >>> min(li)
# LVector3f(-0.5, -0.5, -0.5)
# >>> max(li)
# LVector3f(0.5, 0.5, 0.5)
# >>> left_bottom = min(li)
# >>> right_top = max(li)
# >>> height = right_top.z - left_bottom.z
# >>> height
# 1.0
# >>> width = right_top.x - left_bottom.x
# >>> width
# 1.0
# >>> pt = li[0]
# >>> pt
# LVector3f(-0.5, -0.5, 0.5)
# >>> (pt.x - right_bottom.x) / width
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# NameError: name 'right_bottom' is not defined. Did you mean: 'left_bottom'?
# >>> (pt.x - left_bottom.x) / width
# 0.0
# >>> (pt.z - left_bottom.z) / height
# 1.0
# >>> li2 = [((item.x - left_bottom.x) / width, (item.z - left_bottom.z) / height) for item in li]
# >>> li2
# [(0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0), (0.0, 0.0), (0.0, 0.0), (1.0, 0.0), (1.0, 0.0)]
# >>>
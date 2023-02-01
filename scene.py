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


class Block(NodePath):

    def __init__(self, cube, pos, hpr, scale, name):
        super().__init__(BulletRigidBodyNode(name))
        model = cube.copyTo(self)
        end, tip = model.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(1))
        self.setScale(scale)
        self.setPos(pos)
        self.setHpr(hpr)


class Cylinder(NodePath):

    def __init__(self, model, pos, scale):
        super().__init__(BulletRigidBodyNode('cylinder'))
        model.reparentTo(self)
        shape = BulletConvexHullShape()
        shape.addGeom(model.node().getGeom(0))
        self.node().addShape(shape)
        self.setCollideMask(BitMask32.bit(1))
        # self.node().setMass(1)
        self.setScale(scale)
        self.setPos(pos)
        # self.setR(180)
        # self.node().setMass(1)


class SquareBuilding(NodePath):

    def __init__(self, world):
        super().__init__(PandaNode('squareBuilding'))
        self.reparentTo(base.render)
        self.world = world
        self.center = Vec3(-5, 10, 0)
        # self.center = Vec3(-5, 10, -3)
        # self.center = Vec3(-5, 10, 1)
        self.cube = self.make_cube()
        self.make_floor()
        
        self.make_walls()
        # self.make_roof()
        self.set_doors()

    def make_cube(self):
        vertices = CUBE['vertices']
        idx_faces = CUBE['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]
        # uv_list = [uv for uv in calc_uv(vertices)]
        # uv = [[uv_list[i] for i in face] for face in idx_faces]

        uv = [Vec2(0, 2.0), Vec2(0, 0), Vec2(2.0, 0), Vec2(2.0, 2.0)]
        uv = [uv for _ in range(6)]

        geomnode = make_geomnode(faces, uv)
        cube = NodePath(geomnode)
        cube.setTwoSided(True)

        return cube

    def make_floor(self):
        tex = base.loader.loadTexture('textures/iron.jpg')
        tex.setWrapU(Texture.WM_repeat)
        tex.setWrapV(Texture.WM_repeat)

        pos = Point3(0, 0, -3.5)
        self.floor = Block(self.cube, pos + self.center, Vec3(0, 90, 0), Vec3(16, 1, 16), 'floor')
        self.floor.reparentTo(self)
        self.floor.setTexture(tex)
        self.floor.setTexScale(TextureStage.getDefault(), 2, 2)
        self.world.attachRigidBody(self.floor.node())

    
    def make_walls(self):
        st = TextureStage.getDefault()

        walls = [
            [Point3(0, 6.25, 2), Vec3(90, 90, 0), Vec3(0.5, 10, 12), None],    # back
            [Point3(-5.75, 0, 2), Vec3(180, 90, 0), Vec3(0.5, 10, 12), None],  # left
            [Point3(5.75, 0, 2), Vec3(180, 90, 0), Vec3(0.5, 10, 12), None],   # right
            [Point3(-4, -6.25, 1), Vec3(90, 90, 0), Vec3(0.5, 8, 4), (st, 0.5, 1)],    # front left
            [Point3(4, -6.25, 1), Vec3(90, 90, 0), Vec3(0.5, 8, 4), (st, 0.5, 1)],     # front right
            [Point3(0, -6.25, 6.0), Vec3(90, 90, 0), Vec3(0.5, 2, 12), (st, 1, 0.1)],  # front top
            # [Point3(0, -6.25, 6.5), Vec3(90, 90, 0), Vec3(0.5, 1, 10), (st, 1, 0.1)],
        ]

        tex = base.loader.loadTexture('textures/fieldstone.jpg')
        tex.setWrapU(Texture.WM_repeat)
        tex.setWrapV(Texture.WM_repeat)

        for i, (pos, hpr, scale, tex_scale) in enumerate(walls):
            pos += self.center
            block = Block(self.cube, pos, hpr, scale, f'wall_{i}')
            block.reparentTo(self)
            block.setTexture(tex)
            if tex_scale:
                block.setTexScale(*tex_scale)

            self.world.attachRigidBody(block.node())

    def make_roof(self):
        vertices = DECAGONAL_PRISM['vertices']
        idx_faces = DECAGONAL_PRISM['faces']
        vertices = [Vec3(vertex) for vertex in vertices]
        faces = [[vertices[i] for i in face] for face in idx_faces]
        uv_list = [uv for uv in calc_uv(vertices)]
        uv = [[uv_list[i] for i in face] for face in idx_faces]

        geomnode = make_geomnode(faces, uv)
        prism = NodePath(geomnode)
        prism.setTwoSided(True)


        tex = base.loader.loadTexture('textures/barkTexture.jpg')
        pos = Point3(self.center.x - 8, self.center.y, 1.5)
        scale = Vec3(0.8, 0.8, 5)

        self.roof = Cylinder(prism, pos, scale)
        self.roof.reparentTo(self)
        self.roof.setTexture(tex)
        # self.roof.setP(90)
        self.world.attachRigidBody(self.roof.node())



    
    def set_doors(self):
        # door = [Point3(0, -6.25, 1), Vec3(90, 90, 0), Vec3(0.5, 8, 4)]
        #     # [Point3(2, -6.25, 1), Vec3(90, 90, 0), Vec3(0.5, 8, 2)]

        tex = base.loader.loadTexture('textures/iron.jpg')
        # tex.setWrapU(Texture.WM_repeat)
        # tex.setWrapV(Texture.WM_repeat)

        # import pdb; pdb.set_trace()
        
        door = Block(
            self.cube,
            Point3(0, -6.25, 1) + self.center,
            Vec3(90, 90, 0),
            Vec3(0.5, 8, 4),
            'door'
        )
        door.reparentTo(self)
        door.setTexture(tex)
        # door.setTexScale(TextureStage.getDefault(), 0.5, 1)
        door.node().setMass(1)
        door.node().setDeactivationEnabled(False)
        self.world.attachRigidBody(door.node())


        wall = self.getChild(4)
        hinge = BulletHingeConstraint(
            wall.node(),
            door.node(),
            Point3(0.25, 0, 2),
            Point3(0.25, 0, -2),
            Vec3(0, 1, 0),
            Vec3(0, 1, 0),
            True,
        )
        hinge.setDebugDrawSize(2.0)
        hinge.setLimit(-90, 120, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(hinge)



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
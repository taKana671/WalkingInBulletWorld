import array

from panda3d.core import LColor, Vec3
from panda3d.core import NodePath
from panda3d.core import Geom, GeomNode, GeomTriangles
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat


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


# def make_geomnode(faces, texcoords, normal_vecs):
def make_geometry(faces, texcoords):
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


def make_node(polh_dic):
    vertices = polh_dic['vertices']
    idx_faces = polh_dic['faces']
    vertices = [Vec3(vertex) for vertex in vertices]
    faces = [[vertices[i] for i in face] for face in idx_faces]
    uv = polh_dic['uv']
    geomnode = make_geometry(faces, uv)
    return geomnode


class Singleton(NodePath):

    _instances = dict()

    def __init__(self, geomnode):
        super().__init__(geomnode)
        self.setTwoSided(True)


class Cube(Singleton):

    @classmethod
    def make(cls):
        if cls not in cls._instances:
            geomnode = make_node(CUBE)
            cls._instances[cls] = cls(geomnode)
        return cls._instances[cls]


class DecagonalPrism(Singleton):

    @classmethod
    def make(cls):
        if cls not in cls._instances:
            geomnode = make_node(DECAGONAL_PRISM)
            cls._instances[cls] = cls(geomnode)
        return cls._instances[cls]


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

# cube_normal_vecs = [
#     [Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0), Vec3(-1, 0, 0)],
#     [Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0), Vec3(0, -1, 0)],
#     [Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1), Vec3(0, 0, 1)],
#     [Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0), Vec3(0, 1, 0)],
#     [Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(1, 0, 0)],
#     [Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1), Vec3(0, 0, -1)]
# ]
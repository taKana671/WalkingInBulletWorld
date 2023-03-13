import array
import math

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


def make_tube(segs_a=5, segs_c=12, height=2.0, radius=0.5):
    arr_format = GeomVertexArrayFormat()
    arr_format.add_column('vertex', 3, Geom.NTFloat32, Geom.CPoint)
    arr_format.add_column('normal', 3, Geom.NTFloat32, Geom.CColor)
    arr_format.add_column('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
    fmt = GeomVertexFormat.register_format(arr_format)

    vdata_values = array.array('f', [])
    prim_indices = array.array('H', [])

    # segs_c = 12
    # segs_a = 5
    # height = 2.0
    delta_angle = 2.0 * math.pi / segs_c
    # radius = 0.5

    for i in range(segs_a + 1):
        z = height * i / segs_a
        v = i / segs_a

        for j in range(segs_c + 1):
            angle = delta_angle * j
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            normal_vec = Vec3(x, y, 0).normalized()
            u = j / segs_c

            vdata_values.extend((x, y, z))
            vdata_values.extend(normal_vec)
            vdata_values.extend((u, v))

    for i in range(segs_a):
        for j in range(0, segs_c):
            idx = j + i * (segs_c + 1)
            prim_indices.extend([idx, idx + 1, idx + segs_c + 1])
            prim_indices.extend([idx + segs_c + 1, idx + 1, idx + 1 + segs_c + 1])

    vdata = GeomVertexData('tube', fmt, Geom.UHStatic)
    rows = (segs_c + 1) * (segs_a + 1)
    vdata.unclean_set_num_rows(rows)
    vdata_mem = memoryview(vdata.modifyArray(0)).cast('B').cast('f')
    vdata_mem[:] = vdata_values

    prim = GeomTriangles(Geom.UHStatic)
    prim_array = prim.modify_vertices()
    prim_array.unclean_set_num_rows(len(prim_indices))
    prim_mem = memoryview(prim_array).cast('B').cast('H')
    prim_mem[:] = prim_indices

    node = GeomNode('geomnode')
    geom = Geom(vdata)
    geom.add_primitive(prim)
    node.add_geom(geom)

    return node


def make_torus(segs_r=24, segs_s=12, ring_radius=1.2, section_radius=0.5):
    arr_format = GeomVertexArrayFormat()
    arr_format.add_column('vertex', 3, Geom.NTFloat32, Geom.CPoint)
    arr_format.add_column('normal', 3, Geom.NTFloat32, Geom.CColor)
    arr_format.add_column('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
    fmt = GeomVertexFormat.register_format(arr_format)

    vdata_values = array.array('f', [])
    prim_indices = array.array('H', [])

    # segs_r = 24  # 24
    # segs_s = 12  # 16
    # ring_radius = 1.2
    # section_radius = 0.5

    delta_angle_h = 2.0 * math.pi / segs_r
    delta_angle_v = 2.0 * math.pi / segs_s

    for i in range(segs_r + 1):
        angle_h = delta_angle_h * i
        u = i / segs_r

        for j in range(segs_s + 1):
            angle_v = delta_angle_v * j
            r = ring_radius - section_radius * math.cos(angle_v)
            c = math.cos(angle_h)
            s = math.sin(angle_h)

            x = r * c
            y = r * s
            z = section_radius * math.sin(angle_v)
            nx = x - ring_radius * c
            ny = y - ring_radius * s
            normal_vec = Vec3(nx, ny, z).normalized()
            v = 1.0 - j / segs_s

            vdata_values.extend((x, y, z))
            vdata_values.extend(normal_vec)
            vdata_values.extend((u, v))

    for i in range(segs_r):
        for j in range(0, segs_s):
            idx = j + i * (segs_s + 1)
            prim_indices.extend([idx, idx + 1, idx + segs_s + 1])
            prim_indices.extend([idx + segs_s + 1, idx + 1, idx + 1 + segs_s + 1])

    vdata = GeomVertexData('torous', fmt, Geom.UHStatic)
    rows = (segs_r + 1) * (segs_s + 1)
    vdata.unclean_set_num_rows(rows)
    vdata_mem = memoryview(vdata.modify_array(0)).cast('B').cast('f')
    vdata_mem[:] = vdata_values

    prim = GeomTriangles(Geom.UHStatic)
    prim_array = prim.modify_vertices()
    prim_array.unclean_set_num_rows(len(prim_indices))
    prim_mem = memoryview(prim_array).cast('B').cast('H')
    prim_mem[:] = prim_indices

    node = GeomNode('geomnode')
    geom = Geom(vdata)
    geom.add_primitive(prim)
    node.add_geom(geom)

    return node


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
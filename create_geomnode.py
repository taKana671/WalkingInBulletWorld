import array
import math

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import Geom, GeomNode, GeomTriangles
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat

from utils import singleton


class GeomRoot(NodePath):

    def __init__(self, geomnode):
        super().__init__(geomnode)
        self.set_two_sided(True)

    def create_format(self):
        arr_format = GeomVertexArrayFormat()
        arr_format.add_column('vertex', 3, Geom.NTFloat32, Geom.CPoint)
        arr_format.add_column('color', 4, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('normal', 3, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
        fmt = GeomVertexFormat.register_format(arr_format)
        return fmt


class Polyhedrons(GeomRoot):

    def __init__(self):
        geomnode = self.create_geomnode()
        super().__init__(geomnode)

    def __init_subclass__(cls):
        super().__init_subclass__()
        if not hasattr(cls, 'create_geomnode'):
            raise NotImplementedError()

    def create_polyhedron(self, faces, texcoords, normal_vecs):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])
        start = 0

        for face, coords, vecs in zip(faces, texcoords, normal_vecs):
            for pt, uv, vec in zip(face, coords, vecs):
                vdata_values.extend(pt)
                vdata_values.extend((1, 1, 1, 1))
                vdata_values.extend(vec)
                vdata_values.extend(uv)

            for indices in self.get_prim_indices(start, len(face)):
                prim_indices.extend(indices)
            start += len(face)

        vdata = GeomVertexData('cube', fmt, Geom.UHStatic)
        num_rows = sum(len(face) for face in faces)
        vdata.unclean_set_num_rows(num_rows)
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

    def get_prim_indices(self, start, n):
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


@singleton
class Cube(Polyhedrons):

    def create_geomnode(self):
        face_vertices = [[CUBE['vertices'][i] for i in face] for face in CUBE['faces']]

        geomnode = self.create_polyhedron(
            face_vertices,
            CUBE['uv'],
            CUBE['normal']
        )
        return geomnode


@singleton
class DecagonalPrism(Polyhedrons):

    def calc_norm(self, face_vertices, z_vals):
        for vertices, z in zip(face_vertices, z_vals):
            yield [Vec3(v[0], v[1], 0).normalized() if v == 0 else Vec3(0, 0, z) for v in vertices]

    def create_geomnode(self):
        vertices = DECAGONAL_PRISM['vertices']
        faces = DECAGONAL_PRISM['faces']
        z_vals = DECAGONAL_PRISM['z']
        face_vertices = [[vertices[i] for i in face] for face in faces]
        normal = [norms for norms in self.calc_norm(face_vertices, z_vals)]

        geomnode = self.create_polyhedron(
            face_vertices,
            DECAGONAL_PRISM['uv'],
            normal
        )
        return geomnode


@singleton
class RightTriangularPrism(Polyhedrons):

    def create_geomnode(self):
        vertices = RIGHT_TRIANGULAR_PRISM['vertices']
        faces = RIGHT_TRIANGULAR_PRISM['faces']
        face_vertices = [[vertices[i] for i in face] for face in faces]

        geomnode = self.create_polyhedron(
            face_vertices,
            RIGHT_TRIANGULAR_PRISM['uv'],
            RIGHT_TRIANGULAR_PRISM['normal']
        )
        return geomnode


class Tube(GeomRoot):
    """Create a geom node of the tube.
       Args:
            segs_a (int): subdivisions of the mantle along the rotation axis;
            segs_c (int): subdivisions of the mantle along a circular cross_section;
            height (float): the length of the tube;
            radius (float): the radius of the tube; cannot be negative;
    """

    def __init__(self, segs_a=5, segs_c=12, height=2.0, radius=0.5):
        geomnode = self.create_tube(segs_a, segs_c, height, radius)
        super().__init__(geomnode)

    def create_tube(self, segs_a, segs_c, height, radius):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])
        delta_angle = 2.0 * math.pi / segs_c

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
                vdata_values.extend((1, 1, 1, 1))
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


class RingShape(GeomRoot):
    """Create a geom node of torus, spiral, half ring and so on.
       Args:
            segs_rcnt (int): the number of segments
            segs_r (int): the number of segments of the ring
            segs_s (int): the number of segments of the cross-sections
            ring_radius (float): the radius of the ring; cannot be negative;
            section_radius (float): the radius of the cross-sections perpendicular to the ring; cannot be negative;
            slope (float): the increase of the cross-sections hight
    """

    def __init__(self, segs_rcnt=24, segs_r=24, segs_s=12, ring_radius=1.2, section_radius=0.5, slope=0):
        geomnode = self.create_ring(segs_rcnt, segs_r, segs_s, ring_radius, section_radius, slope)
        super().__init__(geomnode)

    def create_ring(self, segs_rcnt, segs_r, segs_s, ring_radius, section_radius, slope):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])

        delta_angle_h = 2.0 * math.pi / segs_r
        delta_angle_v = 2.0 * math.pi / segs_s

        for i in range(segs_rcnt + 1):
            angle_h = delta_angle_h * i
            u = i / segs_rcnt

            for j in range(segs_s + 1):
                angle_v = delta_angle_v * j
                r = ring_radius - section_radius * math.cos(angle_v)
                c = math.cos(angle_h)
                s = math.sin(angle_h)

                x = r * c
                y = r * s
                z = section_radius * math.sin(angle_v) + slope * i

                nx = x - ring_radius * c
                ny = y - ring_radius * s
                normal_vec = Vec3(nx, ny, z).normalized()
                v = 1.0 - j / segs_s
                vdata_values.extend((x, y, z))
                vdata_values.extend((1, 1, 1, 1))
                vdata_values.extend(normal_vec)
                vdata_values.extend((u, v))

        for i in range(segs_rcnt):
            for j in range(0, segs_s):
                idx = j + i * (segs_s + 1)
                prim_indices.extend([idx, idx + 1, idx + segs_s + 1])
                prim_indices.extend([idx + segs_s + 1, idx + 1, idx + 1 + segs_s + 1])

        vdata = GeomVertexData('torous', fmt, Geom.UHStatic)
        rows = (segs_rcnt + 1) * (segs_s + 1)
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


@singleton
class SphericalShape(GeomRoot):

    def __init__(self, radius=1.5, segments=22):
        geomnode = self.create_sphere(radius, segments)
        super().__init__(geomnode)

    def create_sphere(self, radius, segments):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])

        delta_angle = 2 * math.pi / segments
        color = (1, 1, 1, 1)
        vertex_count = 0

        # the bottom pole vertices
        normal = (0.0, 0.0, -1.0)
        vertex = (0.0, 0.0, -radius)

        for i in range(segments):
            u = i / segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 0.0))

            # the vertex order of the pole vertices
            prim_indices.extend((i, i + segments + 1, i + segments))

        vertex_count += segments

        # the quad vertices
        index_offset = segments

        for i in range((segments - 2) // 2):
            angle_v = delta_angle * (i + 1)
            radius_h = radius * math.sin(angle_v)
            z = radius * -math.cos(angle_v)
            v = 2.0 * (i + 1) / segments

            for j in range(segments + 1):
                angle = delta_angle * j
                c = math.cos(angle)
                s = math.sin(angle)
                x = radius_h * c
                y = radius_h * s
                normal = Vec3(x, y, z).normalized()
                u = j / segments

                vdata_values.extend((x, y, z))
                vdata_values.extend(color)
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

                # the vertex order of the quad vertices
                if i > 0 and j <= segments:
                    px = i * (segments + 1) + j + index_offset
                    prim_indices.extend((px, px - segments - 1, px - segments))
                    prim_indices.extend((px, px - segments, px + 1))

            vertex_count += segments + 1

        # the top pole vertices
        normal = (0.0, 0.0, 1.0)
        vertex = (0.0, 0.0, radius)
        index_offset = vertex_count - segments - 1

        for i in range(segments):
            u = i / segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 1.0))

            # the vertex order of the top pole vertices
            x = i + index_offset
            prim_indices.extend((x, x + 1, x + segments + 1))

        vertex_count += segments

        vdata = GeomVertexData('sphere', fmt, Geom.UHStatic)
        vdata.unclean_set_num_rows(vertex_count)
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


CUBE = {
    'vertices': [
        (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
        (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)
    ],
    'faces': [
        (0, 1, 5, 4), (0, 4, 7, 3), (0, 3, 2, 1),
        (1, 2, 6, 5), (2, 3, 7, 6), (4, 5, 6, 7)
    ],
    # 'uv': [
    #     ((1, 1), (0.75, 1), (0.75, 0), (1, 0)),
    #     ((0, 1), (0, 0), (0.25, 0), (0.25, 1)),
    #     ((0, 0), (1, 0), (1, 1), (0, 1)),
    #     ((0.75, 1), (0.5, 1), (0.5, 0), (0.75, 0)),
    #     ((0.5, 1), (0.25, 1), (0.25, 0), (0.5, 0)),
    #     ((0, 0), (1, 0), (1, 1), (0, 1)),
    # ],
    'uv': [
        ((1, 1), (0.9, 1), (0.9, 0), (1, 0)),
        ((0, 1), (0, 0), (0.4, 0), (0.4, 1)),
        ((0, 0), (1, 0), (1, 1), (0, 1)),
        ((0.9, 1), (0.5, 1), (0.5, 0), (0.9, 0)),
        ((0.5, 1), (0.4, 1), (0.4, 0), (0.5, 0)),
        # ((1, 0), (0.9, 0), (0.5, 0), (0.4, 0))
        ((0, 0), (1, 0), (1, 1), (0, 1)),
    ],
    'normal': [
        [(-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0)],
        [(0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0)],
        [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)],
        [(0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0)],
        [(1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0)],
        [(0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1)]
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
        (0, 9, 8, 7, 6, 5, 4, 3, 2, 1),
        (0, 1, 11, 10),
        (0, 10, 19, 9),
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
        ((0.9, 1), (1, 1), (0.1, 1), (0.2, 1), (0.3, 1), (0.4, 1), (0.5, 1), (0.6, 1), (0.7, 1), (0.8, 1)),
        ((0.9, 1), (0.8, 1), (0.8, 0), (0.9, 0)),
        ((0.9, 1), (0.9, 0), (1, 0), (1, 1)),
        ((0.8, 1), (0.7, 1), (0.7, 0), (0.8, 0)),
        ((0.7, 1), (0.6, 1), (0.6, 0), (0.7, 0)),
        ((0.6, 1), (0.5, 1), (0.5, 0), (0.6, 0)),
        ((0.5, 1), (0.4, 1), (0.4, 0), (0.5, 0)),
        ((0.4, 1), (0.3, 1), (0.3, 0), (0.4, 0)),
        ((0.3, 1), (0.2, 1), (0.2, 0), (0.3, 0)),
        ((0.2, 1), (0.1, 1), (0.1, 0), (0.2, 0)),
        ((0.1, 1), (0, 1), (0, 0), (0.1, 0)),
        ((0.9, 0), (1, 0), (0.1, 0), (0.2, 0), (0.3, 0), (0.4, 0), (0.5, 0), (0.6, 0), (0.7, 0), (0.8, 0)),
    ],
    'z': [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1]
}

RIGHT_TRIANGULAR_PRISM = {
    'vertices': [
        (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, -0.5, -0.5)
    ],
    'faces': [
        (0, 1, 4, 3),
        (0, 3, 5, 2),
        (1, 4, 5, 2),
        (0, 2, 1),
        (3, 5, 4)
    ],
    'uv': [
        [(1, 1), (0.7, 1), (0.7, 0), (1, 0)],
        [(0, 1), (0, 0), (0.35, 0), (0.35, 1)],
        [(0.7, 1), (0.7, 0), (0.35, 0), (0.35, 1)],
        # [(0, 1), (0.35, 1), (0.7, 1)],
        [(0, 0), (1, 0), (0, 1)],
        # [(0, 0), (0.35, 0), (0.7, 0)]
        [(0, 0), (1, 0), (0, 1)],
    ],
    'normal': [
        [(-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0)],
        [(0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0)],
        [(-0.57735, 0.57735, 0.57735), (-0.57735, 0.57735, -0.57735), (0.57735, -0.57735, -0.57735), (0.57735, -0.57735, 0.57735)],
        [(0, 0, 1), (0, 0, 1), (0, 0, 1)],
        [(0, 0, -1), (0, 0, -1), (0, 0, -1)]
    ]
}
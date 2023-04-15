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
    """Create a geom node of sphere.
       Args:
            radius (int): the radius of sphere;
            segments (int): the number of surface subdivisions;
    """

    def __init__(self, radius=1.5, segments=22):
        self.radius = radius
        self.segments = segments
        geomnode = self.create_sphere(radius, segments)
        super().__init__(geomnode)

    def create_bottom_pole(self, vdata_values, prim_indices):
        # the bottom pole vertices
        normal = (0.0, 0.0, -1.0)
        vertex = (0.0, 0.0, -self.radius)
        color = (1, 1, 1, 1)

        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 0.0))

            # the vertex order of the pole vertices
            prim_indices.extend((i, i + self.segments + 1, i + self.segments))

        return self.segments

    def create_quads(self, index_offset, vdata_values, prim_indices):
        delta_angle = 2 * math.pi / self.segments
        color = (1, 1, 1, 1)
        vertex_count = 0

        # the quad vertices
        for i in range((self.segments - 2) // 2):
            angle_v = delta_angle * (i + 1)
            radius_h = self.radius * math.sin(angle_v)
            z = self.radius * -math.cos(angle_v)
            v = 2.0 * (i + 1) / self.segments

            for j in range(self.segments + 1):
                angle = delta_angle * j
                c = math.cos(angle)
                s = math.sin(angle)
                x = radius_h * c
                y = radius_h * s
                normal = Vec3(x, y, z).normalized()
                u = j / self.segments

                vdata_values.extend((x, y, z))
                vdata_values.extend(color)
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

                # the vertex order of the quad vertices
                if i > 0 and j <= self.segments:
                    px = i * (self.segments + 1) + j + index_offset
                    prim_indices.extend((px, px - self.segments - 1, px - self.segments))
                    prim_indices.extend((px, px - self.segments, px + 1))

            vertex_count += self.segments + 1

        return vertex_count

    def create_top_pole(self, index_offset, vdata_values, prim_indices):
        vertex = (0.0, 0.0, self.radius)
        normal = (0.0, 0.0, 1.0)
        color = (1, 1, 1, 1)

        # the top pole vertices
        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 1.0))

            # the vertex order of the top pole vertices
            x = i + index_offset
            prim_indices.extend((x, x + 1, x + self.segments + 1))

        return self.segments

    def create_sphere(self, radius, segments):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])
        vertex_count = 0

        # create vertices of the bottom pole, quads, and top pole
        vertex_count += self.create_bottom_pole(vdata_values, prim_indices)
        vertex_count += self.create_quads(vertex_count, vdata_values, prim_indices)
        vertex_count += self.create_top_pole(vertex_count - segments - 1, vdata_values, prim_indices)

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


@singleton
class Cylinder(GeomRoot):
    """Create a geom node of cylinder.
       Args:
            radius (float): the radius of the cylinder; cannot be negative;
            segs_c (int): subdivisions of the mantle along a circular cross-section; mininum is 3;
            height (int): length of the cylinder;
            segs_a (int): subdivisions of the mantle along the axis of rotation; minimum is 1;
    """

    def __init__(self, radius=0.5, segs_c=20, height=1, segs_a=2):
        self.radius = radius
        self.segs_c = segs_c
        self.height = height
        self.segs_a = segs_a
        geomnode = self.create_cylinder()
        super().__init__(geomnode)

    def cap_vertices(self, delta_angle, bottom=True):
        z = 0 if bottom else self.height

        # vertex and uv of the center
        yield ((0, 0, z), (0.5, 0.5))

        # vertex and uv of triangles
        for i in range(self.segs_c):
            angle = delta_angle * i
            c = math.cos(angle)
            s = math.sin(angle)
            x = self.radius * c
            y = self.radius * s
            u = 0.5 + c * 0.5
            v = 0.5 - s * 0.5
            yield ((x, y, z), (u, v))

    def create_bottom_cap(self, delta_angle, vdata_values, prim_indices):
        normal = (0, 0, -1)
        color = (1, 1, 1, 1)

        # bottom cap center and triangle vertices
        for vertex, uv in self.cap_vertices(delta_angle, bottom=True):
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend(uv)

        # the vertex order of the bottom cap vertices
        for i in range(self.segs_c - 1):
            prim_indices.extend((0, i + 2, i + 1))
        prim_indices.extend((0, 1, self.segs_c))

        return self.segs_c + 1

    def create_mantle(self, index_offset, delta_angle, vdata_values, prim_indices):
        vertex_count = 0

        # mantle triangle vertices
        for i in range(self.segs_a + 1):
            z = self.height * i / self.segs_a
            v = i / self.segs_a

            for j in range(self.segs_c + 1):
                angle = delta_angle * j
                x = self.radius * math.cos(angle)
                y = self.radius * math.sin(angle)
                normal = Vec3(x, y, 0.0).normalized()
                u = j / self.segs_c
                vdata_values.extend((x, y, z))
                vdata_values.extend((1, 1, 1, 1))
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

            vertex_count += self.segs_c + 1

            # the vertex order of the mantle vertices
            if i > 0:
                for j in range(self.segs_c):
                    px = index_offset + i * (self.segs_c + 1) + j
                    prim_indices.extend((px, px - self.segs_c - 1, px - self.segs_c))
                    prim_indices.extend((px, px - self.segs_c, px + 1))

        return vertex_count

    def create_top_cap(self, index_offset, delta_angle, vdata_values, prim_indices):
        normal = (0, 0, 1)
        color = (1, 1, 1, 1)

        # top cap center and triangle vertices
        for vertex, uv in self.cap_vertices(delta_angle, bottom=False):
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend(uv)

        # the vertex order of top cap vertices
        for i in range(index_offset + 1, index_offset + self.segs_c):
            prim_indices.extend((index_offset + self.segs_c, i - 1, i))
        prim_indices.extend((index_offset + self.segs_c, index_offset, index_offset + self.segs_c - 1))

        return self.segs_c + 1

    def create_cylinder(self):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])
        delta_angle = 2 * math.pi / self.segs_c
        vertex_count = 0

        # create vertices of the bottom cap, mantle and top cap.
        vertex_count += self.create_bottom_cap(delta_angle, vdata_values, prim_indices)
        vertex_count += self.create_mantle(vertex_count, delta_angle, vdata_values, prim_indices)
        vertex_count += self.create_top_cap(vertex_count, delta_angle, vdata_values, prim_indices)

        vdata = GeomVertexData('cylinder', fmt, Geom.UHStatic)
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
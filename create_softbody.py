from panda3d.bullet import BulletSoftBodyNode
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHelper
from panda3d.bullet import BulletTriangleMeshShape, BulletTriangleMesh
from panda3d.core import NodePath
from panda3d.core import GeomNode, RopeNode, PandaNode
from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import GeomVertexFormat
from panda3d.core import NurbsCurveEvaluator
from panda3d.bullet import BulletSoftBodyConfig

from create_geomnode import Tube, RingShape


class Pipe(NodePath):

    def __init__(self, model, pos, hpr, scale, bit):
        super().__init__(BulletRigidBodyNode('pipe'))
        self.model = model.copy_to(self)
        mesh = BulletTriangleMesh()
        mesh.add_geom(self.model.node().get_geom(0))
        shape = BulletTriangleMeshShape(mesh, dynamic=False)
        self.node().add_shape(shape)
        self.node().set_mass(1)
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)
        self.set_collide_mask(BitMask32.bit(bit))
        self.set_color(1, 0, 0, 1)
        # self.node().set_kinematic(True)


# class Ring(NodePath):

#     def __init__(self, model, pos, hpr, scale):
#         super().__init__(BulletRigidBodyNode('ring'))
#         self.model = model.copy_to(self)
#         mesh = BulletTriangleMesh()
#         mesh.add_geom(self.model.node().get_geom(0))
#         shape = BulletTriangleMeshShape(mesh, dynamic=False)
#         self.node().add_shape(shape)
#         self.node().set_mass(1)
#         self.set_pos(pos)
#         self.set_hpr(hpr)
#         self.set_scale(scale)
#         self.set_collide_mask(BitMask32.all_on())


class Car(NodePath):

    def __init__(self, pos, world, r, b):
        super().__init__(PandaNode('car'))
        self.world = world
        # self.create_car(pos)
        self.roof = r
        self.board = b

        self.create_rope()
        self.reparent_to(base.render)


    def create_car(self, pos):
        geomnode = RingShape(ring_radius=0.5, segs_r=6, section_radius=0.05)
        # edge1 = Pipe(ring_geomnode, Point3(0, 0, 0), Vec3(0, 0, 0), Vec3(1))
        self.car = Pipe(geomnode, pos, Vec3(0, 90, 90), Vec3(2, 2, 10), 1)
        # edge1.reparent_to(self.car)
        self.car.reparent_to(self)
        self.world.attach(self.car.node())

        # geomnode2 = RingShape(ring_radius=0.5, segs_r=6, section_radius=0.05)
        # car2 = Pipe(geomnode2, Point3(0, -1, 0), Vec3(0, 0, 0), Vec3(1, 1, 1), 2)
        # car2.node().set_kinematic(True)
        # # car2.set_pos(0, 0, -1)
        # car2.reparent_to(self.car)
        # self.world.attach(car2.node())

    def create_rope(self):
        info = self.world.get_world_info()
        info.set_air_density(1.2)
        info.set_water_density(0)
        info.set_water_offset(0)
        info.set_water_normal(Vec3(0, 0, 0))

        res = 8
        # p1 = Point3(0, 0, 4)
        # p2 = Point3(10, 0, 4)
        # p1 = Point3(-2.875, 1.875, 9) + Point3(70, -15, -1.5)
        # # p2 = Point3(0.5, 0.5, 7) + Point3(70, -15, -1.5)
        # p2 = Point3(0, 2, 5) + Point3(70, -15, -1.5)
        fixeds = 1

        ropes = NodePath('Ropes')
        ropes.reparent_to(self)

        p1 = Point3(-1.75, 5.75, 9.5) + Point3(70, -15, -1.5)
        p2 = Point3(-1.75, 5.75, 3) + Point3(70, -15, -1.5)  

        rope = Rope(ropes, info, p1, p2, res, fixeds)
        self.world.attach_soft_body(rope.node())

        # rope.node().appendAnchor(0, self.roof.node(), Point3(-2, 2, -0.5))
        # rope.node().appendAnchor(rope.node().get_num_nodes() - 1, self.board.node(), Point3(-2, 2, 0.5))
        # rope.node().appendAnchor(0, self.roof.node())
        rope.node().appendAnchor(rope.node().get_num_nodes() - 1, self.board.node())


        p1_2 = Point3(1.75, 5.75, 9.25) + Point3(70, -15, -1.5)
        p2_2 = Point3(1.75, 5.75, 3.25) + Point3(70, -15, -1.5)  
        rope_2 = Rope(ropes, info, p1_2, p2_2, res, fixeds)
        self.world.attach_soft_body(rope_2.node())

        # rope_2.node().appendAnchor(0, self.roof.node())
        rope_2.node().appendAnchor(rope.node().get_num_nodes() - 1, self.board.node())


        p1_3 = Point3(-1.75, 2.25, 9.25) + Point3(70, -15, -1.5)
        p2_3 = Point3(-1.75, 2.25, 3.25) + Point3(70, -15, -1.5)  
        rope_3 = Rope(ropes, info, p1_3, p2_3, res, fixeds)
        self.world.attach_soft_body(rope_3.node())

        # rope_3.node().appendAnchor(0, self.roof.node())
        rope_3.node().appendAnchor(rope.node().get_num_nodes() - 1, self.board.node())


        p1_4 = Point3(1.75, 2.25, 9.25) + Point3(70, -15, -1.5)
        p2_4 = Point3(1.75, 2.25, 3.25) + Point3(70, -15, -1.5)  
        rope_4 = Rope(ropes, info, p1_4, p2_4, res, fixeds)
        self.world.attach_soft_body(rope_4.node())

        # rope_4.node().appendAnchor(0, self.roof.node())
        rope_4.node().appendAnchor(rope.node().get_num_nodes() - 1, self.board.node())


class RopeMaker:

    def __init__(self, world):
        self.world = world
        self.info = self.world.get_world_info()
        self.info.set_air_density(1.2)
        self.info.set_water_density(0)
        self.info.set_water_offset(0)
        self.info.set_water_normal(Vec3(0, 0, 0))

        self.ropes = NodePath('Ropes')
        self.ropes.reparent_to(base.render)

    def attach_last_node(self, idx, tex, from_pt, to_pt, body, res=8):
        fixeds = 1
        rope = Rope(self.ropes, idx, tex, self.info, from_pt, to_pt, res, fixeds)
        self.world.attach_soft_body(rope.node())

        # rope.node().append_anchor(0, body.node())
        rope.node().append_anchor(rope.node().get_num_nodes() - 1, body.node())



class Rope(NodePath):

    def __init__(self, parent, idx, tex, info, from_pt, to_pt, res, fixeds):
        super().__init__(BulletSoftBodyNode.make_rope(info, from_pt, to_pt, res, fixeds))
        self.node().set_total_mass(50.0)
        self.node().get_shape(0).set_margin(0.1)
        self.set_name(f'rope_{idx}')
        self.reparent_to(parent)

        curve = NurbsCurveEvaluator()
        curve.reset(res + 2)
        self.node().link_curve(curve)

        self.rope = NodePath(RopeNode(f'visualized_rope_{idx}'))
        self.rope.node().set_curve(curve)
        self.rope.node().set_render_mode(RopeNode.RMTube)
        self.rope.node().set_uv_mode(RopeNode.UVParametric)
        self.rope.node().set_num_subdiv(4)
        self.rope.node().set_num_slices(8)
        self.rope.node().set_thickness(0.1)
        self.rope.reparent_to(parent)
        self.rope.set_texture(base.loader.loadTexture(tex))








class Cloth(NodePath):
# class Cloth:

    def __init__(self, world, obj, pt00, pt10, pt01, pt11, resx, resy, fixeds=15):
        super().__init__(PandaNode('cloth'))
        self.world = world
        # self.reparent_to(base.render)
        # self.world_np = NodePath('world')
        # self.world_np.reparent_to(base.render)
        self.create_cloth(pt00, pt10, pt01, pt11, resx, resy, fixeds, obj)
        # self.cloth = self.create_cloth2(pt00, pt10, pt01, pt11, resx, resy, fixeds)
        self.reparent_to(base.render)
        # self.reparent_to(parent)

    def create_cloth(self, pt00, pt10, pt01, pt11, resx, resy, fixeds, obj):
        info = self.world.get_world_info()
        info.set_air_density(1.2)
        info.set_water_density(0)
        info.set_water_offset(0)
        info.set_water_normal(Vec3(0, 0, 0))

        body_nd = BulletSoftBodyNode.make_patch(
            info, pt00, pt10, pt01, pt11, resx, resy, fixeds, True)

        material = body_nd.append_material()
        material.set_linear_stiffness(0.4)
        body_nd.generate_bending_constraints(2, material)
        body_nd.set_total_mass(50.0)
        body_nd.get_shape(0).set_margin(0.5)
        self.body_np = self.attach_new_node(body_nd)
        self.body_np.set_collide_mask(BitMask32.bit(1))
        self.world.attach_soft_body(body_nd)

        fmt = GeomVertexFormat.getV3n3t2()
        geom = BulletHelper.make_geom_from_faces(body_nd, fmt, True)
        body_nd.link_geom(geom)

        vis_nd = GeomNode('')
        vis_nd.add_geom(geom)
        vis_np = self.body_np.attach_new_node(vis_nd)
        tex = base.loader.load_texture('textures/grass.jpg')
        vis_np.set_texture(tex)
        BulletHelper.make_texcoords_for_patch(geom, resx, resy)

        self.body_np.node().appendAnchor(self.body_np.node().getNumNodes() - 1, obj.node())

        # import pdb; pdb.set_trace()

    # def create_cloth2(self, pt00, pt10, pt01, pt11, resx, resy, fixeds):
    #     info = self.world.get_world_info()
    #     info.set_air_density(1.2)
    #     info.set_water_density(0)
    #     info.set_water_offset(0)
    #     info.set_water_normal(Vec3(0, 0, 0))

    #     body_nd = BulletSoftBodyNode.make_patch(
    #         info, pt00, pt10, pt01, pt11, resx, resy, fixeds, True)

    #     body_path = NodePath(body_nd)
    #     material = body_path.node().append_material()
    #     material.set_linear_stiffness(0.4)
    #     body_path.node().generate_bending_constraints(2, material)
    #     body_path.node().set_total_mass(50.0)
    #     body_path.node().get_shape(0).set_margin(0.5)
    #     # body_np = self.attach_new_node(body_nd)
    #     body_path.set_collide_mask(BitMask32.bit(1))
    #     self.world.attach_soft_body(body_path.node())

    #     fmt = GeomVertexFormat.getV3n3t2()
    #     geom = BulletHelper.make_geom_from_faces(body_path.node(), fmt, True)
    #     body_path.node().link_geom(geom)

    #     vis_nd = GeomNode('')
    #     vis_nd.add_geom(geom)
    #     vis_np = body_path.attach_new_node(vis_nd)
    #     tex = base.loader.load_texture('textures/fabric1.jpg')
    #     vis_np.set_texture(tex)
    #     BulletHelper.make_texcoords_for_patch(geom, resx, resy)

    #     return body_path






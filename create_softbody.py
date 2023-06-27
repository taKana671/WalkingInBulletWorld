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

    def attach_last_node(self, suffix, tex, from_pt, to_pt, body, res=8):
        fixeds = 1
        rope = Rope(self.ropes, suffix, tex, self.info, from_pt, to_pt, res, fixeds)
        self.world.attach_soft_body(rope.node())
        rope.node().append_anchor(rope.node().get_num_nodes() - 1, body.node())


class ClothMaker:

    def __init__(self, world):
        self.world = world
        self.info = self.world.get_world_info()
        self.info.set_air_density(1.2)
        self.info.set_water_density(0)
        self.info.set_water_offset(0)
        self.info.set_water_normal(Vec3(0, 0, 0))

        self.cloths = NodePath('Cloths')
        self.cloths.reparent_to(base.render)

    def create_cloth(self, suffix, tex_path, pt00, pt10, pt01, pt11, resx, resy, fixeds=15):
        cloth = Cloth(self.cloths, suffix, tex_path, self.info, pt00, pt10, pt01, pt11, resx, resy, fixeds)
        self.world.attach_soft_body(cloth.node())


class Rope(NodePath):

    def __init__(self, parent, suffix, tex, info, from_pt, to_pt, res, fixeds):
        super().__init__(BulletSoftBodyNode.make_rope(info, from_pt, to_pt, res, fixeds))
        self.node().set_total_mass(50.0)
        self.node().get_shape(0).set_margin(0.1)
        self.set_name(f'rope_{suffix}')
        self.reparent_to(parent)

        curve = NurbsCurveEvaluator()
        curve.reset(res + 2)
        self.node().link_curve(curve)

        self.rope = NodePath(RopeNode(f'visualized_rope_{suffix}'))
        self.rope.node().set_curve(curve)
        self.rope.node().set_render_mode(RopeNode.RMTube)
        self.rope.node().set_uv_mode(RopeNode.UVParametric)
        self.rope.node().set_num_subdiv(4)
        self.rope.node().set_num_slices(8)
        self.rope.node().set_thickness(0.1)
        self.rope.reparent_to(parent)
        self.rope.set_texture(base.loader.loadTexture(tex))


class Cloth(NodePath):

    def __init__(self, parent, suffix, tex_path, info, pt00, pt10, pt01, pt11, resx, resy, fixeds):
        super().__init__(BulletSoftBodyNode.make_patch(info, pt00, pt10, pt01, pt11, resx, resy, fixeds, True))
        material = self.node().append_material()
        material.set_linear_stiffness(0.4)
        self.node().generate_bending_constraints(2, material)
        self.node().set_total_mass(50.0)
        self.node().get_shape(0).set_margin(0.5)
        self.set_name(f'cloth_{suffix}')
        self.reparent_to(parent)
        self.set_collide_mask(BitMask32.all_on())

        fmt = GeomVertexFormat.getV3n3t2()
        geom = BulletHelper.make_geom_from_faces(self.node(), fmt, True)
        self.node().link_geom(geom)

        self.cloth = NodePath(GeomNode(f'visualized_cloth_{suffix}'))
        self.cloth.node().add_geom(geom)
        self.cloth.reparent_to(self)
        self.cloth.set_texture(base.loader.load_texture(tex_path))
        BulletHelper.make_texcoords_for_patch(geom, resx, resy)



# class Cloth(NodePath):
# # class Cloth:

#     def __init__(self, world, obj, pt00, pt10, pt01, pt11, resx, resy, fixeds=15):
#         super().__init__(PandaNode('cloth'))
#         self.world = world
#         # self.reparent_to(base.render)
#         # self.world_np = NodePath('world')
#         # self.world_np.reparent_to(base.render)
#         self.create_cloth(pt00, pt10, pt01, pt11, resx, resy, fixeds, obj)
#         # self.cloth = self.create_cloth2(pt00, pt10, pt01, pt11, resx, resy, fixeds)
#         self.reparent_to(base.render)
#         # self.reparent_to(parent)

#     def create_cloth(self, pt00, pt10, pt01, pt11, resx, resy, fixeds, obj):
#         info = self.world.get_world_info()
#         info.set_air_density(1.2)
#         info.set_water_density(0)
#         info.set_water_offset(0)
#         info.set_water_normal(Vec3(0, 0, 0))

#         body_nd = BulletSoftBodyNode.make_patch(
#             info, pt00, pt10, pt01, pt11, resx, resy, fixeds, True)

#         material = body_nd.append_material()
#         material.set_linear_stiffness(0.4)
#         body_nd.generate_bending_constraints(2, material)
#         body_nd.set_total_mass(50.0)
#         body_nd.get_shape(0).set_margin(0.5)
#         self.body_np = self.attach_new_node(body_nd)
#         self.body_np.set_collide_mask(BitMask32.bit(1))
#         self.world.attach_soft_body(body_nd)

#         fmt = GeomVertexFormat.getV3n3t2()
#         geom = BulletHelper.make_geom_from_faces(body_nd, fmt, True)
#         body_nd.link_geom(geom)

#         vis_nd = GeomNode('')
#         vis_nd.add_geom(geom)
#         vis_np = self.body_np.attach_new_node(vis_nd)
#         tex = base.loader.load_texture('textures/grass.jpg')
#         vis_np.set_texture(tex)
#         BulletHelper.make_texcoords_for_patch(geom, resx, resy)

#         self.body_np.node().appendAnchor(self.body_np.node().getNumNodes() - 1, obj.node())


from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState
from panda3d.core import CardMaker, TextureStage
from panda3d.core import TransparencyAttrib
from direct.interval.LerpInterval import LerpTexOffsetInterval

from buildings import StoneHouse, BrickHouse, Terrace, Observatory, Bridge, Tunnel


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D Walking In BulletWorld
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        sky = base.loader.load_model('models/blue-sky/blue-sky-sphere')
        sky.set_color(2, 2, 2, 1)
        sky.set_scale(0.2)
        sky.reparent_to(self)


class TerrainShape(NodePath):

    def __init__(self, img):
        super().__init__(BulletRigidBodyNode('terrain_shape'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        self.node().add_shape(shape)
        self.node().set_mass(0)
        self.set_collide_mask(BitMask32.bit(1))


class Water(NodePath):

    def __init__(self, size):
        super().__init__(NodePath('water'))
        card = CardMaker('surface')
        card.set_frame(0, size, 0, size)
        self.surface = self.attach_new_node(card.generate())
        self.surface.look_at(Vec3.down())
        self.surface.set_transparency(TransparencyAttrib.MAlpha)
        self.surface.set_texture(base.loader.load_texture('textures/water.png'))
        self.surface.set_tex_scale(TextureStage.get_default(), 4)


class Scene(NodePath):

    def __init__(self, world):
        super().__init__(PandaNode('scene'))
        self.reparent_to(base.render)
        self.world = world
        self.size = 256  # size of terrain and water

        # make sky
        self.sky = Sky()
        self.sky.reparent_to(self)

        # make terrain
        self.terrains = NodePath('terrain')
        self.terrains.reparent_to(self)
        self.make_terrain('terrains/heightfield7.png')

        # make water
        self.water = Water(self.size)
        pos = self.terrain.get_pos()
        pos.z = -3
        self.water.reparent_to(self)
        self.water.set_pos(pos)
        LerpTexOffsetInterval(self.water.surface, 200, (1, 0), (0, 0)).loop()

        # make buildings
        self.buildings = NodePath('buildings')
        self.buildings.reparent_to(self)
        self.make_buildings()

    def make_buildings(self):

        buildings = [
            [StoneHouse, Point3(38, 75, 1), 0],
            [BrickHouse, Point3(50, -27, 0), -45],
            [Terrace, Point3(1, 1, -2), -180],
            [Observatory, Point3(-80, 80, -2.5), 45],
            [Bridge, Point3(38, 43, 1), 0],
            [Tunnel, Point3(-45, -68, 3), 222],
        ]
        for bldg, pos, h in buildings:
            building = bldg(self.world, self.buildings, pos, h)
            building.build()

    def make_terrain(self, img_file):
        img = PNMImage(Filename(img_file))
        terrain_shape = TerrainShape(img)
        terrain_shape.reparent_to(self.terrains)
        self.world.attach(terrain_shape.node())

        terrain_node = ShaderTerrainMesh()
        heightfield = base.loader.load_texture(img_file)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = self.terrains.attach_new_node(terrain_node)
        self.terrain.set_scale(self.size, self.size, 10)
        offset = img.get_x_size() / 2.0 - 0.5
        self.terrain.set_pos(-offset, -offset, -10 / 2.0)  # terrain bottom left. terrain_pos LPoint3f(-127.5, -127.5, -5)

        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", base.camera)
        grass_tex = base.loader.load_texture('textures/grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.set_texture(grass_tex)
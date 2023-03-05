from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath, PandaNode, TransformState
from panda3d.core import Vec3, Point3, LColor, BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState

from panda3d.core import CardMaker, TextureStage

from panda3d.core import TransparencyAttrib
from panda3d.core import BitMask32, LPoint3, NodePath, PandaNode
from direct.interval.LerpInterval import LerpTexOffsetInterval

from buildings import StoneHouse, BrickHouse, Terrace, Observatory

load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D ShaderTerrainMesh Demo
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Scene(NodePath):

    def __init__(self, world):
        super().__init__(PandaNode('scene'))
        self.reparentTo(base.render)
        self.world = world
        self.make_terrain('terrains/heightfield7.png')
        self.make_water()
        self.make_buildings()
        print(self.getChildren())

    def make_buildings(self):
        # buildings = [
        #     [StoneHouse, Point3(20, 10, -4), 0],
        #     [BrickHouse, Point3(60, 30, -2.8), -45],
        #     [Terrace, Point3(-30, 10, -3.5), 45],
        #     [Observatory, Point3(-93, 42, -2.5), 0]
        # ]

        # for _class, pos, h in buildings:
        #     building = _class(self.world, pos, h)
        #     building.build()

        stone_house = StoneHouse(self.world, Point3(38, 75, 1))
        stone_house.build()

        brick_house = BrickHouse(self.world, Point3(75, -39, -2), 160)
        brick_house.build()

        terrace = Terrace(self.world, Point3(1, 1, -2), -180)
        terrace.build()
        observatory = Observatory(self.world, Point3(-80, 80, -2.5), 45)
        observatory.build()

    def make_terrain(self, img_heightfield):
        img = PNMImage(Filename(img_heightfield))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        nd = BulletRigidBodyNode('test')
        nd.addShape(shape)
        nd.setMass(0)
        # np.setCollideMask(BitMask32.bit(1))
        self.world.attachRigidBody(nd)

        terrain_node = ShaderTerrainMesh()
        heightfield = base.loader.loadTexture(img_heightfield)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = self.attachNewNode(terrain_node)
        self.terrain.setScale(256, 256, 10)
        offset = img.getXSize() / 2.0 - 0.5
        self.terrain.setPos(-offset, -offset, -10 / 2.0)  # terrain bottom left. terrain_pos LPoint3f(-127.5, -127.5, -5)

        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", base.camera)
        grass_tex = base.loader.loadTexture('textures/grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.setTexture(grass_tex)

    def make_water(self):
        card = CardMaker('water')
        card.setFrame(0, 256, 0, 256)
        self.water = self.attachNewNode(card.generate())
        self.water.lookAt(Vec3.down())
        self.water.setPos(Point3(-127.5, -127.5, -3))
        self.water.setTransparency(TransparencyAttrib.MAlpha)
        self.water.setTexture(base.loader.loadTexture('textures/water2.png'))
        self.water.setTexScale(TextureStage.getDefault(), 4)
        LerpTexOffsetInterval(self.water, 200, (1, 0), (0, 0)).loop()
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

from buildings import StoneHouse, BrickHouse, Terrace, Observatory, Bridge, Garden

load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D ShaderTerrainMesh Demo
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        sky = base.loader.loadModel('models/blue-sky/blue-sky-sphere')
        sky.setColor(2, 2, 2, 1)
        sky.setScale(0.2)
        sky.reparentTo(self)


class TerrainShape(NodePath):

    def __init__(self, img):
        super().__init__(BulletRigidBodyNode('terrain_shape'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        self.node().addShape(shape)
        self.node().setMass(0)
        self.setCollideMask(BitMask32.bit(1))


class Water(NodePath):

    def __init__(self, size):
        super().__init__(NodePath('water'))
        card = CardMaker('surface')
        card.setFrame(0, size, 0, size)
        self.surface = self.attachNewNode(card.generate())
        self.surface.lookAt(Vec3.down())
        self.surface.setTransparency(TransparencyAttrib.MAlpha)
        self.surface.setTexture(base.loader.loadTexture('textures/water2.png'))
        self.surface.setTexScale(TextureStage.getDefault(), 4)


class Scene(NodePath):

    def __init__(self, world):
        super().__init__(PandaNode('scene'))
        self.reparentTo(base.render)
        self.world = world
        self.size = 256  # size of terrain and water

        # make sky
        self.sky = Sky()
        self.sky.reparentTo(self)

        # make terrain
        self.terrains = NodePath('terrain')
        self.terrains.reparentTo(self)
        self.make_terrain('terrains/heightfield7.png')

        # make water
        self.water = Water(self.size)
        pos = self.terrain.getPos()
        pos.z = -3
        self.water.reparentTo(self)
        self.water.setPos(pos)
        LerpTexOffsetInterval(self.water.surface, 200, (1, 0), (0, 0)).loop()

        # make buildings
        self.buildings = NodePath('buildings')
        self.buildings.reparentTo(self)
        self.make_buildings()

    def make_buildings(self):

        buildings = [
            [StoneHouse, Point3(38, 75, 1), 0],
            [BrickHouse, Point3(50, -27, 0), -45],
            [Terrace, Point3(1, 1, -2), -180],
            [Observatory, Point3(-80, 80, -2.5), 45],
            [Bridge, Point3(38, 43, 1), 0],
            # [Garden, Point3(38, -47, 2), 0]
        ]
        for bldg, pos, h in buildings:
            building = bldg(self.world, self.buildings, pos, h)
            building.build()

    def make_terrain(self, img_file):
        img = PNMImage(Filename(img_file))
        terrain_shape = TerrainShape(img)
        terrain_shape.reparentTo(self.terrains)
        self.world.attachRigidBody(terrain_shape.node())

        terrain_node = ShaderTerrainMesh()
        heightfield = base.loader.loadTexture(img_file)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = self.terrains.attachNewNode(terrain_node)
        self.terrain.setScale(self.size, self.size, 10)
        offset = img.getXSize() / 2.0 - 0.5
        self.terrain.setPos(-offset, -offset, -10 / 2.0)  # terrain bottom left. terrain_pos LPoint3f(-127.5, -127.5, -5)

        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", base.camera)
        grass_tex = base.loader.loadTexture('textures/grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.setTexture(grass_tex)
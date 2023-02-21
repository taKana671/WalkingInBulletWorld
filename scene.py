from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath
from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState

from buildings import StoneHouse, BrickHouse, Terrace, Observatory


class Scene:

    def __init__(self, world):
        self.world = world

        load_prc_file_data("", """
            textures-power-2 none
            gl-coordinate-system default
            window-title Panda3D ShaderTerrainMesh Demo
            filled-wireframe-apply-shader true
            stm-max-views 8
            stm-max-chunk-count 2048""")

        self.create_terrain()
        self.make_buildings()

    def make_buildings(self):
        stone_house = StoneHouse(self.world, Point3(20, 10, -4))
        stone_house.build()
        brick_house = BrickHouse(self.world, Point3(60, 30, -2.8), -45)
        brick_house.build()
        terrace = Terrace(self.world, Point3(-30, 10, -3.5), 45)
        terrace.build()

        observatory = Observatory(self.world, Point3(-114, 85, 0))
        observatory.build()


    def create_terrain(self):
        img = PNMImage(Filename('mytest.png'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        np = NodePath(BulletRigidBodyNode('test'))
        np.node().addShape(shape)
        np.setCollideMask(BitMask32.bit(1))
        self.world.attachRigidBody(np.node())

        terrain_node = ShaderTerrainMesh()
        heightfield = base.loader.loadTexture('mytest.png')
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = base.render.attachNewNode(terrain_node)
        self.terrain.setScale(256, 256, 10)
        offset = img.getXSize() / 2.0 - 0.5
        self.terrain.setPos(-offset, -offset, -10 / 2.0)

        terrain_shader = Shader.load(Shader.SL_GLSL, "terrain.vert.glsl", "terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", base.camera)
        grass_tex = base.loader.loadTexture('grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.setTexture(grass_tex)

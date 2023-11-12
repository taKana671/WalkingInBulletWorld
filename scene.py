from enum import Enum, auto

from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, Point3, BitMask32, LColor
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState
from panda3d.core import CardMaker, TextureStage, Texture
from panda3d.core import TransparencyAttrib
from direct.interval.LerpInterval import LerpTexOffsetInterval

from buildings import (
    StoneHouse,
    BrickHouse,
    Terrace,
    Observatory,
    Bridge,
    Tunnel,
    AdventureBridge,
    MazeHouse,
    ElevatorTower
)


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D Walking In BulletWorld
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Skies(Enum):

    DAY = auto()
    NIGHT = auto()


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        self.blue_sky = base.loader.load_model('models/blue-sky/blue-sky-sphere')
        self.night_sky = base.loader.load_model('models/night-stars/stars') 

        base.set_background_color(0, 0, 0, 1)
        self.set_shader_off()
        self.model = None

    def set_model(self, sky_type):
        """Change models.
            Args:
                sky_type (Skies):
        """
        if self.model:
            self.model.detach_node()

        match sky_type:
            case Skies.DAY:
                self.model = self.blue_sky
                self.model.set_color(2, 2, 2, 1)
                self.model.set_scale(0.2)
                self.model.set_z(0)

            case Skies.NIGHT:
                self.model = self.night_sky
                self.model.set_color(2, 2, 2, 1)
                self.model.set_scale(0.3)
                self.model.set_z(-50)

        self.model.reparent_to(self)


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

    def __init__(self, world, ambient_light, directional_light):
        super().__init__(PandaNode('scene'))
        self.reparent_to(base.render)
        self.world = world
        self.ambient_light = ambient_light
        self.directional_light = directional_light
        self.size = 256  # size of terrain and water

        # make sky
        self.sky = Sky()
        self.sky.reparent_to(self)
        self.sky.set_model(Skies.DAY)

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
        self.make_buildings()

    def make_buildings(self):
        self.buildings = NodePath('buildings')
        self.buildings.reparent_to(self)

        StoneHouse(self.world, self.buildings, Point3(38, 75, 1), 0).build()
        BrickHouse(self.world, self.buildings, Point3(50, -27, 0), -45).build()
        Terrace(self.world, self.buildings, Point3(1, 1, -2), -180).build()
        Observatory(self.world, self.buildings, Point3(-80, 80, -2.5), 45).build()
        Bridge(self.world, self.buildings, Point3(38, 43, 1), 0).build()
        Tunnel(self.world, self.buildings, Point3(-45, -68, 3), 222).build()
        AdventureBridge(self.world, self.buildings, Point3(92, -29, -1), 0).build()
        MazeHouse(self.world, self.buildings, Point3(-24, 87, -1.5), 0).build()
        ElevatorTower(self.world, self.buildings, Point3(87, 23, -3.5)).build()

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

    def change_sky(self, sky_type):
        match sky_type:
            case Skies.DAY:
                if self.sky.get_shader():
                    self.sky.clear_shader()

                self.sky.set_model(sky_type)
                self.directional_light.set_brightness()

            case Skies.NIGHT:
                self.sky.set_model(sky_type)
                self.directional_light.set_brightness(LColor(0, 0, 0, 1))

                self.sky.set_shader(
                    Shader.load(Shader.SL_GLSL, 'shaders/fireworks_v.glsl', 'shaders/fireworks_f.glsl'))
                props = base.win.get_properties()
                self.sky.set_shader_input('u_resolution', props.get_size())
                tex = Texture()
                self.sky.set_shader_input('tex', tex)

            case _:
                raise InvalidSkyError(sky_type)


class InvalidSkyError(Exception):

    def __init__(self, arg=""):
        self.arg = arg

    def __str__(self):
        return f'{self.arg} is invalid. Please specify from members of Skies.'

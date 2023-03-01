from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, Point3, LColor, BitMask32, Plane, PlaneNode, Mat4
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState

from panda3d.core import PTA_LVecBase4f, UnalignedLVecBase4f
from panda3d.core import CardMaker, Texture, CullFaceAttrib

from panda3d.core import TransparencyAttrib
from panda3d.core import FrameBufferProperties, TextNode, BitMask32, LPoint3
from panda3d.core import WindowProperties, GraphicsOutput, Texture, GraphicsPipe


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
        # self.create_water()

    def make_buildings(self):
        stone_house = StoneHouse(self.world, Point3(20, 10, -4))
        stone_house.build()
        brick_house = BrickHouse(self.world, Point3(60, 30, -2.8), -45)
        brick_house.build()
        terrace = Terrace(self.world, Point3(-30, 10, -3.5), 45)
        terrace.build()
        observatory = Observatory(self.world, Point3(-93, 42, -2.5))
        observatory.build()

    def create_terrain(self):
        img = PNMImage(Filename('terrains/heightfield.png'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        np = NodePath(BulletRigidBodyNode('test'))
        np.node().addShape(shape)
        np.setCollideMask(BitMask32.bit(1))
        self.world.attachRigidBody(np.node())

        terrain_node = ShaderTerrainMesh()
        heightfield = base.loader.loadTexture('terrains/heightfield.png')
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = base.render.attachNewNode(terrain_node)
        self.terrain.setScale(256, 256, 10)
        offset = img.getXSize() / 2.0 - 0.5
        self.terrain.setPos(-offset, -offset, -10 / 2.0)
        # print('terrain_pos', self.terrain.getPos()) terrain_pos LPoint3f(-127.5, -127.5, -5)

        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", base.camera)
        grass_tex = base.loader.loadTexture('textures/grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.setTexture(grass_tex)

    def create_water(self):
        size = 512  # size of the wave buffer
        pos = Point3(128.0, 300.0, 50.0)
        # pos = Point3(-127.5, 300.0, 50.0)
        # pos = Point3(20, 300, 50)
        radius = 500.0
        
        light_pos = (pos.x, pos.y, pos.z, radius ** 2)
        light_color = (0.9, 0.9, 0.9, 1.0)

        base.render.setShaderInput('light_pos', light_pos)
        base.render.setShaderInput('light_color', light_color)


        self.skybox = loader.loadModel('skybox/skybox')
        self.skybox.reparentTo(base.render)
        # skybox.setPos(128, 128, 64)
        self.skybox.setPos(-127.5, -127.5, -20)
        self.skybox.setScale(300)

        card = CardMaker('plane')
        card.setFrame(0, 256, 0, 256)
        self.water_plane = base.render.attachNewNode(card.generate())
        self.water_plane.lookAt(Vec3.down())
        self.water_plane.setPos(0, 127.5, -3)

        # self.water_plane.setColor(1, 0, 0, 1)
        self.water_plane.flattenStrong()

        self.water_plane.setShader(Shader.load(Shader.SL_GLSL, 'shaders/water_v.glsl', 'shaders/water_f.glsl'))
        # self.water_plane.setShader(base.loader.loadShader("shaders/water_shader.cg"))
        self.water_plane.setShaderInput('size', float(size))
        self.water_plane.setShaderInput('normal_map', base.loader.loadTexture('textures/water.png'))
        self.water_plane.hide(BitMask32.bit(1))


        # :::::::::::::::::::::
        # self.water_plane.setShaderInput('camera', base.camera)
        # :::::::::::::::::::::


        # # make water buffer
        self.water_buffer = base.win.makeTextureBuffer("water", size, size)
        self.water_buffer.setClearColor(base.win.getClearColor())
        self.water_buffer.setSort(-1)
        
        # winprops = WindowProperties()
        # props = FrameBufferProperties()
        # props.setRgbColor(1)
        # self.water_buffer = base.graphicsEngine.makeOutput(
        #     base.pipe, "model buffer", -2, props, winprops,
        #     GraphicsPipe.BFSizeTrackHost | GraphicsPipe.BFRefuseWindow,
        #     base.win.getGsg(), base.win)
        # self.water_buffer.setClearColor(base.win.getClearColor())
        # self.water_buffer.setSort(-3)
        # tex = Texture()
        # self.water_buffer.addRenderTexture(
        #     tex, GraphicsOutput.RTMBindOrCopy, GraphicsOutput.RTPColor)
        
        
        self.water_camera = base.makeCamera(self.water_buffer)
        self.water_camera.reparentTo(base.render)
        self.water_camera.node().setLens(base.camLens)

        # self.water_camera.node().getLens().setFov(90)
        self.water_camera.node().setCameraMask(BitMask32.bit(1))

        # # Create this texture and apply settings
        reflect_tex = self.water_buffer.getTexture()
        reflect_tex.setWrapU(Texture.WMClamp)
        reflect_tex.setWrapV(Texture.WMClamp)

        li = [
            [0.5, 0, 0, 0],
            [0, 0.383022, -0.321394, 0],
            [0, 0.321394, 0.383022, 0],
            [96.5717, 79.9214, 66.5843, 1]
        ]
        self.m = Mat4()
        for i, row in enumerate(li):
            for j, val in enumerate(row):
                self.m[i][j] = val
    
        # # Create plane for clipping and for reflection matrix
        self.clip_plane = Plane(Vec3(0, 0, 1), Point3(0, 0, -3)) # a bit off, but that's how it should be
        # self.clip_plane = Plane(Vec3(0, 0, 1), Point3(0, 0, -50)) # a bit off, but that's how it should be

        clip_plane_node = base.render.attachNewNode(PlaneNode("water", self.clip_plane))
        tmp_node = NodePath("StateInitializer")
        tmp_node.setClipPlane(clip_plane_node)
        tmp_node.setAttrib(CullFaceAttrib.makeReverse())
        # base.camNode.setInitialState(tmp_node.getState()) #<- だめ
        self.water_camera.node().setInitialState(tmp_node.getState())
        self.water_plane.setShaderInput('camera', self.water_camera)
        # self.water_plane.setShaderInput('camera', base.camera)
        self.water_plane.setShaderInput("reflection", reflect_tex)
        # self.scene.water_camera.setMat(self.scene.m * self.scene.clip_plane.getReflectionMat())
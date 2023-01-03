import sys

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletDebugNode, BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, ZUp

from panda3d.core import PandaNode, NodePath
from panda3d.core import Vec3, Point3
from panda3d.core import Filename
from panda3d.core import PNMImage

from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState


class Walking(ShowBase):

    def __init__(self):
        super().__init__()

        load_prc_file_data("", """
            textures-power-2 none
            gl-coordinate-system default
            window-title Panda3D ShaderTerrainMesh Demo
            filled-wireframe-apply-shader true
            stm-max-views 8
            stm-max-chunk-count 2048"""
        )
        self.disableMouse()

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))


        # ****************************************
        collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        self.world.setDebugNode(collide_debug.node())
        collide_debug.show()
        # ****************************************
        self.create_terrain()

        self.accept('escape', sys.exit)
        self.taskMgr.add(self.update, 'update')


    def create_terrain(self):
        img = PNMImage(Filename('mytest.png'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        np = NodePath(BulletRigidBodyNode('test'))
        np.node().addShape(shape)
        self.world.attachRigidBody(np.node())

        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)

        terrain_node = ShaderTerrainMesh()
        heightfield = self.loader.loadTexture('mytest.png')
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain_node.heightfield = heightfield
        terrain_node.target_triangle_width = 10.0
        terrain_node.generate()

        self.terrain = self.render.attachNewNode(terrain_node)
        self.terrain.setScale(256, 256, 10)

        offset = img.getXSize() / 2.0 - 0.5

        # self.terrain.setPos(-65, -65, -5)
        self.terrain.setPos(-offset, -offset, -10 / 2.0)
        terrain_shader = Shader.load(Shader.SL_GLSL, "terrain.vert.glsl", "terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", self.camera)
        grass_tex = self.loader.loadTexture('grass.png')
        grass_tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.setTexture(grass_tex)


    def update(self, task):
        dt = globalClock.getDt()


        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()


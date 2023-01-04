import sys

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock

from direct.showbase.InputStateGlobal import inputState

from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletDebugNode, BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage

from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState

from direct.actor.Actor import Actor



class Walker(NodePath):

    RUN = 'run'
    WALK = 'walk'

    def __init__(self):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
        self.reparentTo(base.render)
        self.setCollideMask(BitMask32.bit(1))
        self.setPos(0, 0, 0)
        self.setH(180)
        self.setScale(0.5)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.setTransform(TransformState.makePos(Vec3(0, 0, -3)))
        self.actor.setName('ralph')
        self.actor.reparentTo(self)

        inputState.watchWithModifiers('forward', 'arrow_up')
        inputState.watchWithModifiers('backward', 'arrow_down')
        inputState.watchWithModifiers('left', 'arrow_left')
        inputState.watchWithModifiers('right', 'arrow_right')

    def move(self, dt):
        if inputState.isSet('forward'):
            self.setY(self, -20 * dt)
        if inputState.isSet('backward'):
            self.setY(self, 10 * dt)
        if inputState.isSet('left'):
            self.setH(self.getH() + 100 * dt)
        if inputState.isSet('right'):
            self.setH(self.getH() - 100 * dt)

        anim = self.actor.getCurrentAnim()
        # print(anim)

        if inputState.isSet('forward'):
            if anim != self.RUN:
                self.actor.loop(self.RUN)
        elif inputState.isSet('backward'):
            if anim != self.WALK:
                self.actor.loop(self.WALK)
                self.actor.setPlayRate(-1.0, 'walk')  # -1 means to play an animation backwards.
        elif inputState.isSet('left') or inputState.isSet('right'):
            if anim != self.WALK:
                self.actor.loop(self.WALK)
                self.actor.setPlayRate(1.0, 'walk')
        else:
            if anim is not None:
                self.actor.stop()
                self.actor.pose('walk', 5)


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
        # self.camera.setPos(Point3(0, -30, 5))
        # self.camera.lookAt(0, 0, 0)

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))


        # ****************************************
        # collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        # self.world.setDebugNode(collide_debug.node())
        # collide_debug.show()
        # ****************************************
        self.create_terrain()

        self.walker = Walker()
        self.world.attachCharacter(self.walker.node())
        # print(self.walker.actor.listJoints())

        self.camera.reparentTo(self.walker)
        self.camLens.setFov(90)
        self.camera.setPosHpr(Point3(0, 20, 3), Vec3(180, 0, 0))

        self.accept('escape', sys.exit)
        self.taskMgr.add(self.update, 'update')


    def create_terrain(self):
        img = PNMImage(Filename('mytest.png'))
        shape = BulletHeightfieldShape(img, 10, ZUp)
        np = NodePath(BulletRigidBodyNode('test'))
        np.node().addShape(shape)
        np.setCollideMask(BitMask32.bit(1))
        self.world.attachRigidBody(np.node())

        # self.camLens.set_fov(90)
        # self.camLens.set_near_far(0.1, 50000)

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
        self.walker.move(dt)


        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()


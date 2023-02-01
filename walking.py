import math
import sys

import time

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock

from direct.showbase.InputStateGlobal import inputState

from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletDebugNode, BulletRigidBodyNode
from panda3d.bullet import BulletHeightfieldShape, BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
<<<<<<< HEAD
from panda3d.core import Vec3, Point3, BitMask32, Quat
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState
from direct.actor.Actor import Actor

from panda3d.core import CompassEffect

from scene import SquareBuilding


class PositionNode(NodePath):

    def __init__(self, pos):
        h, w = 6, 1.5  # h = 6
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'walker'))
        self.setCollideMask(BitMask32.bit(1))
        self.reparentTo(base.render)
        self.setPos(-10, -3, -3)
        self.setScale(0.5)


class DirectionNode(NodePath):

    def __init__(self, parent):
        super().__init__(PandaNode('directionRoot'))
        self.reparentTo(parent)
        # self.setH(180)


class Ralph(NodePath):
    RUN = 'run'
    WALK = 'walk'

    def __init__(self):
        super().__init__(PandaNode('ralph'))

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.setTransform(TransformState.makePos(Vec3(0, 0, -2.5)))  # -3
        self.actor.setName('ralph')
        self.actor.reparentTo(self)
        self.setH(180)

    def play_anim(self, command, rate):
        if self.actor.getCurrentAnim() != command:
            self.actor.loop(command)
            self.actor.setPlayRate(rate, command)

    def stop_anim(self):
        if self.actor.getCurrentAnim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)
=======
from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage

from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState

from direct.actor.Actor import Actor

>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced


class Walker(NodePath):

<<<<<<< HEAD
=======
    RUN = 'run'
    WALK = 'walk'

>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced
    def __init__(self):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
        self.reparentTo(base.render)
        self.setCollideMask(BitMask32.bit(1))
<<<<<<< HEAD
        self.setPos(-10, -3, -3)
        self.setScale(0.5)
        self.walker = Ralph()
        self.walker.reparentTo(self)

    def move(self, dist):
        orientation = self.walker.getQuat(base.render).getForward()
        # pos = base.render.getRelativePoint(self, Point3(0, 10, 0))
        self.setPos(self.getPos() + orientation * dist)

    def turn(self, angle):
        self.walker.setH(self.walker.getH() + angle)

    def run(self, rate=1):
        self.walker.play_anim(self.walker.RUN, rate)

    def walk(self, rate=1):
        self.walker.play_anim(self.walker.WALK, rate)

    def stop(self):
        self.walker.stop_anim()
=======
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
>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced


class Walking(ShowBase):

    def __init__(self):
        super().__init__()

        load_prc_file_data("", """
            textures-power-2 none
            gl-coordinate-system default
            window-title Panda3D ShaderTerrainMesh Demo
            filled-wireframe-apply-shader true
            stm-max-views 8
<<<<<<< HEAD
            stm-max-chunk-count 2048""")
=======
            stm-max-chunk-count 2048"""
        )
>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced
        self.disableMouse()
        # self.camera.setPos(Point3(0, -30, 5))
        # self.camera.lookAt(0, 0, 0)

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

<<<<<<< HEAD
=======

>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced
        # ****************************************
        # collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        # self.world.setDebugNode(collide_debug.node())
        # collide_debug.show()
        # ****************************************
        self.create_terrain()
<<<<<<< HEAD
        self.building = SquareBuilding(self.world)

        self.walker = Walker()

        self.world.attachCharacter(self.walker.node())
        # print(self.walker.actor.listJoints())

        self.floater = NodePath(PandaNode('floater'))
        self.floater.reparentTo(self.walker)
        self.floater.setZ(2.0)
        
        self.camera_np = NodePath(PandaNode('camera_nd'))
        self.camera_np.reparentTo(self.walker)
        self.camera.reparentTo(self.camera_np)
        # self.camera.reparentTo(self.walker)

        self.camera.setPos(Point3(0, -10, 0))
        # self.camera_np.setH(-90)
        # self.camera.lookAt(self.floater)
        
        
        
        self.now_walker_pos = self.walker.getPos()
        
        self.is_rotating = False

        self.camLens.setFov(90)

        inputState.watchWithModifiers('forward', 'arrow_up')
        inputState.watchWithModifiers('backward', 'arrow_down')
        inputState.watchWithModifiers('left', 'arrow_left')
        inputState.watchWithModifiers('right', 'arrow_right')

        self.accept('escape', sys.exit)
        self.accept('p', self.print_info)
=======

        self.walker = Walker()
        self.world.attachCharacter(self.walker.node())
        # print(self.walker.actor.listJoints())

        self.camera.reparentTo(self.walker)
        self.camLens.setFov(90)
        self.camera.setPosHpr(Point3(0, 20, 3), Vec3(180, 0, 0))

        self.accept('escape', sys.exit)
>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced
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

<<<<<<< HEAD
    def control_walker(self, dt):
        if inputState.isSet('forward'):
            self.walker.move(-10 * dt)
        if inputState.isSet('backward'):
            self.walker.move(10 * dt)
        if inputState.isSet('left'):
            self.walker.turn(100 * dt)
        if inputState.isSet('right'):
            self.walker.turn(-100 * dt)

        if inputState.isSet('forward'):
            self.walker.run()
        elif inputState.isSet('backward'):
            self.walker.walk(-1)  # -1 means to play an animation backwards.
        elif inputState.isSet('left') or inputState.isSet('right'):
            self.walker.walk()
        else:
            self.walker.stop()

    def print_info(self):
        print('camera angle', self.camera_np.getH())
        print('walker angle', self.walker.walker.getH())

        # walker_pos = self.walker.getPos()
        # camera_pos = self.camera_np.getPos() + walker_pos

        # print('walker_pos', self.walker.getPos())
        # print('camera_np_pos', self.camera_np.getPos())
        # print('camera_pos', self.camera.getPos())

        # print('camera_walker_pos', self.camera.getPos(self.walker))
        # print('camera_cameranp_pos', self.camera.getPos(self.camera_np))

    def get_rotation_angle(self, camera_pos, walker_pos, turn):
        axis = self.walker.getQuat().getUp()
        q = Quat()

        for i in range(36):
            angle = turn * 10 * (i + 1) + self.camera_np.getH()
            q.setFromAxisAngle(angle, axis)
            vec = q.xform(camera_pos - walker_pos)
            rotated_camera_pos = walker_pos + vec
            result = self.world.rayTestClosest(rotated_camera_pos, walker_pos)
            if node := result.getNode():
                if node.getName() == 'character':
                    return angle
        return None

    def rotate_camera(self, camera_pos, walker_pos):
        result = self.world.rayTestClosest(camera_pos, walker_pos)

        if node := result.getNode():
            # if node.getName() == 'block':
            if node.getName() != 'character':
                v1 = self.now_walker_pos - camera_pos
                v2 = result.getHitPos() - camera_pos
                cross = v1.x * v2.y - v2.x * v1.y
                # -1 means walker turns right, and 1 means walker turns left.
                turn = -1 if cross < 0 else 1

                if angle := self.get_rotation_angle(camera_pos, walker_pos, turn):
                    self.camera_np.setH(angle)
                    self.camera.lookAt(self.floater)

    def update(self, task):
        dt = globalClock.getDt()
        self.control_walker(dt)

        walker_pos = self.walker.getPos()
        camera_pos = self.camera.getPos(self.walker) + walker_pos
        self.rotate_camera(camera_pos, walker_pos)
        
        # if not self.is_rotating:
        #     result = self.world.rayTestClosest(camera_pos, walker_pos)

        #     if node := result.getNode():
        #         if node.getName() == 'block':
        #             v1 = self.now_walker_pos - camera_pos
        #             v2 = result.getHitPos() - camera_pos
        #             cross = v1.x * v2.y - v2.x * v1.y
        #             # -1 means walker turns right, and 1 means walker turns left.
        #             self.turn = -1 if cross < 0 else 1
        #             angle = self.get_rotation_angle(camera_pos, walker_pos, self.turn)
        #             self.camera_np.setH(angle)
        #             self.rotation = 90 - abs(angle)
        #             self.is_rotating = True
        # else:
        #     if self.rotation > 0:
        #         angle = 90 - self.rotation
        #         (angle + 10) * self.turn
        #         self.camera_np.setH((angle + 10) * self.turn)
        #         self.camera.lookAt(self.floater)
        #         self.rotation -= 10
        #     else:
        #         self.is_rotating = False

        # print(self.building.floor.getPos())
        if walker_pos != self.now_walker_pos:
            self.now_walker_pos = walker_pos
=======

    def update(self, task):
        dt = globalClock.getDt()
        self.walker.move(dt)

>>>>>>> 506b24d768aa60f44d57e133433c0ac7256a8ced

        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()


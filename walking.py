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
from panda3d.core import Vec3, Point3, BitMask32, Quat
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState
from direct.actor.Actor import Actor

from panda3d.core import CompassEffect

from scene import StoneHouse


class Sphere(NodePath):

    def __init__(self, color):
        super().__init__(PandaNode('spehre'))
        self.reparentTo(base.render)
        sphere = base.loader.loadModel('models/sphere/sphere')
        sphere.reparentTo(self)
        self.setScale(0.05, 0.05, 0.05)
        self.setColor(color)


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

        self.right_eye = self.actor.exposeJoint(None, 'modelRoot', 'RightEyeLid')
        self.left_eye = self.actor.exposeJoint(None, 'modelRoot', 'LeftEyeLid')
        # joint = self.actor.controlJoint(None, 'modelRoot', 'RightEyeLid')
        # joint.setPos(-0.3, -0.3, -0.3)

        # the point at which the right eye looks
        self.front_right = NodePath('frontRight')
        self.front_right.reparentTo(self)
        self.front_right.setPos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparentTo(self)
        self.front_left.setPos(0.3, -2, -2.7)

        # **debug***************************************
        sphere1 = Sphere((1, 0, 0, 1))  # Red
        sphere1.reparentTo(self.front_right)
        sphere2 = Sphere((0, 0, 1, 1))  # Blue
        sphere2.reparentTo(self.front_left)
        # **********************************************

    def play_anim(self, command, rate):
        if self.actor.getCurrentAnim() != command:
            self.actor.loop(command)
            self.actor.setPlayRate(rate, command)

    def stop_anim(self):
        if self.actor.getCurrentAnim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)


class Walker(NodePath):

    def __init__(self, world):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
        self.world = world
        self.reparentTo(base.render)
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        self.setPos(-10, -3, -3)
        # self.setPos(10, 10, 8)
        self.setScale(0.5)
        self.walker = Ralph()
        self.walker.reparentTo(self)

        self.cam_navigator = NodePath('camNavigator')
        self.cam_navigator.reparentTo(self.walker)
        self.cam_navigator.setPos(Point3(0, 10, 0))

    def navigate(self):
        """Returns a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.getRelativePoint(self.walker, Vec3(0, 10, 0))

    def ray_cast(self, from_pos, to_pos, mask=None):
        if mask is None:
            result = self.world.rayTestAll(from_pos, to_pos)
        else:
            result = self.world.rayTestAll(from_pos, to_pos, BitMask32.bit(mask))

        for hit in result.getHits():
            if hit.getNode() != self.node():
                return hit
        return None

    def go_forward(self, dist):
        walker_pos = self.getPos()
        orientation = self.walker.getQuat(base.render).getForward()
        pos = walker_pos + orientation * dist

        below = base.render.getRelativePoint(self, Vec3(0, 0, -3))
        right_eye = self.walker.right_eye.getPos() + walker_pos
        front_right = self.walker.front_right.getPos(self) + walker_pos
        left_eye = self.walker.left_eye.getPos() + walker_pos
        front_left = self.walker.front_left.getPos(self) + walker_pos

        if below_hit := self.ray_cast(walker_pos, below):
            if (front_right_hit := self.ray_cast(right_eye, front_right, 2)) and \
                    (front_lelt_hit := self.ray_cast(left_eye, front_left, 2)):
                if front_right_hit.getNode() == front_lelt_hit.getNode():
                    below_height = below_hit.getHitPos().z
                    step_height = front_right_hit.getHitPos().z

                    if 0.5 < (diff := step_height - below_height) < 1.2:
                        pos.z += diff

        self.setPos(pos)

    def go_back(self, dist):
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


class Walking(ShowBase):

    def __init__(self):
        super().__init__()

        load_prc_file_data("", """
            textures-power-2 none
            gl-coordinate-system default
            window-title Panda3D ShaderTerrainMesh Demo
            filled-wireframe-apply-shader true
            stm-max-views 8
            stm-max-chunk-count 2048""")
        self.disableMouse()
        # self.camera.setPos(Point3(0, -30, 5))
        # self.camera.lookAt(0, 0, 0)

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        # ****************************************
        collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        self.world.setDebugNode(collide_debug.node())
        collide_debug.show()
        # ****************************************
        self.create_terrain()
        self.building = StoneHouse(self.world)

        self.walker = Walker(self.world)
        self.world.attachCharacter(self.walker.node())
        # print(self.walker.walker.actor.listJoints())

        self.floater = NodePath('floater')
        self.floater.reparentTo(self.walker)
        self.floater.setZ(2.0)
        
        self.camera_np = NodePath('cameraNp')
        self.camera_np.reparentTo(self.walker)
        self.camera.reparentTo(self.camera_np)
        # self.camera.reparentTo(self.walker)
        self.camera_np.setPos(self.walker.navigate())
        self.camera.lookAt(self.floater)
        self.camLens.setFov(90)

        self.in_room = False

        inputState.watchWithModifiers('forward', 'arrow_up')
        inputState.watchWithModifiers('backward', 'arrow_down')
        inputState.watchWithModifiers('left', 'arrow_left')
        inputState.watchWithModifiers('right', 'arrow_right')

        self.accept('escape', sys.exit)
        self.accept('p', self.print_info)
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

    def control_walker(self, dt):
        if inputState.isSet('forward'):
            self.walker.go_forward(-10 * dt)
        if inputState.isSet('backward'):
            self.walker.go_back(10 * dt)
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
        print('walker_pos', self.walker.getPos())
        print('camera_navigator', self.walker.cam_navigator.getPos(), self.walker.cam_navigator.getPos(self.walker), self.walker.navigate())
        print('camera_pos', self.camera.getPos(), self.camera.getPos(self.walker))


        # print(self.walker.walker.right_eye_lookat.getPos(self.walker) + self.walker.getPos())
        print('right_eye_lookat', self.walker.getRelativeVector(self.walker.walker.front_right, Vec3(-0.3, -2, -2.7))  + self.walker.getPos()) 
        print('left_eye_lookat', self.walker.getRelativeVector(self.walker.walker.front_left, Vec3(0.3, -2, -2.7))  + self.walker.getPos())
                
        print('直下')
        # ver_ground = self.walker.getRelativeVector(self.walker.walker, Vec3(0, 0,-2.7)) + self.walker.getPos() 
        ver_ground = self.render.getRelativePoint(self.walker, Vec3(0, 0, -3))
        print('-3だけ下', ver_ground)
        result = self.world.rayTestAll(self.walker.getPos(), ver_ground)
        for hit in result.getHits():
            nd = hit.getNode()
            print('name', nd.getName(), 'hit_pos', hit.getHitPos())
        
        print('右目から見た前方')
        ground = self.walker.walker.front_right.getPos(self.walker) + self.walker.getPos()
        print('ground', ground)
        eye = self.walker.walker.right_eye.getPos() + self.walker.getPos()
        print('eye', eye)
        # ground = self.walker.getRelativeVector(self.walker.navigator, Vec3(-0.3, -2, -2.7)) + self.walker.getPos()
        # result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        
        for hit in result.getHits():
            nd = hit.getNode()
            print(nd.getName())

        print('左目から見た前方')
        ground = self.walker.walker.front_left.getPos(self.walker) + self.walker.getPos()
        print('ground', ground)
        eye = self.walker.walker.left_eye.getPos() + self.walker.getPos()
        print('eye', eye)
        # ground = self.walker.getRelativeVector(self.walker.navigator, Vec3(-0.3, -2, -2.7)) + self.walker.getPos()
        # result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        
        for hit in result.getHits():
            nd = hit.getNode()
            print('name', nd.getName(), 'hit_pos', hit.getHitPos())
        # eye = self.walker.walker.left_eye.getPos() + self.walker.getPos()
        # ground = self.walker.getRelativeVector(self.walker.navigator_left, Vec3(0.3, -2, -2.7)) + self.walker.getPos()
        # result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        # for hit in result.getHits():
        #     nd = hit.getNode()
        #     print(nd.getName())


        print('----------------------')


    def control_camera(self):
        walker_pos = self.walker.getPos()
        camera_pos = self.camera.getPos(self.walker) + walker_pos
        result = self.world.rayTestClosest(camera_pos, walker_pos)

        if result.hasHit():
            if result.getNode() != self.walker.node():
                self.camera_np.setPos(self.walker.navigate())
                self.camera.lookAt(self.floater)

                # if not self.in_room:
                #     print('comein')
                #     self.camera.detachNode()
                #     self.camera.reparentTo(self.render)
                #     self.camera.setPos(Point3(15, 10, 2))
                #     # self.camera.lookAt(self.floater)
                #     self.in_room = True
                # else:
                #     self.camera.detachNode()
                #     self.camera.reparentTo(self.camera_np)
                #     # self.camLens.setFov(90)
                #     self.camera_np.setPos(Vec3(0, 10, 0))
                #     self.in_room = False


    def update(self, task):
        dt = globalClock.getDt()
        self.control_walker(dt)
        self.control_camera()

        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()


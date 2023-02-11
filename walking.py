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
        # self.setPos(-5, 10, 8)
        self.setScale(0.5)
        self.walker = Ralph()
        self.walker.reparentTo(self)

        self.jump = False

        # self.navigator = NodePath('navigator')
        # self.navigator.reparentTo(self.walker)
        # self.navigator.setY(-2)
        # self.navigator.setX(-0.3)
        # self.navigator.setZ(-2.7)

        # self.navigator_left = NodePath('navigator_left')
        # self.navigator_left.reparentTo(self.walker)
        # self.navigator_left.setY(-2)
        # self.navigator_left.setX(0.3)
        # self.navigator_left.setZ(-2.7)

    def look_below(self):
        to_pos = base.render.getRelativePoint(self, Vec3(0, 0, -3))
        result = self.world.rayTestAll(self.getPos(), to_pos)
        for hit in result.getHits():
            if (node := hit.getNode()).getName() != 'character':
                return node

    def look_forward(self, eye, front, below_node):
        from_pos = eye.getPos() + self.getPos()
        to_pos = front.getPos(self) + self.getPos()

        result = self.world.rayTestAll(from_pos, to_pos, BitMask32.bit(2))
        for hit in result.getHits():
            if (node := hit.getNode()) not in (self.node(), below_node):

                return node

    def go_forward(self, dist):
        below_node = self.look_below()
        # import pdb; pdb.set_trace()
        front_right = self.look_forward(self.walker.right_eye, self.walker.front_right, below_node)
        front_left = self.look_forward(self.walker.left_eye, self.walker.front_left, below_node)

        print(below_node, front_right, front_left)

        # front_right = self.walker.right_eye_lookat.getPos(self) + self.getPos()
        # right_eye = self.walker.right_eye.getPos() + self.getPos()
        # front_left = self.walker.left_eye_lookat.getPos(self) + self.getPos()
        # left_eye = self.walker.left_eye.getPos() + self.getPos()

        if front_right and front_left:
            if front_right == front_left and front_left != below_node:
                self.jump = True
                # self.node().setMaxJumpHeight(0.2)  # 5.0
                # self.node().setJumpSpeed(5.0)      # 8.0
                # self.node().doJump()

        orientation = self.walker.getQuat(base.render).getForward()
        # pos = base.render.getRelativePoint(self, Point3(0, 10, 0))
        self.setPos(self.getPos() + orientation * dist)

        if self.jump:
            self.setZ(self.getZ() + 0.3)
            self.jump = False


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
        # collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        # self.world.setDebugNode(collide_debug.node())
        # collide_debug.show()
        # ****************************************
        self.create_terrain()
        self.building = StoneHouse(self.world)

        self.walker = Walker(self.world)
        self.world.attachCharacter(self.walker.node())
        # print(self.walker.walker.actor.listJoints())

        self.floater = NodePath('floater')
        # self.floater = NodePath(PandaNode('floater'))
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
            # if self.is_steps():
            #     if self.walker.node().isOnGround():
            #         self.walker.node().setMaxJumpHeight(1.0)  # 5.0
            #         self.walker.node().setJumpSpeed(5.0)      # 8.0
            #         self.walker.node().doJump()
            self.walker.go_forward(-10 * dt)
        if inputState.isSet('backward'):
            self.walker.go_back(10 * dt)
            # self.walker.move(10 * dt)
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

    def is_steps(self):
        eye = self.walker.walker.right_eye.getPos() + self.walker.getPos()
        ground = self.walker.getRelativeVector(self.walker.walker, Vec3(-0.3, -2, -2.7)) + self.walker.getPos()

        result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        for hit in result.getHits():
            nd = hit.getNode()
            print(nd.getName())
            if nd.getName().startswith('step'):
                return True
        return False

    def print_info(self):
        print('walker_pos', self.walker.getPos())

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
            print(nd.getName())
        
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
            print(nd.getName())
        # eye = self.walker.walker.left_eye.getPos() + self.walker.getPos()
        # ground = self.walker.getRelativeVector(self.walker.navigator_left, Vec3(0.3, -2, -2.7)) + self.walker.getPos()
        # result = self.world.rayTestAll(eye, ground, BitMask32.bit(2))
        # for hit in result.getHits():
        #     nd = hit.getNode()
        #     print(nd.getName())



        print('----------------------')
 
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

        if walker_pos != self.now_walker_pos:
            self.now_walker_pos = walker_pos

        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()


import sys

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

from scene import StoneHouse


class Sphere(NodePath):

    def __init__(self, color):
        super().__init__(PandaNode('spehre'))
        self.reparentTo(base.render)
        sphere = base.loader.loadModel('models/sphere/sphere')
        sphere.reparentTo(self)
        self.setScale(0.05, 0.05, 0.05)
        self.setColor(color)


class Walker(NodePath):
    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
        self.world = world
        self.reparentTo(base.render)
        self.setCollideMask(BitMask32.allOn())
        # self.setPos(-10, -3, -3)  # (10, 10, 8)
        self.setPos(Point3(16, -20, -3))
        self.setScale(0.5)

        self.direction_node = NodePath(PandaNode('direction'))
        self.direction_node.reparentTo(self)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.setTransform(TransformState.makePos(Vec3(0, 0, -2.5)))  # -3
        self.actor.setName('ralph')
        self.actor.reparentTo(self.direction_node)
        self.direction_node.setH(180)

        self.right_eye = self.actor.exposeJoint(None, 'modelRoot', 'RightEyeLid')
        self.left_eye = self.actor.exposeJoint(None, 'modelRoot', 'LeftEyeLid')
        # joint = self.actor.controlJoint(None, 'modelRoot', 'RightEyeLid')
        # joint.setPos(-0.3, -0.3, -0.3)

        # the point at which the right eye looks
        self.front_right = NodePath('frontRight')
        self.front_right.reparentTo(self.direction_node)
        self.front_right.setPos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparentTo(self.direction_node)
        self.front_left.setPos(0.3, -2, -2.7)

        # **debug***************************************
        sphere1 = Sphere((1, 0, 0, 1))  # Red
        sphere1.reparentTo(self.front_right)
        sphere2 = Sphere((0, 0, 1, 1))  # Blue
        sphere2.reparentTo(self.front_left)
        # **********************************************

    def navigate(self):
        """Returns a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.getRelativePoint(self.direction_node, Vec3(0, 10, 0))

    def ray_cast(self, from_pos, to_pos, mask=None):
        if mask is None:
            result = self.world.rayTestAll(from_pos, to_pos)
        else:
            result = self.world.rayTestAll(from_pos, to_pos, mask)

        for hit in result.getHits():
            if hit.getNode() != self.node():
                return hit
        return None

    def current_location(self):
        below = base.render.getRelativePoint(self, Vec3(0, 0, -3))
        return self.ray_cast(self.getPos(), below)

    def watch_steps(self):
        right_eye = self.right_eye.getPos() + self.getPos()
        front_right = self.front_right.getPos(self) + self.getPos()

        left_eye = self.left_eye.getPos() + self.getPos()
        front_left = self.front_left.getPos(self) + self.getPos()

        if (right_hit := self.ray_cast(right_eye, front_right, BitMask32.bit(2))) and \
                (lelt_hit := self.ray_cast(left_eye, front_left, BitMask32.bit(2))):
            if right_hit.getNode() == lelt_hit.getNode():
                return right_hit
        return None

    def go_forward(self, dist):
        orientation = self.direction_node.getQuat(base.render).getForward()
        pos = self.getPos() + orientation * dist

        if below_hit := self.current_location():
            if steps_hit := self.watch_steps():
                below_height = below_hit.getHitPos().z
                step_height = steps_hit.getHitPos().z

                if 0.5 < (diff := step_height - below_height) < 1.2:
                    pos.z += diff
        self.setPos(pos)

    def go_back(self, dist):
        # pos = base.render.getRelativePoint(self, Point3(0, 10, 0))
        orientation = self.direction_node.getQuat(base.render).getForward()
        self.setPos(self.getPos() + orientation * dist)

    def turn(self, angle):
        self.direction_node.setH(self.direction_node.getH() + angle)

    def play_anim(self, command, rate=1):
        if self.actor.getCurrentAnim() != command:
            self.actor.loop(command)
            self.actor.setPlayRate(rate, command)

    def stop_anim(self):
        if self.actor.getCurrentAnim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)


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
        self.floater.reparentTo(self.walker)
        self.floater.setZ(2.0)

        # using camera_np***************
        # self.camera_np = NodePath('cameraNp')
        # self.camera_np.reparentTo(self.walker)
        # self.camera.reparentTo(self.camera_np)
        # self.camera_np.setPos(self.walker.navigate())
        # self.camera.lookAt(self.floater)
        # *******************************

        self.camera.reparentTo(self.walker)
        self.camera.setPos(self.walker.navigate())
        self.camera.lookAt(self.floater)
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
        # contol walker movement
        if inputState.isSet('forward'):
            self.walker.go_forward(-10 * dt)
        if inputState.isSet('backward'):
            self.walker.go_back(10 * dt)
        if inputState.isSet('left'):
            self.walker.turn(100 * dt)
        if inputState.isSet('right'):
            self.walker.turn(-100 * dt)

        # play animation
        if inputState.isSet('forward'):
            self.walker.play_anim(self.walker.RUN)
        elif inputState.isSet('backward'):
            self.walker.play_anim(self.walker.WALK, -1)
        elif inputState.isSet('left') or inputState.isSet('right'):
            self.walker.play_anim(self.walker.WALK)
        else:
            self.walker.stop_anim()

    def print_info(self):
        print(self.walker.getPos())

    def control_camera_outdoors(self):
        # If the camera's view is blocked by an object like walls, the camera is repositioned.
        walker_pos = self.walker.getPos()
        camera_pos = self.camera.getPos(self.walker) + walker_pos
        result = self.world.rayTestClosest(camera_pos, walker_pos)

        if result.hasHit():
            if result.getNode() != self.walker.node():
                if not result.getNode().getName().startswith('door'):
                    self.camera.setPos(self.walker.navigate())
                    # self.camera_np.setPos(self.walker.navigate())
                    self.camera.lookAt(self.floater)

        # if the character goes into a room, the camera is reparented to a room-camera np.
        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if (name := location.getNode().getName()).startswith('room'):
                room_camera = self.render.find(f'**/{name}_camera')

                self.camera.detachNode()
                self.camera.reparentTo(room_camera)
                self.camera.setPos(0, 0, 0)
                self.camera.lookAt(self.floater)

                # *****using self.camera_np*************
                # self.camera.detachNode()
                # self.camera.reparentTo(room_camera)
                # self.camera.lookAt(self.floater)
                # ***************************************

    def control_camera_indoors(self):
        self.camera.lookAt(self.floater)

        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if not location.getNode().getName().startswith('room'):
                self.camera.detachNode()
                self.camera.reparentTo(self.walker)
                self.camera.setPos(0, -10, 0)
                self.camera.lookAt(self.floater)

                # *****using self.camera_np*************
                # self.camera.detachNode()
                # self.camera.reparentTo(self.camera_np)
                # # self.camera_np.setPos(self.walker.navigate(True))  # <- なくてもOK
                # self.camera.lookAt(self.floater)
                # ***************************************

    def update(self, task):
        dt = globalClock.getDt()
        self.control_walker(dt)

        if self.walker.isAncestorOf(self.camera):
            self.control_camera_outdoors()
        else:
            self.control_camera_indoors()

        self.world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()

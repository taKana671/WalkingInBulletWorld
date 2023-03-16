import sys

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.InputStateGlobal import inputState
from direct.actor.Actor import Actor
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletCapsuleShape, ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, Point3, BitMask32, Quat
from panda3d.core import AmbientLight, DirectionalLight

from scene import Scene
from utils import Cube


class DebugCube(NodePath):

    def __init__(self, name, cube, color):
        super().__init__(PandaNode(name))
        self.cube = cube.copyTo(self)
        self.cube.reparentTo(self)
        self.setScale(0.15, 0.15, 0.15)
        self.setHpr(45, 45, 45)
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
        self.setPos(Point3(38, -47, 3))
        # self.setPos(Point3(-42, -71, 3))
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

        # the point at which the right eye looks
        self.front_right = NodePath('frontRight')
        self.front_right.reparentTo(self.direction_node)
        self.front_right.setPos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparentTo(self.direction_node)
        self.front_left.setPos(0.3, -2, -2.7)

        self.debug_right = None
        self.debug_left = None

    def toggle_debug(self):
        if not self.debug_right:
            cube = Cube.make()
            self.debug_right = DebugCube('right', cube, (1, 0, 0, 1))  # Red
            self.debug_left = DebugCube('left', cube, (0, 0, 1, 1))  # Blue

        if self.debug_right.hasParent():
            self.debug_right.detach_node()
            self.debug_left.detach_node()
        else:
            self.debug_right.reparentTo(self.front_right)
            self.debug_left.reparentTo(self.front_left)

    def navigate(self):
        """Returns a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.getRelativePoint(self.direction_node, Vec3(0, 10, 2))

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
        self.disableMouse()
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        self.debug_np = self.render.attachNewNode(BulletDebugNode('debug'))
        self.world.setDebugNode(self.debug_np.node())

        self.scene = Scene(self.world)

        self.walker = Walker(self.world)
        self.world.attachCharacter(self.walker.node())

        self.floater = NodePath('floater')
        self.floater.reparentTo(self.walker)
        self.floater.setZ(2.0)

        self.camera.reparentTo(self.walker)
        self.camera.setPos(self.walker.navigate())
        self.camera.lookAt(self.floater)
        # self.camera.setPos(Point3(16, -20, 100))
        # self.camera.lookAt(self.floater)

        self.camLens.setFov(90)
        # self.setup_lights()
        self.mask = BitMask32.bit(2) | BitMask32.bit(1)

        inputState.watchWithModifiers('forward', 'arrow_up')
        inputState.watchWithModifiers('backward', 'arrow_down')
        inputState.watchWithModifiers('left', 'arrow_left')
        inputState.watchWithModifiers('right', 'arrow_right')

        self.accept('escape', sys.exit)
        self.accept('p', self.print_info)
        self.accept('d', self.toggle_debug)
        self.accept('f', self.walker.toggle_debug)
        self.taskMgr.add(self.update, 'update')

    def toggle_debug(self):
        if self.debug_np.isHidden():
            self.debug_np.show()
        else:
            self.debug_np.hide()

    def setup_lights(self):
        ambient_light = self.render.attachNewNode(AmbientLight('ambientLignt'))
        ambient_light.node().setColor((0.6, 0.6, 0.6, 1))
        self.render.setLight(ambient_light)

        directional_light = self.render.attachNewNode(DirectionalLight('directionalLight'))
        directional_light.node().getLens().setFilmSize(200, 200)
        directional_light.node().getLens().setNearFar(1, 100)
        directional_light.node().setColor((1, 1, 1, 1))
        directional_light.setPosHpr(Point3(-127, -127, 30), Vec3(-30, -45, 0))
        # directional_light.setHpr((-30, -45, 0))
        # directional_light.node().setShadowCaster(True)

        # self.render.setShaderAuto()
        self.render.setLight(directional_light)
        # self.render.setDepthOffset(-2)

        state = directional_light.node().getInitialState()
        temp = NodePath(PandaNode('temp'))
        temp.setState(state)
        temp.setDepthOffset(-2)
        directional_light.node().setInitialState(temp.getState())
        # self.render.setDepthOffset(-2)

        directional_light.node().setShadowCaster(True)
        self.render.setShaderAuto()

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
        print('camera', self.camera.getPos(), self.camera.getPos(self.walker))
        print('walker', self.walker.getPos(), 'camera', self.camera.getPos(self.walker) + self.walker.getPos())
        print('navigator', self.walker.getRelativePoint(self.walker.direction_node, Vec3(0, 10, 2)))
        print('navigator + walker_pos', self.walker.getPos() + self.walker.getRelativePoint(self.walker.direction_node, Vec3(0, 10, 2)))

    def ray_cast(self, from_pos, to_pos):
        result = self.world.rayTestClosest(from_pos, to_pos, self.mask)

        if result.hasHit():
            return result.getNode()

        return None

    def find_camera_pos(self, walker_pos, next_pos):
        q = Quat()
        point = Point3(0, 0, 0)
        start = self.camera.getPos()
        angle = r = None

        for i in range(36):
            camera_pos = next_pos + walker_pos
            if self.ray_cast(camera_pos, walker_pos) == self.walker.node():
                return next_pos

            times = i // 2 + 1
            angle = 10 * times if i % 2 == 0 else -10 * times
            q.setFromAxisAngle(angle, Vec3.up())
            r = q.xform(start - point)
            next_pos = point + r

        return None

    def control_camera_outdoors(self):
        """Repositions the camera if the camera's view is blocked by objects like walls, and
           reparents the camera to the room_camera if the character goes into a room.
        """
        # reposition
        walker_pos = self.walker.getPos()
        camera_pos = self.camera.getPos() + walker_pos

        if self.ray_cast(camera_pos, walker_pos) != self.walker.node():
            if next_pos := self.find_camera_pos(walker_pos, self.walker.navigate()):
                self.camera.setPos(next_pos)
                self.camera.lookAt(self.floater)

        # reparent camera
        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if (name := location.getNode().getName()).startswith('room'):
                room_camera = self.render.find(f'**/{name}_camera')
                self.camera.detachNode()
                self.camera.reparentTo(room_camera)
                self.camera.setPos(0, 0, 0)
                self.camera.lookAt(self.floater)

    def control_camera_indoors(self):
        self.camera.lookAt(self.floater)

        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if not location.getNode().getName().startswith('room'):
                self.camera.detachNode()
                self.camera.reparentTo(self.walker)
                self.camera.setPos(0, -10, 2)
                self.camera.lookAt(self.floater)

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

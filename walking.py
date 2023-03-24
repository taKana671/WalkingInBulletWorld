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
        self.cube = cube.copy_to(self)
        self.cube.reparent_to(self)
        self.set_scale(0.15, 0.15, 0.15)
        self.set_hpr(45, 45, 45)
        self.set_color(color)


class Walker(NodePath):
    RUN = 'run'
    WALK = 'walk'

    def __init__(self, world):
        h, w = 6, 1.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)
        super().__init__(BulletCharacterControllerNode(shape, 0.4, 'character'))
        self.world = world
        self.set_collide_mask(BitMask32.allOn())
        self.set_pos(Point3(38, -47, 3))
        # self.set_pos(Point3(-42, -71, 3))
        self.set_scale(0.5)
        self.reparent_to(base.render)
        self.world.attach_character(self.node())

        self.direction_node = NodePath(PandaNode('direction'))
        self.direction_node.reparent_to(self)

        self.actor = Actor(
            'models/ralph/ralph.egg',
            {self.RUN: 'models/ralph/ralph-run.egg',
             self.WALK: 'models/ralph/ralph-walk.egg'}
        )
        self.actor.set_transform(TransformState.make_pos(Vec3(0, 0, -2.5)))  # -3
        self.actor.set_name('ralph')
        self.actor.reparent_to(self.direction_node)
        self.direction_node.set_h(180)

        self.right_eye = self.actor.expose_joint(None, 'modelRoot', 'RightEyeLid')
        self.left_eye = self.actor.expose_joint(None, 'modelRoot', 'LeftEyeLid')

        # the point at which the right eye looks
        self.front_right = NodePath('frontRight')
        self.front_right.reparent_to(self.direction_node)
        self.front_right.set_pos(-0.3, -2, -2.7)

        # the point at which the left eye looks
        self.front_left = NodePath('frontLeft')
        self.front_left.reparent_to(self.direction_node)
        self.front_left.set_pos(0.3, -2, -2.7)

        self.debug_right = None
        self.debug_left = None

    def toggle_debug(self):
        if not self.debug_right:
            cube = Cube.make()
            self.debug_right = DebugCube('right', cube, (1, 0, 0, 1))  # Red
            self.debug_left = DebugCube('left', cube, (0, 0, 1, 1))  # Blue

        if self.debug_right.has_parent():
            self.debug_right.detach_node()
            self.debug_left.detach_node()
        else:
            self.debug_right.reparent_to(self.front_right)
            self.debug_left.reparent_to(self.front_left)

    def navigate(self):
        """Returns a relative point to enable camera to follow a character
           when camera's view is blocked by an object like walls.
        """
        return self.get_relative_point(self.direction_node, Vec3(0, 10, 2))

    def get_rayhit(self, result):
        for hit in result.get_hits():
            if hit.get_node() != self.node():
                return hit
        return None

    def current_location(self):
        below = base.render.get_relative_point(self, Vec3(0, 0, -3))
        result = self.world.ray_test_all(self.get_pos(), below)
        return self.get_rayhit(result)

    def watch_steps(self):
        right_eye = self.right_eye.get_pos() + self.get_pos()
        front_right = self.front_right.get_pos(self) + self.get_pos()
        right_result = self.world.ray_test_all(right_eye, front_right, BitMask32.bit(2))

        left_eye = self.left_eye.get_pos() + self.get_pos()
        front_left = self.front_left.get_pos(self) + self.get_pos()
        left_result = self.world.ray_test_all(left_eye, front_left, BitMask32.bit(2))

        if (right_hit := self.get_rayhit(right_result)) and \
                (lelt_hit := self.get_rayhit(left_result)):
            if right_hit.get_node() == lelt_hit.get_node():
                return right_hit
        return None

    def go_forward(self, dist):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        next_pos = self.get_pos() + orientation * dist

        if below_hit := self.current_location():
            if forward_hit := self.watch_steps():
                below_height = below_hit.get_hit_pos().z
                forward_height = forward_hit.get_hit_pos().z

                if 0.5 < (diff := forward_height - below_height) < 1.2:
                    next_pos.z += diff
        self.set_pos(next_pos)

    def go_back(self, dist):
        orientation = self.direction_node.get_quat(base.render).get_forward()
        self.set_pos(self.get_pos() + orientation * dist)

    def turn(self, angle):
        self.direction_node.set_h(self.direction_node.get_h() + angle)

    def play_anim(self, command, rate=1):
        if self.actor.get_current_anim() != command:
            self.actor.loop(command)
            self.actor.set_play_rate(rate, command)

    def stop_anim(self):
        if self.actor.get_current_anim() is not None:
            self.actor.stop()
            self.actor.pose(self.WALK, 5)


class BasicAmbientLight(NodePath):

    def __init__(self):
        super().__init__(AmbientLight('ambient_light'))
        self.node().set_color((0.6, 0.6, 0.6, 1))
        base.render.set_light(self)
        self.reparent_to(base.render)


class BasicDayLight(NodePath):

    def __init__(self, parent):
        super().__init__(DirectionalLight('directional_light'))
        self.node().get_lens().set_film_size(200, 200)
        self.node().get_lens().set_near_far(10, 200)
        self.node().set_color((1, 1, 1, 1))
        self.set_pos_hpr(Point3(0, 0, 50), Vec3(-30, -45, 0))
        self.node().set_shadow_caster(True, 8192, 8192)

        state = self.node().get_initial_state()
        temp = NodePath(PandaNode('temp_np'))
        temp.set_state(state)
        temp.set_depth_offset(-3)
        self.node().set_initial_state(temp.get_state())

        base.render.set_light(self)
        base.render.set_shader_auto()
        self.reparent_to(parent)


class Walking(ShowBase):

    def __init__(self):
        super().__init__()
        self.disable_mouse()
        self.world = BulletWorld()
        self.world.set_gravity(Vec3(0, 0, -9.81))

        self.debug_np = self.render.attach_new_node(BulletDebugNode('debug'))
        self.world.set_debug_node(self.debug_np.node())

        self.scene = Scene(self.world)
        self.walker = Walker(self.world)

        self.floater = NodePath('floater')
        self.floater.set_z(2.0)
        self.floater.reparent_to(self.walker)

        self.camera.reparent_to(self.walker)
        self.camera.set_pos(self.walker.navigate())
        self.camera.look_at(self.floater)
        self.camLens.set_fov(90)

        # setup light
        self.ambient_light = BasicAmbientLight()
        self.directional_light = BasicDayLight(self.camera)

        self.mask = BitMask32.bit(2) | BitMask32.bit(1)

        inputState.watch_with_modifiers('forward', 'arrow_up')
        inputState.watch_with_modifiers('backward', 'arrow_down')
        inputState.watch_with_modifiers('left', 'arrow_left')
        inputState.watch_with_modifiers('right', 'arrow_right')

        self.accept('escape', sys.exit)
        self.accept('p', self.print_info)
        self.accept('d', self.toggle_debug)
        self.accept('f', self.walker.toggle_debug)
        self.taskMgr.add(self.update, 'update')

    def toggle_debug(self):
        if self.debug_np.is_hidden():
            self.debug_np.show()
        else:
            self.debug_np.hide()

    def control_walker(self, dt):
        # contol walker movement
        if inputState.is_set('forward'):
            self.walker.go_forward(-10 * dt)
        if inputState.is_set('backward'):
            self.walker.go_back(10 * dt)
        if inputState.is_set('left'):
            self.walker.turn(100 * dt)
        if inputState.is_set('right'):
            self.walker.turn(-100 * dt)

        # play animation
        if inputState.is_set('forward'):
            self.walker.play_anim(self.walker.RUN)
        elif inputState.is_set('backward'):
            self.walker.play_anim(self.walker.WALK, -1)
        elif inputState.is_set('left') or inputState.is_set('right'):
            self.walker.play_anim(self.walker.WALK)
        else:
            self.walker.stop_anim()

    def print_info(self):
        print('camera', self.camera.get_pos(), self.camera.get_pos(self.walker))
        print('walker', self.walker.get_pos(), 'camera', self.camera.get_pos(self.walker) + self.walker.get_pos())
        print('navigator', self.walker.get_relative_point(self.walker.direction_node, Vec3(0, 10, 2)))
        print('navigator + walker_pos', self.walker.get_pos() + self.walker.get_relative_point(self.walker.direction_node, Vec3(0, 10, 2)))

    def ray_cast(self, from_pos, to_pos):
        result = self.world.ray_test_closest(from_pos, to_pos, self.mask)

        if result.has_hit():
            return result.get_node()
        return None

    def find_camera_pos(self, walker_pos, next_pos):
        q = Quat()
        point = Point3(0, 0, 0)
        start = self.camera.get_pos()
        angle = r = None

        for i in range(36):
            camera_pos = next_pos + walker_pos
            if self.ray_cast(camera_pos, walker_pos) == self.walker.node():
                return next_pos

            times = i // 2 + 1
            angle = 10 * times if i % 2 == 0 else -10 * times
            q.set_from_axis_angle(angle, Vec3.up())
            r = q.xform(start - point)
            next_pos = point + r

        return None

    def control_camera_outdoors(self):
        """Repositions the camera if the camera's view is blocked by objects like walls, and
           reparents the camera to the room_camera if the character goes into a room.
        """
        # reposition
        walker_pos = self.walker.get_pos()
        camera_pos = self.camera.get_pos() + walker_pos

        if self.ray_cast(camera_pos, walker_pos) != self.walker.node():
            if next_pos := self.find_camera_pos(walker_pos, self.walker.navigate()):
                self.camera.set_pos(next_pos)
                self.camera.look_at(self.floater)

        # reparent camera
        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if (name := location.get_node().get_name()).startswith('room'):
                room_camera = self.render.find(f'**/{name}_camera')
                self.camera.detach_node()
                self.camera.reparent_to(room_camera)
                self.camera.set_pos(0, 0, 0)
                self.camera.look_at(self.floater)

    def control_camera_indoors(self):
        self.camera.look_at(self.floater)

        if location := self.walker.current_location():  # location: panda3d.bullet.BulletRayHit
            if not location.get_node().get_name().startswith('room'):
                self.camera.detach_node()
                self.camera.reparent_to(self.walker)
                self.camera.set_pos(0, -10, 2)
                self.camera.look_at(self.floater)

    def update(self, task):
        dt = globalClock.get_dt()
        self.control_walker(dt)

        if self.walker.is_ancestor_of(self.camera):
            self.control_camera_outdoors()
        else:
            self.control_camera_indoors()

        self.world.do_physics(dt)
        return task.cont


if __name__ == '__main__':
    app = Walking()
    app.run()

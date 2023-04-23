import sys

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.InputStateGlobal import inputState
from direct.gui.DirectGui import OnscreenText
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletDebugNode
from panda3d.core import NodePath, PandaNode, TextNode
from panda3d.core import Vec3, Point3, BitMask32, Quat

from lights import BasicAmbientLight, BasicDayLight
from scene import Scene
from walker import Walker


class Instructions(NodePath):

    def __init__(self):
        super().__init__(PandaNode('instructions'))
        self.create_instructions([
            '[ESC]: Quit',
            '[Left Arrow]: Rotate Ralph Left',
            '[Right Arrow]: Rotate Ralph Right',
            '[Up Arrow]: Run Ralph Forward',
            '[Down Arrow]: Walk Ralph Backward',
            '[ I ]: ON/OFF Instructions'
        ])
        self.reparent_to(base.a2dTopLeft)

    def create_instructions(self, texts):
        start_y = -0.1

        for i, text in enumerate(texts):
            OnscreenText(
                text=text,
                parent=self,
                align=TextNode.ALeft,
                pos=(0.05, start_y - (i * 0.05)),
                fg=(1, 1, 1, 1),
                scale=0.05,
            )


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

        # show instructions
        self.instructions = Instructions()

        # setup light
        self.ambient_light = BasicAmbientLight()
        self.directional_light = BasicDayLight(self.walker)

        self.mask = BitMask32.bit(1)

        inputState.watch_with_modifiers('forward', 'arrow_up')
        inputState.watch_with_modifiers('backward', 'arrow_down')
        inputState.watch_with_modifiers('left', 'arrow_left')
        inputState.watch_with_modifiers('right', 'arrow_right')

        self.accept('escape', sys.exit)
        self.accept('p', self.print_info)
        self.accept('d', self.toggle_debug)
        self.accept('f', self.walker.toggle_debug)
        self.accept('i', self.toggle_instructions)

        self.taskMgr.add(self.update, 'update')

    def toggle_debug(self):
        if self.debug_np.is_hidden():
            self.debug_np.show()
        else:
            self.debug_np.hide()

    def toggle_instructions(self):
        if self.instructions.is_hidden():
            self.instructions.show()
        else:
            self.instructions.hide()

    def control_walker(self, dt):
        # contol walker movement
        direction = 0
        angle = 0

        if inputState.is_set('forward'):
            direction += -1
        if inputState.is_set('backward'):
            direction += 1
        if inputState.is_set('left'):
            angle += 100 * dt
        if inputState.is_set('right'):
            angle += -100 * dt

        self.walker.update(dt, direction, angle)

        # play animation
        anim = None
        rate = 1

        if inputState.is_set('forward'):
            anim = self.walker.RUN
        elif inputState.is_set('backward'):
            anim, rate = self.walker.WALK, -1
        elif inputState.is_set('left') or inputState.is_set('right'):
            anim = self.walker.WALK

        self.walker.play_anim(anim, rate)

    def print_info(self):
        print('walker', self.walker.get_pos())

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
        """Reposition the camera if the camera's view is blocked by objects like walls, and
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



# Assertion failed: other._error_type == ET_ok at line 399 of panda/src/pgraph/nodePath.cxx
# Traceback (most recent call last):
#   File "C:\Users\Kanae\Desktop\py311env\RalphWalking\walking.py", line 197, in update
#     self.control_camera_outdoors()
#   File "C:\Users\Kanae\Desktop\py311env\RalphWalking\walking.py", line 178, in control_camera_outdoors
#     self.camera.reparent_to(room_camera)
# AssertionError: other._error_type == ET_ok at line 399 of panda/src/pgraph/nodePath.cxx
# :task(error): Exception occurred in PythonTask update.
# Traceback (most recent call last):
#   File "C:\Users\Kanae\Desktop\py311env\RalphWalking\walking.py", line 207, in <module>
#     app.run()
#   File "C:\Users\Kanae\Desktop\py311env\py311env\Lib\site-packages\direct\showbase\ShowBase.py", line 3330, in run
#     self.taskMgr.run()
#   File "C:\Users\Kanae\Desktop\py311env\py311env\Lib\site-packages\direct\task\Task.py", line 553, in run
#     self.step()
#   File "C:\Users\Kanae\Desktop\py311env\py311env\Lib\site-packages\direct\task\Task.py", line 504, in step
#     self.mgr.poll()
#   File "C:\Users\Kanae\Desktop\py311env\RalphWalking\walking.py", line 197, in update
#     self.control_camera_outdoors()
#   File "C:\Users\Kanae\Desktop\py311env\RalphWalking\walking.py", line 178, in control_camera_outdoors
#     self.camera.reparent_to(room_camera)
# AssertionError: other._error_type == ET_ok at line 399 of panda/src/pgraph/nodePath.cxx
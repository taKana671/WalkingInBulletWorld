"""
Textures: Eric Matyas (https://soundimage.org/attribution-info/)
"""
import math
from enum import Enum
from itertools import product, chain

from panda3d.core import Vec3, Vec2, Point3, LColor
from panda3d.core import Texture, TextureStage
from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape, BulletSphereShape
from panda3d.bullet import BulletTriangleMeshShape, BulletTriangleMesh
from panda3d.bullet import BulletRigidBodyNode

from automatic_doors import SlidingDoor, ConeTwistDoor, SlidingDoorSensor, ConeTwistDoorSensor
from create_geomnode import Cube, RightTriangularPrism, Tube, RingShape, SphericalShape, Cylinder
from create_softbody import RopeMaker, ClothMaker
from elevator import Elevator, ElevatorDoorSensor
from mask_manager import Mask


class Images(Enum):

    FIELD_STONE = 'fieldstone.jpg'
    IRON = 'iron.jpg'
    BOARD = 'board.jpg'
    BRICK = 'brick.jpg'
    CONCRETE = 'concrete.jpg'
    LAYINGBROCK = 'layingrock.jpg'
    COBBLESTONES = 'cobblestones.jpg'
    METALBOARD = 'metalboard.jpg'
    CONCRETE2 = 'concrete2.jpg'
    ROPE = 'rope2.jpg'
    BARK = 'bark1.jpg'
    FABRIC = 'fabric2.jpg'
    CONCRETE4 = 'concrete4.jpg'
    BRICK2 = 'tile2.jpg'

    SMALL_STONES = 'small_stones.jpg'

    @property
    def path(self):
        return f'textures/{self.value}'


class Material(NodePath):

    def __init__(self, name, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)
        self.set_collide_mask(bitmask)


class Block(Material):

    def __init__(self, name, model, pos, hpr, scale, bitmask):
        super().__init__(name, pos, hpr, scale, bitmask)
        self.model = model.copy_to(self)
        end, tip = self.model.get_tight_bounds()
        self.node().add_shape(BulletBoxShape((tip - end) / 2))
        self.set_collide_mask(bitmask)
        self.node().set_mass(0)


class InvisibleLift(Material):

    def __init__(self, name, shape, pos, hpr, scale, bitmask):
        super().__init__(name, pos, hpr, scale, bitmask)
        self.node().add_shape(shape)
        self.set_collide_mask(bitmask)
        self.node().set_kinematic(True)
        self.hide()


class Convex(Material):

    def __init__(self, name, model, pos, hpr, scale, bitmask):
        super().__init__(name, pos, hpr, scale, bitmask)
        self.model = model.copy_to(self)
        shape = BulletConvexHullShape()
        shape.add_geom(self.model.node().get_geom(0))
        self.node().add_shape(shape)


class Ring(Material):

    def __init__(self, name, model, pos, hpr, scale, bitmask):
        super().__init__(name, pos, hpr, scale, bitmask)
        self.model = model.copy_to(self)
        mesh = BulletTriangleMesh()
        mesh.add_geom(self.model.node().get_geom(0))
        shape = BulletTriangleMeshShape(mesh, dynamic=False)
        self.node().add_shape(shape)


class Sphere(Material):

    def __init__(self, name, model, pos, scale, bitmask):
        super().__init__(name, pos, Vec3(0), scale, bitmask)
        self.model = model.copy_to(self)
        end, tip = self.model.get_tight_bounds()
        size = tip - end
        self.node().add_shape(BulletSphereShape(size.z / 2))


class Buildings(NodePath):

    _textures = dict()

    def __init__(self, world, name):
        super().__init__(PandaNode(name))
        self.world = world
        self.cube = Cube()
        self.cylinder = Cylinder()
        self.right_triangle_prism = RightTriangularPrism()
        self.sphere = SphericalShape(segments=42)

    def texture(self, image):
        if image not in self._textures:
            tex = base.loader.load_texture(image.path)
            tex.set_wrap_u(Texture.WM_repeat)
            tex.set_wrap_v(Texture.WM_repeat)
            self._textures[image] = tex

        return self._textures[image]

    # def block(self, name, parent, pos, scale,
    #           hpr=None, horizontal=True, bitmask=BitMask32.bit(1), hide=False, active=False):
    def block(self, name, parent, pos, scale,
              hpr=None, horizontal=True, bitmask=Mask.building, hide=False, active=False):
        if not hpr:
            hpr = Vec3(0, 0, 0) if horizontal else Vec3(90, 0, 0)

        block = Block(name, self.cube, pos, hpr, scale, bitmask)
        su = (scale.x * 2 + scale.y * 2) / 4
        sv = scale.z / 4
        block.set_tex_scale(TextureStage.get_default(), su, sv)

        if hide:
            block.hide()

        if active:
            block.node().set_mass(1)
            block.node().set_deactivation_enabled(False)

        block.reparent_to(parent)
        self.world.attach(block.node())
        return block

    def lift(self, name, parent, overlap_obj, bitmask=Mask.lift):
        lift = InvisibleLift(
            name,
            overlap_obj.node().get_shape(0),
            overlap_obj.get_pos(),
            overlap_obj.get_hpr(),
            overlap_obj.get_scale(),
            bitmask
        )

        lift.reparent_to(parent)
        self.world.attach(lift.node())
        return lift

    def knob(self, door, name, pos, color=LColor(0, 0, 0, 1)):
        end, tip = door.get_tight_bounds()
        scale = Vec3((tip - end).y + 1, 0.05, 0.05)
        hpr = Vec3(90, 0, 0)
        knob = Block(name, self.cube, pos, hpr, scale, BitMask32.bit(1))
        knob.set_hpr(hpr)
        knob.set_color(color)
        knob.reparent_to(door)

    def twist(self, door, wall, door_frame, wall_frame, inward=True):
        direction = 1 if door_frame.x < 0 else -1
        if not inward:
            direction *= -1

        twist = ConeTwistDoor(
            door.node(),
            wall.node(),
            TransformState.make_pos(door_frame),
            TransformState.make_pos(wall_frame),
            direction
        )

        self.world.attach_constraint(twist, True)
        return twist

    def slider(self, door, wall, door_frame, wall_frame, horizon=True):
        if horizon:
            ts_door_frame = TransformState.make_pos(door_frame)
            ts_wall_frame = TransformState.make_pos(wall_frame)
            movement_range = -door_frame.x * 2
        else:  # shutter
            ts_door_frame = TransformState.make_pos_hpr(door_frame, Vec3(0, 0, -90))
            ts_wall_frame = TransformState.make_pos_hpr(wall_frame, Vec3(0, 0, -90))
            movement_range = -door_frame.z * 2

        direction = 1 if movement_range > 0 else -1

        slider = SlidingDoor(
            door.node(),
            wall.node(),
            ts_door_frame,
            ts_wall_frame,
            movement_range,
            direction
        )

        self.world.attach_constraint(slider, True)
        return slider

    def door_sensor(self, name, parent, pos, scale, bitmask, sensor, *args):
        """Arges:
                sensor (SlidingDoorSensor or ConeTwistDoorSensor)
                args: stop_pos (Point3) and constrains if sensor is ElevatorDoorSensor, and constrains only if not.
        """
        sensor = sensor(name, self.world, self.cube, pos, scale, bitmask, *args)
        sensor.hide()
        sensor.reparent_to(parent)
        self.world.attach_ghost(sensor.node())

        return sensor

    # def pole(self, name, parent, pos, scale, tex_scale, hpr=None, vertical=True,
            #  bitmask=BitMask32.bit(3), hide=False, active=False):
    def pole(self, name, parent, pos, scale, tex_scale, hpr=None, vertical=True,
             bitmask=Mask.building, hide=False, active=False):
        if not hpr:
            hpr = Vec3(0, 0, 180) if vertical else Vec3(0, 90, 0)

        pole = Convex(name, self.cylinder, pos, hpr, scale, bitmask)
        pole.set_tex_scale(TextureStage.get_default(), tex_scale)

        if hide:
            pole.hide()

        if active:
            pole.node().set_mass(1)
            # pole.node().set_deactivation_enabled(False)

        pole.reparent_to(parent)
        self.world.attach(pole.node())
        return pole

    def triangular_prism(self, name, parent, pos, hpr, scale,
                         tex_scale=None, hide=False,  bitmask=Mask.building):
        prism = Convex(name, self.right_triangle_prism, pos, hpr, scale, bitmask)

        if tex_scale:
            prism.set_tex_scale(TextureStage.get_default(), tex_scale)
        if hide:
            prism.hide()

        prism.reparent_to(parent)
        self.world.attach(prism.node())
        return prism

    def room_camera(self, name, parent, pos, moving_direction=None, hide=False):
        """Args:
            moving_direction (str): 'x' or 'y'
        """
        room_camera = self.block(name, parent, pos, Vec3(0.25, 0.25, 0.25))
        room_camera.set_color((0, 0, 0, 1))

        if moving_direction:
            room_camera.set_tag('moving_direction', moving_direction)

        if hide:
            room_camera.hide()

        return room_camera

    def point_on_circumference(self, angle, radius):
        rad = math.radians(angle)
        x = math.cos(rad) * radius
        y = math.sin(rad) * radius
        return x, y

    def tube(self, name, parent, geomnode, pos, scale, hpr=None, horizontal=True, bitmask=BitMask32.allOn()):
        if not hpr:
            hpr = Vec3(0, 90, 0) if horizontal else Vec3(90, 0, 0)

        tube = Ring(name, geomnode, pos, hpr, scale, bitmask)

        tube.reparent_to(parent)
        self.world.attach(tube.node())
        return tube

    def ring_shape(self, name, parent, geomnode, pos, scale=Vec3(1), hpr=None, hor=True,
                   tex_scale=None, bitmask=BitMask32.all_on()):
        if not hpr:
            hpr = Vec3(0, 90, 0) if hor else Vec3(90, 0, 0)

        ring = Ring(name, geomnode, pos, hpr, scale, bitmask)
        if tex_scale:
            ring.set_tex_scale(TextureStage.get_default(), tex_scale)

        ring.reparent_to(parent)
        self.world.attach(ring.node())
        return ring

    def sphere_shape(self, name, parent, pos, scale, bitmask=BitMask32.bit(1)):
        sphere = Sphere(name, self.sphere, pos, scale, bitmask)

        sphere.reparent_to(parent)
        self.world.attach(sphere.node())
        return sphere


class StoneHouse(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'stoneHouse')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def build(self):
        self._build()
        base.taskMgr.add(self.sensor1.sensing, 'stone1_sensing')
        base.taskMgr.add(self.sensor2.sensing, 'stone2_sensing')
        # Child nodes of the self.building are combined together into one node
        # (maybe into the node lastly parented to self.house?).
        self.flatten_strong()

    def make_textures(self):
        self.wall_tex = self.texture(Images.FIELD_STONE)    # for walls
        self.floor_tex = self.texture(Images.IRON)          # for floors, steps and roof
        self.door_tex = self.texture(Images.BOARD)          # for doors
        self.column_tex = self.texture(Images.CONCRETE)     # for columns
        self.fence_tex = self.texture(Images.METALBOARD)

    def _build(self):
        self.make_textures()
        walls = NodePath('walls')
        walls.reparent_to(self)
        floors = NodePath('floors')
        floors.reparent_to(self)
        doors = NodePath('doors')
        doors.reparent_to(self)
        columns = NodePath('columns')
        columns.reparent_to(self)
        fences = NodePath('fences')
        fences.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self)

        # columns
        gen = ((x, y) for x, y in product((-15, 15), (-11, 11)))
        for i, (x, y) in enumerate(gen):
            pos = Point3(x, y, -0.5)
            self.pole(f'column_{i}', columns, pos, Vec3(2, 2, 6), Vec2(2, 1))

        # the 1st floor outside
        pos_scale = [
            [Point3(-11, 0, 0), Vec3(10, 1, 24)],          # left
            [Point3(11, 0, 0), Vec3(10, 1, 24)],           # right
            [Point3(0, -10, 0), Vec3(12, 1, 4)],           # front
            [Point3(0, 10, 0), Vec3(12, 1, 4)]             # back
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'floor1_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0))

        # room floor and room camera on the 1st floor
        self.block('room1', floors, Point3(0, 0, 0), Vec3(12, 1, 16), hpr=Vec3(0, 90, 0))
        self.room_camera('room1_camera', room_camera, Point3(0, 0, 6.25))

        # walls on the 1st floor
        walls_1st_floor = [
            [Point3(-5.75, 0, 3.5), Vec3(16, 0.5, 6), False],          # left
            [Point3(5.75, 0, 1.5), Vec3(16, 0.5, 2), False],           # right under
            [Point3(5.75, 3, 3.5), Vec3(10, 0.5, 2), False],           # right middle back
            [Point3(5.75, -7, 3.5), Vec3(2, 0.5, 2), False],           # right front
            [Point3(5.75, 0, 5.5), Vec3(16, 0.5, 2), False],           # right top
            [Point3(-13.75, -4.25, 7), Vec3(8.5, 0.5, 13), False],     # left side of the steps
            [Point3(0, 8.25, 3.5), Vec3(12, 0.5, 6), True],            # rear
            [Point3(0, -8.25, 5.5), Vec3(12, 0.5, 2), True],           # front top
        ]
        for i, (pos, scale, hpr) in enumerate(walls_1st_floor):
            self.block(f'wall1_{i}', walls, pos, scale, horizontal=hpr)

        # doors on the lst floor
        door_scale = Vec3(2, 0.5, 4)
        y, z = -8.25, 2.5
        # left
        wall1_l = self.block('wall1_l', walls, Point3(-4, y, z), Vec3(4, 0.5, 4))
        door1_l = self.block('door1_l', doors, Point3(-1, y, z), door_scale, bitmask=Mask.door, active=True)
        self.knob(door1_l, 'knob1_l', Point3(0.4, 0, 0))
        # right
        wall1_r = self.block('wall1_r', walls, Point3(4, y, z), Vec3(4, 0.5, 4))
        door1_r = self.block('door1_r', doors, Point3(1, y, z), door_scale, bitmask=Mask.door, active=True)
        self.knob(door1_r, 'knob1_r', Point3(-0.4, 0, 0))
        # twists
        twists = []
        for h in [1.8, -1.8]:
            twists.append(self.twist(door1_l, wall1_l, Point3(-1, 0, h), Point3(2, 0, h)))
            twists.append(self.twist(door1_r, wall1_r, Point3(1, 0, h), Point3(-2, 0, h)))

        self.sensor1 = self.door_sensor(
            'stone_sensor1', invisible, Point3(0, -8, 0), Vec3(4, 4, 1), Mask.sensor, ConeTwistDoorSensor, *twists
        )

        # 2nd floor
        pos_scale = [
            [Point3(4, -4.25, 6.75), Vec3(20, 0.5, 8.5)],
            [Point3(-9.75, -1, 6.75), Vec3(7.5, 0.5, 2)]
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'floor2_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0))

        # room floor and room camera on the 2nd floor
        self.block('room2', floors, Point3(-4, 4.25, 6.75), Vec3(20, 0.5, 8.5), hpr=Vec3(0, 90, 0))
        self.room_camera('room2_camera', room_camera, Point3(-10, 4, 13))

        # balcony fence
        pos_scale_hpr = [
            [Point3(4, -8.25, 7.75), Vec3(0.5, 1.5, 20), Vec3(0, 90, 90)],
            [Point3(-5.75, -5, 7.75), Vec3(0.5, 1.5, 6), Vec3(0, 90, 0)],
            [Point3(13.75, -4, 7.75), Vec3(0.5, 1.5, 8), Vec3(0, 90, 0)],
            [Point3(10, 0.25, 7.5), Vec3(0.5, 2.0, 8), Vec3(0, 90, 90)]
        ]

        for i, (pos, scale, hpr) in enumerate(pos_scale_hpr):
            self.block(f'balcony_{i}', floors, pos, scale, hpr=hpr, bitmask=Mask.poles)

        # walls on the 2nd floor
        walls_2nd_floor = [
            [Point3(-13.75, 4, 8), Vec3(8, 0.5, 2), False],         # left
            [Point3(-13.75, 1.5, 10), Vec3(3, 0.5, 2), False],      # left
            [Point3(-13.75, 6.5, 10), Vec3(3, 0.5, 2), False],      # left
            [Point3(-13.75, 4, 12), Vec3(8, 0.5, 2), False],        # left
            [Point3(5.75, 4.25, 10), Vec3(7.5, 0.5, 6), False],     # right
            [Point3(-4, 8.25, 10), Vec3(20, 0.5, 6), True],         # rear
            [Point3(-6.5, 0.25, 9), Vec3(1, 0.5, 4), True],         # front
            [Point3(-7.75, 0.125, 9), Vec3(1.5, 0.25, 4), True],    # front
            [Point3(-13.25, 0.25, 9), Vec3(0.5, 0.5, 4), True],     # front
            [Point3(-12.25, 0.125, 9), Vec3(1.5, 0.25, 4), True],   # front
            [Point3(-9.75, 0.25, 12), Vec3(7.5, 0.5, 2), True],     # front
            [Point3(0, 0.25, 8), Vec3(12, 0.5, 2), True],           # front
            [Point3(-4, 0.25, 10), Vec3(4, 0.5, 2), True],          # front
            [Point3(4, 0.25, 10), Vec3(4, 0.5, 2), True],           # front
            [Point3(0, 0.25, 12), Vec3(12, 0.5, 2), True]           # front
        ]
        for i, (pos, scale, hor) in enumerate(walls_2nd_floor):
            self.block(f'wall2_{i}', walls, pos, scale, horizontal=hor)

        # doors on the 2nd floor
        door_scale = Vec3(1.5, 0.25, 4)
        y, z = 0.375, 9
        # left
        wall2_l = self.block('wall2_l', invisible, Point3(-12.25, y, z), door_scale, hide=True)
        door2_l = self.block('door2_l', doors, Point3(-10.75, y, z), door_scale, bitmask=Mask.door, active=True)
        self.knob(door2_l, 'knob2_l', Point3(0.3, 0, 0))
        # right
        wall2_r = self.block('wall2_r', invisible, Point3(-7.75, y, z), door_scale, hide=True)
        door2_r = self.block('door2_r', doors, Point3(-9.25, y, z), door_scale, bitmask=Mask.door, active=True)
        self.knob(door2_r, 'knob2_r', Point3(-0.3, 0, 0))

        x = door_scale.x / 2
        slider1 = self.slider(door2_l, wall2_l, Point3(-x, 0, 0), Point3(x, 0, 0))
        slider2 = self.slider(door2_r, wall2_r, Point3(x, 0, 0), Point3(-x, 0, 0))
        self.sensor2 = self.door_sensor('stone_sensor2', invisible, Point3(-10, -0, 6.75), Vec3(3, 4, 0.5), Mask.sensor,
                                        SlidingDoorSensor, slider1, slider2)

        # roof
        self.block('roof', floors, Point3(-4, 4.25, 13.25), Vec3(20, 8.5, 0.5))

        # steps that leads to the 2nd floor
        for i in range(7):
            pos = Point3(-9.75, -8.5 + i, 0 + i)
            hide = True if i == 0 else False
            block = self.block(f'step_2{i}', floors, pos, Vec3(7.5, 1, 1), hpr=Vec3(0, 90, 0), hide=hide)
            self.lift(f'lift_2{i}', invisible, block)

        # steps that leads to the 1st floor
        x_diffs = [15.9, -15.9]

        for i in range(5):
            pos = Point3(0, 12.5 + i, 0 - i)
            block = self.block(f'step_1{i}', floors, pos, Vec3(32, 1, 1), hpr=Vec3(0, 90, 0))
            if i > 0:
                self.lift(f'lift_1{i}', invisible, block)

            # falling preventions
            for j, x_diff in enumerate(x_diffs):
                f_pos = pos + Vec3(x_diff, 0, 1.5)
                self.block(f'step_fence_{i}{j}', fences, f_pos, Vec3(0.15, 0.15, 2.1), bitmask=Mask.poles)

            # handrails
            if i == 2:
                for k, x_diff in enumerate(x_diffs):
                    rail_pos = pos + Vec3(x_diff, 0, 2.5)
                    self.block(f'handrail_{i}{k}', fences, rail_pos, Vec3(0.15, 0.15, 5.7), Vec3(0, 45, 0), bitmask=Mask.poles)

        doors.set_texture(self.door_tex)
        walls.set_texture(self.wall_tex)
        floors.set_texture(self.floor_tex)
        columns.set_texture(self.column_tex)
        fences.set_texture(self.fence_tex)


class BrickHouse(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'brickHouse')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def build(self):
        self._build()
        base.taskMgr.add(self.sensor.sensing, 'brick_sensing')
        self.flatten_strong()

    def make_textures(self):
        self.wall_tex = self.texture(Images.BRICK)      # for walls
        self.floor_tex = self.texture(Images.CONCRETE)  # for floors
        self.roof_tex = self.texture(Images.IRON)       # for roofs
        self.door_tex = self.texture(Images.BOARD)      # for doors

    def _build(self):
        self.make_textures()
        floors = NodePath('foundation')
        floors.reparent_to(self)
        walls = NodePath('wall')
        walls.reparent_to(self)
        roofs = NodePath('roof')
        roofs.reparent_to(self)
        doors = NodePath('door')
        doors.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self)

        # room floors
        pos_scale = [
            [Point3(0, 0, 0), Vec3(13, 9, 3)],     # big room
            [Point3(3, -6.5, 0), Vec3(7, 4, 3)],   # small room
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'room_brick{i}', floors, pos, scale)
            if i == 1:
                self.small_room = self.block(f'room_brick{i}', floors, pos, scale)

        # room_camera
        self.room_camera('room_brick1_camera', room_camera, Point3(3, 3, 5.5))

        # steps
        steps_num = 3

        for i in range(steps_num):
            step_pos = Point3(3, -9.5 - i, 1 - i)
            scale = Vec3(7, 2 + i * 2, 1)
            block = self.block(f'step_{i}', floors, step_pos, scale)

            if i > 0:
                self.lift(f'step_lift_{i}', invisible, block)

            # invisible slope
            if i == steps_num - 1:
                slope_pos = step_pos + Vec3(0, -3.5, 0)
                self.triangular_prism('hidden_slope', invisible, slope_pos, Vec3(0, 180, 90), Vec3(1, 1, 7), hide=True)

        # walls
        walls_1st_floor = [
            [Point3(0, 4.25, 5.5), Vec3(12, 0.5, 8), True],          # rear
            [Point3(5, -8.25, 3.25), Vec3(2, 0.5, 3.5), True],       # front right
            [Point3(1, -8.375, 3.25), Vec3(2, 0.25, 3.5), True],     # front left
            [Point3(3, -8.25, 5.25), Vec3(6, 0.5, 0.5), True],       # front_top
            [Point3(-1.5, -4.25, 5.5), Vec3(2, 0.5, 8), True],       # back room front right
            [Point3(-5.25, -4.25, 5.5), Vec3(1.5, 0.5, 8), True],    # back room front left
            [Point3(-3.5, -4.25, 3.0), Vec3(2, 0.5, 3), True],       # back room front under
            [Point3(-3.5, -4.25, 8.0), Vec3(2, 0.5, 3), True],       # back room front under
            [Point3(3, -4.25, 7.5), Vec3(7, 0.5, 4), True],          # back room front
            [Point3(-0.25, -6.25, 3.5), Vec3(4.5, 0.5, 4), False],   # left side
            [Point3(-6.25, -3, 5.5), Vec3(3, 0.5, 8), False],
            [Point3(-6.25, 3, 5.5), Vec3(3, 0.5, 8), False],
            [Point3(-6.25, 0, 3.0), Vec3(3, 0.5, 3), False],
            [Point3(-6.25, 0, 8.0), Vec3(3, 0.5, 3), False],
            [Point3(6.25, -6.25, 3.5), Vec3(4.5, 0.5, 4), False],    # right side
            [Point3(6.25, -2.75, 5.5), Vec3(2.5, 0.5, 8), False],
            [Point3(6.25, 3, 5.5), Vec3(3, 0.5, 8), False],
            [Point3(6.25, 0, 3.0), Vec3(3, 0.5, 3), False],
            [Point3(6.25, 0, 8.0), Vec3(3, 0.5, 3), False]
        ]
        for i, (pos, scale, hor) in enumerate(walls_1st_floor):
            self.block(f'wall1_{i}', walls, pos, scale, horizontal=hor)

        # door
        door_scale = Vec3(2, 0.25, 3.5)
        y, z = -8.125, 3.25

        wall_l = self.block('wall1_l', walls, Point3(1, y, z), door_scale, hide=True)
        door = self.block('door_1', doors, Point3(3, y, z), door_scale, bitmask=Mask.door, active=True)
        self.knob(door, 'knob_1', Point3(0.4, 0, 0))
        slider = self.slider(door, wall_l, Point3(-1, 0, 0), Point3(1, 0, 0))
        self.sensor = self.door_sensor(
            'brick_sensor', invisible, Point3(3, -8.25, 1), Vec3(2, 3, 1), Mask.sensor, SlidingDoorSensor, slider)

        # roofs
        pos_scale = [
            ((Point3(3, -6.5, 5.75 + 0.25 * i), Vec3(7 - i, 4 - i, 0.5)) for i in range(2)),  # small room
            ((Point3(0, 0, 9.75 + 0.25 * i), Vec3(13 - i, 9 - i, 0.5)) for i in range(2)),    # big room
        ]
        for i, (pos, scale) in enumerate(chain(*pos_scale)):
            self.block(f'roof_{i}', roofs, pos, scale)

        floors.set_texture(self.floor_tex)
        walls.set_texture(self.wall_tex)
        roofs.set_texture(self.roof_tex)
        doors.set_texture(self.door_tex)


class Terrace(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'terrace')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def make_textures(self):
        self.wall_tex = self.texture(Images.LAYINGBROCK)    # for walls
        self.floor_tex = self.texture(Images.COBBLESTONES)  # for floor
        self.roof_tex = self.texture(Images.IRON)           # for roofs
        self.steps_tex = self.texture(Images.METALBOARD)    # for steps

    def build(self):
        self.make_textures()
        floors = NodePath('floors')
        floors.reparent_to(self)
        walls = NodePath('walls')
        walls.reparent_to(self)
        roofs = NodePath('roofs')
        roofs.reparent_to(self)
        steps = NodePath('steps')
        steps.reparent_to(self)
        lifts = NodePath('lifts')
        lifts.reparent_to(self)

        # the 1st floor
        self.block('floor1', floors, Point3(0.125, 0, 0), Vec3(16.25, 0.5, 12), hpr=Vec3(0, 90, 0))

        # walls
        pos_scale_hpr = [
            [Point3(-5.5, 5.75, 3.25), Vec3(5, 0.5, 6), True],      # rear
            [Point3(-7.75, 3.25, 3.25), Vec3(4.5, 0.5, 6), False]   # side
        ]
        for i, (pos, scale, hor) in enumerate(pos_scale_hpr):
            self.block(f'wall1_{i}', walls, pos, scale, horizontal=hor)

        # columns
        gen = ((x, y) for x, y in [(-7.5, -5.5), (7.5, -5.5), (7.5, 5.5)])
        for i, (x, y) in enumerate(gen):
            pos = Point3(x, y, 6.25)
            self.pole(f'column_{i}', roofs, pos, Vec3(0.5, 0.5, 8), Vec2(4, 1))

        # roof
        roof_pos = Point3(0, 0, 6.5)
        roof_scale = Vec3(16, 0.5, 12)
        self.block('roof', roofs, Point3(0, 0, 6.5), Vec3(16, 0.5, 12), hpr=Vec3(0, 90, 0))

        # fall prevention blocks on roof
        x = roof_scale.x / 2 - 0.25
        y = roof_scale.z / 2 - 0.25
        z = roof_pos.z + roof_scale.y / 2 + 0.5

        pos_w_hor = [
            [Point3(0, y, z), 16, True],        # rear
            [Point3(0, -y, z), 16, True],       # front
            [Point3(-x, 0, z), 11, False],      # left
            [Point3(x, -1.75, z), 7.5, False]   # right
        ]

        for i, (pos, w, hor) in enumerate(pos_w_hor):
            scale = Vec3(w, 0.5, 1)
            self.block(f'prevention_{i}', roofs, pos, scale, horizontal=hor, bitmask=Mask.fence)

        # spiral center pole
        center = Point3(9, 1.5, 8)
        self.pole('center_pole', roofs, center, Vec3(1.5, 1.5, 10), Vec2(5, 1), bitmask=Mask.poles)
        sphere_pos = center + Vec3(0, 0, 0.7)
        self.sphere_shape('pole_sphere', roofs, sphere_pos, Vec3(0.5), bitmask=Mask.fence)

        # spiral staircase
        steps_num = 7
        scale = Vec3(4, 0.5, 2)

        for i in range(steps_num):
            s_angle = -90 + 30 * i
            sx, sy = self.point_on_circumference(s_angle, 2.5)
            s_pos = Point3(center.x + sx, center.y + sy, i + 0.5)
            block = self.block(f'step_{i}', steps, s_pos, scale, hpr=Vec3(s_angle, 90, 0))

            if i < steps_num - 1:
                self.lift(f'lift_{i}', lifts, block)

            # falling preventions
            for j in range(3):
                f_angle = -100 + 10 * (i * 3 + j)
                fx, fy = self.point_on_circumference(f_angle, 4.3)
                f_scale = Vec3(0.15, 0.15, 2.2 + j * 0.4)
                f_pos = Point3(center.x + fx, center.y + fy, s_pos.z + 0.25 + f_scale.z / 2)
                self.block(f'spiral_fence_{i}{j}', steps, f_pos, f_scale, bitmask=Mask.poles)

        # embedded lift for the first step
        block = self.block('step_0_1', steps, Point3(7, -1, 0), scale, hpr=Vec3(-90, 90, 0), hide=True)
        self.lift('lift_0_1', lifts, block)

        # handrail of spiral staircase
        pos = center - Vec3(0, 0, 5)
        hpr = Vec3(-101, 0, 0)
        geomnode = RingShape(segs_rcnt=14, slope=0.5, ring_radius=4.3, section_radius=0.15)
        self.ring_shape('handrail', steps, geomnode, pos, hpr=hpr, bitmask=Mask.poles)

        for i, pos in enumerate([Point3(8.25, -2.73, 3.0), Point3(7.52, 5.54, 10.0)]):
            self.sphere_shape(f'handrail_sphere_{i}', steps, pos, Vec3(0.15), bitmask=Mask.poles)

        # entrance slope
        self.triangular_prism(
            'entrance_slope', floors, Point3(-9.5, -2.5, 0), Vec3(180, 90, 0), Vec3(3, 0.5, 7), tex_scale=Vec2(3, 2)
        )

        walls.set_texture(self.wall_tex)
        floors.set_texture(self.floor_tex)
        roofs.set_texture(self.roof_tex)
        steps.set_texture(self.steps_tex)
        self.flatten_strong()


class Observatory(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'observatory')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def make_textures(self):
        self.steps_tex = self.texture(Images.METALBOARD)
        self.landing_tex = self.texture(Images.CONCRETE2)
        self.posts_tex = self.texture(Images.IRON)

    def build(self):
        self.make_textures()
        steps = NodePath('steps')
        steps.reparent_to(self)
        landings = NodePath('landings')
        landings.reparent_to(self)
        posts = NodePath('posts')
        posts.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)

        # spiral center pole
        center = Point3(10, 0, 20)
        self.pole('spiral_center', posts, center, Vec3(2.5, 2.5, 20), Vec2(4, 1), bitmask=Mask.fence)
        sphere_pos = center + Vec3(0, 0, 1.1)
        self.sphere_shape('pole_sphere', posts, sphere_pos, Vec3(0.8), bitmask=Mask.fence)

        # spiral staircase
        steps_num = 19                                           # the number of steps
        s_scale = Vec3(4, 2.5, 0.5)                              # scale of a triangular prism

        for i in range(steps_num):
            s_angle = -90 + 30 * i
            sx, sy = self.point_on_circumference(s_angle, 2.5)
            s_pos = Point3(center.x + sx, center.y + sy, i + 0.5)
            hpr = Vec3(s_angle, 180, 180)
            step = self.triangular_prism(f'spiral_step_{i}', steps, s_pos, hpr, s_scale)
            self.lift(f'spiral_step_lift_{i}', invisible, step)

            # falling preventions
            for j in range(3):
                f_angle = -100 + 10 * (i * 3 + j)
                fx, fy = self.point_on_circumference(f_angle, 4.3)
                f_scale = Vec3(0.15, 0.15, 2.2 + j * 0.4)
                f_pos = Point3(center.x + fx, center.y + fy, s_pos.z + 0.25 + f_scale.z / 2)
                self.block(f'spiral_fence_{i}{j}', steps, f_pos, f_scale, bitmask=Mask.poles)

        # handrail of the spiral staircase
        pos = center - Vec3(0, 0, 17)
        hpr = Vec3(-101, 0, 0)
        geomnode = RingShape(segs_rcnt=38, slope=0.5, ring_radius=4.3, section_radius=0.15)
        self.ring_shape('handrail', steps, geomnode, pos, hpr=hpr, bitmask=Mask.poles)

        for i, pos in enumerate([Point3(9.2, -4.2, 3), Point3(8.5, 4.0, 22.05)]):
            self.sphere_shape(f'handrail_sphere_{i}', steps, pos, Vec3(0.15), bitmask=Mask.poles)

        # stair landings
        landing_positions = [
            Point3(6.75, 2.5, 18.25),
            Point3(6.75, 8.5, 15.25),
            Point3(0.75, 8.5, 12.25),
            Point3(-5.25, 8.5, 9.25),
            Point3(-5.25, 2.5, 6.25),
            Point3(-11.25, 2.5, 3.25)
        ]
        for i, pos in enumerate(landing_positions):
            block = self.block(f'landing_{i}', landings, pos, Vec3(4, 1, 4), hpr=Vec3(0, 90, 0))
            if i > 0:
                self.lift(f'landing_lift_{i}', invisible, block)

                # pole supporting landing
                support_pos = pos - Vec3(0, 0, 0.5)
                scale = Vec3(0.5, 0.5, pos.z)
                self.pole(f'support_{i}', posts, support_pos, scale, Vec2(4, 1))

        # steps between stair landings
        scale = Vec3(4, 1, 1)
        diffs = {
            0: (Vec3(0, 2.5 + i, -1 - i) for i in range(2)),    # landing position + diff
            1: (Vec3(-2.5 - i, 0, -1 - i) for i in range(2)),
            2: (Vec3(-2.5 - i, 0, -1 - i) for i in range(2)),
            3: (Vec3(0, -2.5 - i, -1 - i) for i in range(2)),
            4: (Vec3(-2.5 - i, 0, -1 - i) for i in range(2)),
            5: (Vec3(-2.5 - i, 0, -1 - i) for i in range(2))
        }

        for k, val in diffs.items():
            landing_pos = landing_positions[k]
            for i, diff in enumerate(val):
                horizontal = True if diff.x == 0 else False
                step_pos = landing_pos + diff
                block = self.block(f'step_{k}{i}', steps, step_pos, scale, horizontal=horizontal)
                self.lift(f'step_lift_{k}{i}', invisible, block)

        # falling preventions on stair landings
        diff = 1.9
        diffs = {
            0: [(-diff, 0), (0, -diff)],  # key is the index of landings
            1: [(0, diff), (diff, 0)],
            2: [(0, diff), (0, -diff)],
            3: [(-diff, 0), (0, diff)],
            4: [(0, -diff), (diff, 0)],
            5: [(0, diff), (0, -diff)]
        }
        geomnode = RingShape(segs_rcnt=12, ring_radius=1.85, segs_s=8, section_radius=0.1)

        for k, v in diffs.items():
            landing_pos = landing_positions[k]
            for i, (diff_x, diff_y) in enumerate(v):
                fence_pos = landing_pos + Vec3(diff_x, diff_y, 0.5)
                hpr = Vec3(0, 90, 0) if diff_x == 0 else Vec3(90, 90, 0)
                self.ring_shape(f'landing_fence_{k}{i}', steps, geomnode, fence_pos, hpr=hpr, bitmask=Mask.poles)

        steps.set_texture(self.steps_tex)
        landings.set_texture(self.landing_tex)
        posts.set_texture(self.posts_tex)
        self.flatten_strong()


class Bridge(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'bridge')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def make_textures(self):
        self.bridge_tex = self.texture(Images.IRON)         # for bridge girder
        self.column_tex = self.texture(Images.CONCRETE)     # for columns
        self.fence_tex = self.texture(Images.METALBOARD)    # for fences

    def build(self):
        self.make_textures()
        girders = NodePath('girders')
        girders.reparent_to(self)
        columns = NodePath('columns')
        columns.reparent_to(self)
        fences = NodePath('fences')
        fences.reparent_to(self)
        lifts = NodePath('lift')
        lifts.reparent_to(self)

        # bridge girders
        pos_scale = [
            [Point3(0, 0, 0), Vec3(8, 1, 8)],
            [Point3(0, 12, 0), Vec3(4, 1, 16)],
            [Point3(0, -12, 0), Vec3(4, 1, 16)],
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'girder_{i}', girders, pos, scale, hpr=Vec3(0, 90, 0))

        # columns supporting bridge girders
        pos_xy = [
            ((x, y) for x, y in product((3, -3), (3, -3))),
            ((0, y) for y in (12, -12))
        ]
        for i, (x, y) in enumerate(chain(*pos_xy)):
            pos = Point3(x, y, -0.5)
            self.pole(f'column_{i}', columns, pos, Vec3(2, 2, 6), Vec2(2, 1), hpr=(0, 0, 180))

        # steps
        diffs = [1.9, -1.9]

        for i in range(5):
            pos = Point3(0, -20.5 - i, -1 - i)
            block = self.block(f'step_{i}', girders, pos, Vec3(4, 1, 1))
            self.lift(f'lift_{i}', lifts, block)

            # falling preventions
            for j, diff in enumerate(diffs):
                f_pos = pos + Vec3(diff, 0, 1.5)
                self.block(f'step_fence_{i}{j}', fences, f_pos, Vec3(0.15, 0.15, 2.1), bitmask=Mask.poles)

            # handrails
            if i == 2:
                for k, diff_x in enumerate(diffs):
                    rail_pos = pos + Vec3(diff_x, 0, 2.5)
                    self.block(
                        f'handrail_{i}{k}', fences, rail_pos, Vec3(0.15, 0.15, 5.7), Vec3(0, -45, 0), bitmask=Mask.poles)

        # bridge rails
        hand_rails = [
            [((x, y) for x in (-1.875, 1.875) for y in (-11.875, 11.875)), Vec3(16.25, 0.25, 0.5)],
            [((x, 0) for x in (3.875, -3.875)), Vec3(8.0, 0.25, 0.5)],
            [((x, y) for x in (-2.875, 2.875) for y in (3.875, -3.875)), Vec3(0.25, 1.75, 0.5)]
        ]
        for i, (gen, scale) in enumerate(hand_rails):
            for j, (x, y) in enumerate(gen):
                pos = Point3(x, y, 1.75)
                self.block(
                    f'bridge_rail_{i}{j}', girders, pos, scale, horizontal=False, bitmask=Mask.fence)

        rail_blocks = [
            ((x, y + i) for i in range(17) for x in (1.875, -1.875) for y in (3.875, -19.875)),
            ((x, y) for x in (3.875, -3.875) for y in (3.875, -3.875))
        ]
        for i, (x, y) in enumerate(chain(*rail_blocks)):
            pos = Point3(x, y, 1)
            self.block(
                f'rail_block_{i}', girders, pos, Vec3(0.25, 0.25, 1), horizontal=False, bitmask=Mask.fence
            )

        girders.set_texture(self.bridge_tex)
        columns.set_texture(self.column_tex)
        fences.set_texture(self.fence_tex)
        self.flatten_strong()


class Tunnel(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'tunnel')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def make_textures(self):
        self.wall_tex = self.texture(Images.IRON)           # for tunnel
        self.metal_tex = self.texture(Images.METALBOARD)
        self.pedestal_tex = self.texture(Images.FIELD_STONE)

    def build(self):
        self.make_textures()
        walls = NodePath('wall')
        walls.reparent_to(self)
        metal = NodePath('rings')
        metal.reparent_to(self)
        pedestals = NodePath('pedestals')
        pedestals.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)

        # tunnel
        geomnode = Tube(height=20)
        self.tube('tunnel', walls, geomnode, Point3(0, 0, 0), Vec3(4, 4, 4), bitmask=Mask.building)

        # both ends of the tunnel
        positions = [Point3(0, 0, 0), Point3(0, -80, 0)]
        geomnode = RingShape(ring_radius=0.5, section_radius=0.05)

        for i, pos in enumerate(positions):
            self.ring_shape(f'edge_{i}', walls, geomnode, pos, scale=Vec3(4), tex_scale=Vec2(2), bitmask=Mask.building)

        # steps
        steps_num = 5
        start_steps_y = [0.7, -80.7]
        start_z = -2.5
        diffs = [1.9, -1.9]

        for i in range(steps_num):
            for start_y in start_steps_y:
                y = start_y + i if start_y > 0 else start_y - i
                pos = Point3(0, y, start_z - i)
                block = self.block(f'step_{i}', walls, pos, Vec3(4, 1, 1))
                if i > 0:
                    self.lift(f'lift_{i}', invisible, block)

                # falling preventions
                for j, diff in enumerate(diffs):
                    f_pos = pos + Vec3(diff, 0, 1.5)
                    self.block(f'fence_{i}{j}', metal, f_pos, Vec3(0.15, 0.15, 2), bitmask=Mask.poles)

        # handrails
        for x, y in ((x, y) for y in [2.7, -82.7] for x in diffs):
            hpr = (0, 45, 0) if y > 0 else (0, -45, 0)
            pos = Point3(x, y, -2.05)
            self.block(f'handrail_{i}{j}', metal, pos, Vec3(0.15, 0.15, 5.7), hpr=hpr, bitmask=Mask.poles)

        # rings supporting tunnel
        geomnode = RingShape(ring_radius=0.8, section_radius=0.1)

        for i in range(5):
            y = -0.7 - i * 19.65
            ring_pos = Point3(0, y, 0)
            self.ring_shape(f'ring_{i}', metal, geomnode, ring_pos, scale=Vec3(5), tex_scale=Vec2(2, 4), bitmask=Mask.building)

            # culumn supporting ring
            col_pos = Point3(0, y, -7.3)
            self.block(f'column_{i}', pedestals, col_pos, Vec3(2, 2, 6))

            # poles supporting ring
            for j, (x, z) in enumerate([(0, 4), (0, -2), (2, 0), (-4, 0)]):
                pole_pos = Point3(x, y, z)
                hpr = Vec3(0, 0, 180) if x == 0 else Vec3(90, 90, 0)
                self.pole(f'pole_{i}{j}', metal, pole_pos, Vec3(0.8, 0.8, 2), Vec2(1, 1), hpr=hpr, bitmask=Mask.building)

        walls.set_texture(self.wall_tex)
        metal.set_texture(self.metal_tex)
        pedestals.set_texture(self.pedestal_tex)
        self.flatten_strong()


class AdventureBridge(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'tent')
        self.set_pos(center)
        # self.set_h(h)
        self.reparent_to(parent)
        self.center = center

    def make_textures(self):
        self.board_tex = self.texture(Images.BOARD)
        self.bark_tex = self.texture(Images.BARK)

    def build(self):
        self.make_textures()
        barks = NodePath('barks')
        barks.reparent_to(self)
        boards = NodePath('boards')
        boards.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)

        rope = RopeMaker(self.world)
        cloth = ClothMaker(self.world)
        x_pos = [-1.25, 1.25]
        start_z = 1
        log_h_scale = Vec3(1, 1, 3)
        tex_scale = Vec2(2, 1)
        hpr_h = Vec3(0, 0, 90)

        # steps
        step_start_z = start_z - 0.5
        steps = [[-6.5, 6, True], [32.5, 7, False]]

        for i, (start_y, cnt, decrease) in enumerate(steps):
            for j in range(cnt):
                y = start_y - j if decrease else start_y + j
                log_pos = Point3(-1.5, y, step_start_z - j * 0.5)
                step_pos = Point3(0, y, log_pos.z + 0.25)

                self.pole(f'step_{i}{j}', barks, log_pos, log_h_scale, tex_scale, hpr=hpr_h, bitmask=Mask.fence)
                step = self.block(f'secret_step_{i}{j}', invisible, step_pos, Vec3(0.5, 1, 3), hpr=hpr_h, hide=True)
                self.lift(f'lift_{i}{j}', invisible, step)

        # landings
        landings = [(-5.5, 6), (10.5, 6), (26.5, 6)]

        for i, (start_y, n) in enumerate(landings):
            for j in range(n):
                pos = Point3(-1.5, start_y + j, start_z)
                self.pole(f'landing_{i}{j}', barks, pos, log_h_scale, tex_scale, hpr=hpr_h)

            pos = Point3(0, start_y + n / 2 - 0.5, start_z + 0.25)
            self.block(f'secret_landing_{i}{j}', invisible, pos, Vec3(0.5, 1 * n, 3), hpr=hpr_h, hide=True)

            # poles and cloth
            y_pos = [start_y, start_y + 5]
            cloth_pts = []

            for j, (x, y) in enumerate(product(x_pos, y_pos)):
                pos = Point3(x, y, -4)
                self.pole(f'pole_{i}{j}', boards, pos, Vec3(0.5, 0.5, 10), tex_scale, hpr=(0, 0, 0), bitmask=Mask.poles)
                cloth_pts.append(Point3(x, y, 6) + self.center)

            cloth.create_cloth(i, Images.FABRIC.path, *cloth_pts, 8, 12)

        # bridge of horizontal logs; between landing_1 and landing_2
        bridges = [[-0.5, 5, 0.5, [1.0, 1.5, 2.0, 2.5, 3.0, 3.0, 2.5, 2.0, 1.5, 1.0]]]

        for i, (hor_member_y, hor_member_z, log_y, log_z) in enumerate(bridges):
            # horizontal members
            hor_member_sz = len(log_z) + 1
            for j, x in enumerate(x_pos):
                pos = Point3(x, hor_member_y, hor_member_z)
                self.pole(f'hor_member_h{i}{j}', boards, pos, Vec3(0.3, 0.3, hor_member_sz), tex_scale,
                          hpr=Vec3(0, 90, 180), bitmask=Mask.poles)
            # logs
            for j in range(len(log_z)):
                y = log_y + j
                pos = Point3(-1.5, y, log_z[j])
                log = self.pole(f'log_h{i}', barks, pos, log_h_scale, tex_scale, active=True, hpr=hpr_h, bitmask=Mask.dynamic_body)

                step_pos = Point3(0, y, pos.z + 0.25)
                step = self.block(f'secret_step_h_{i}{j}', invisible, step_pos, Vec3(0.5, 1, 3), hpr=hpr_h, hide=True, bitmask=Mask.ground)
                self.lift(f'lift_h_{i}{j}', invisible, step)

                for k, x in enumerate(x_pos):
                    from_pt = Point3(x, y, hor_member_z - 0.125) + self.center
                    to_pt = Point3(x, y, log_z[j] + 0.45) + self.center
                    rope.attach_last(f'rope_h{i}{j}{k}', Images.ROPE.path, from_pt, to_pt, log)

        # bridge of vertical logs
        bridges = [[15.5, 4, 16.5]]

        for i, (hor_member_y, hor_member_z, log_y) in enumerate(bridges):
            # handrails
            for j, x in enumerate(x_pos):
                pos = Point3(x, hor_member_y, hor_member_z)
                self.pole(f'hor_member_v{i}{j}', boards, pos, Vec3(0.3, 0.3, 11), tex_scale,
                          hpr=Vec3(0, 90, 180), bitmask=Mask.building)
            # logs
            for j in range(10):
                y = log_y + j
                pos = Point3(0, y, 1)

                if j % 2 == 0:
                    log = self.pole(f'log_v{i}', barks, pos, Vec3(1, 1, 1.9), tex_scale,
                                    hpr=(0, 90, 180), active=True, bitmask=Mask.dynamic_body)

                for k, (from_x, to_x) in enumerate(zip(x_pos, [-0.5, 0.5])):
                    from_pt = Point3(from_x, y, hor_member_z - 0.25) + self.center
                    to_pt = Point3(to_x, y + 0.5, 1) + self.center
                    rope.attach_last(f'rope_v{i}{j}{k}', Images.ROPE.path, from_pt, to_pt, log)

        self.block('secret_v', invisible, Point3(0, 21, 1), Vec3(1, 10, 1), hide=True, bitmask=Mask.ground)

        barks.set_texture(self.bark_tex)
        boards.set_texture(self.board_tex)
        self.flatten_strong()


class MazeHouse(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'mazeHouse')
        self.set_pos(center)
        # self.set_h(h)
        self.reparent_to(parent)
        self.center = center

    def make_textures(self):
        self.roofs_tex = self.texture(Images.CONCRETE)
        self.walls_tex = self.texture(Images.BRICK2)
        self.floor_tex = self.texture(Images.CONCRETE4)

    def build(self):
        self.make_textures()
        floor = NodePath('floor')
        floor.reparent_to(self)
        walls = NodePath('walls')
        walls.reparent_to(self)
        roofs = NodePath('roof')
        roofs.reparent_to(self)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)

        # room_camera
        self.block('room_jphouse', floor, Point3(0, 0, 0), Vec3(14.5, 3, 14.5), hpr=Vec3(0, 90, 0))
        self.room_camera('room_jphouse_camera', room_camera, Point3(0, 0, 9), 'x', True)

        # walls
        sy = 0.5

        # outer walls
        xy_sx_hor = [
            [(-7, 0), 14.5, False],   # left
            [(7, 0), 14.5, False],    # right
            [(-3.75, -7), 6, True],   # front left
            [(3.75, -7), 6, True],    # front right
            [(-3.75, 7), 6, True],    # rear left
            [(3.75, 7), 6, True],     # rear right
        ]
        for i, ((x, y), sx, hor) in enumerate(xy_sx_hor):
            pos = Point3(x, y, 3.5)
            scale = Vec3(sx, sy, 4)
            self.block(f'outer_walls_{i}', walls, pos, scale, horizontal=hor)

        # inner walls
        xy_sx_hor = [
            [(-1, -3.75), 6, False],
            [(2.25, -1), 6, True],
            [(1, -4.75), 4, False],
            [(3, -3), 3.5, True],
            [(3, -5.75), 2, False],
            [(5, -3.75), 2, False],
            [(-5.75, -5), 2, True],
            [(-3, -3), 4.5, False],
            [(-4.25, -3), 2, True],
            [(-5, -0.75), 4, False],
            [(-2, 1), 5.5, True],
            [(1, 0.25), 2, False],
            [(4.75, 1), 4, True],
            [(3, 2), 1.5, False],
            [(0, 3), 10.5, True],
            [(-5, 4.25), 2, False],
            [(-3.75, 5), 2, True],
            [(-1, 5.75), 2, False],
            [(2.25, 5), 6, True],
        ]

        for i, ((x, y), sx, hor) in enumerate(xy_sx_hor):
            pos = Point3(x, y, 3.25)
            scale = Vec3(sx, sy, 3.5)
            self.block(f'inner_wall1_{i}', walls, pos, scale, horizontal=hor)

        # steps
        steps_num = 3

        for i in range(steps_num):
            for j, sign in enumerate([1, -1]):
                y = (7.75 + i * 0.5) * sign
                step_pos = Point3(0, y, 1 - i)
                scale = Vec3(4, 1 + i, 1)
                block = self.block(f'step_{i}{j}', floor, step_pos, scale)

                if i > 0:
                    self.lift(f'step_lift_{i}{j}', invisible, block)

        # columns in front of the entrance and exit
        scale = Vec3(0.5, 0.5, 7)
        for i, x in enumerate([2.25, -2.25]):
            for j, y in enumerate([-10, 10]):
                pos = (x, y, 2)
                self.block(f'column_{i}{j}', walls, pos, scale)

        # roofs
        for i in range(4):
            sx = 5 - i
            sz = 3.5 - i
            z = 5.75 + 0.5 * i
            for j, y in enumerate([-8.5, 8.5]):
                self.block('roof', roofs, Point3(0, y, z), Vec3(sx, 0.5, sz), hpr=Vec3(0, 90, 0))

        floor.set_texture(self.floor_tex)
        walls.set_texture(self.walls_tex)
        roofs.set_texture(self.roofs_tex)

        self.flatten_strong()


class ElevatorTower(Buildings):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world, 'elevator_tower')
        self.set_pos(center)
        self.set_h(h)
        self.reparent_to(parent)

    def build(self):
        self._build()
        base.taskMgr.add(self.elevator.control, 'elevator_tower')
        self.flatten_strong()

    def make_textures(self):
        self.metal_tex = self.texture(Images.METALBOARD)
        self.walls_tex = self.texture(Images.BRICK2)
        self.floor_tex = self.texture(Images.IRON)

    def _build(self):
        self.make_textures()
        floor = NodePath('floor')
        floor.reparent_to(self)
        walls = NodePath('walls')
        walls.reparent_to(self)
        metal = NodePath('roof')
        metal.reparent_to(self)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self)
        invisible = NodePath('invisible')
        invisible.reparent_to(self)

        # floor
        floor_h = 2
        pos_scale = [
            [Point3(-5, 5, 0), Vec3(6, floor_h, 6)],          # left
            [Point3(5, 5, 0), Vec3(6, floor_h, 6)],           # right
            [Point3(0, -3, 0), Vec3(16, floor_h, 10)],        # front
            [Point3(0, 6.5, 0), Vec3(16, floor_h, 3)],        # back
            [Point3(0, 3.5, -0.5), Vec3(4, floor_h / 2, 3)]
        ]

        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'floor_{i}', floor, pos, scale, hpr=Vec3(0, 90, 0))

        # walls
        sz = 4
        blocks_xy_scale = [
            [[(0, 5.5), Vec3(4, 1, sz)],
             [(-5, 0), Vec3(2, 4, sz)],
             [(5, 0), Vec3(2, 4, sz)],
             [(-3, -0.25), Vec3(2, 3.5, sz)],
             [(3, -0.25), Vec3(2, 3.5, sz)],
             [(-1.9375, 1.9375), Vec3(0.125, 0.125, sz)],
             [(1.9375, 1.9375), Vec3(0.125, 0.125, sz)]],
            [[(0, 5.5), Vec3(4, 1, sz)],
             [(-4.5, 0), Vec3(3, 4, sz)],
             [(4.5, 0), Vec3(3, 4, sz)],
             [(-2.5, -0.125), Vec3(1, 3.75, sz)],
             [(2.5, -0.125), Vec3(1, 3.75, sz)],
             [(0, 0), Vec3(sz)],
             [(0, -4), Vec3(sz)]],
            [[(0, 5.5), Vec3(4, 1, sz)],
             [(-4, 0), Vec3(sz)],
             [(0, 0), Vec3(sz)],
             [(4, 0), Vec3(sz)],
             [(0, -4), Vec3(sz)]],
            [[(0, 5.5), Vec3(4, 1, sz)],
             [(-5, 1.75), Vec3(2, 0.5, sz)],
             [(-3, 1.5625), Vec3(2, 0.125, sz)],
             [(5, 1.75), Vec3(2, 0.5, sz)],
             [(3, 1.5625), Vec3(2, 0.125, sz)],
             [(-1.9375, 1.9375), Vec3(0.125, 0.125, sz)],
             [(1.9375, 1.9375), Vec3(0.125, 0.125, sz)]],
            [[(0, 4), Vec3(4, 4, 0.5)],
             [(0, 1.75), Vec3(12, 0.5, 0.5)]]
        ]

        prisms_xy_ax = [
            [[(-4, 4), sz, 90], [(-4, -4), sz, 180], [(4, -4), sz, 270], [(4, 4), sz, 360]],
            [[(-4, 4), sz, 90], [(-4, -4), sz, 180], [(4, -4), sz, 270], [(4, 4), sz, 360]],
            [[(-4, 4), sz, 90], [(-4, -4), sz, 180], [(4, -4), sz, 270], [(4, 4), sz, 360]],
            [[(-4, 4), sz, 90], [(4, 4), sz, 360]],
            [[(-4, 4), 0.5, 90], [(4, 4), 0.5, 360]]
        ]

        tex_scale = Vec2(4, 1)
        start_h = (floor_h / 2) + (sz / 2)
        roof_top = len(blocks_xy_scale) - 1

        for i, (blocks, prisms) in enumerate(zip(blocks_xy_scale, prisms_xy_ax)):
            z = start_h + i * sz
            if i == roof_top:
                z -= 1.75
            for j, ((x, y), scale) in enumerate(blocks):
                self.block(f'wall_{i}{j}', walls, Point3(x, y, z), scale)

            for j, ((x, y), scale_z, angle_x) in enumerate(prisms):
                scale = Vec3(4, 4, scale_z)
                self.triangular_prism(f'prism_{i}{j}', walls, Point3(x, y, z), Vec3(angle_x, 0, 0), scale, tex_scale)

        # falling preventions
        handrail_h = start_h + (roof_top - 1) * sz - 0.5
        size = 0.5

        handrails = [
            [(5.75, 0), Vec3(size, 4, size), 0],
            [(-5.75, -0.25), Vec3(size, 3.5, size), 0,],
            [(0, -5.75), Vec3(4, size, size), 0],
            [(-3.8, -3.8), Vec3(5.7, size, size), 135],
            [(3.8, -3.8), Vec3(5.7, size, size), -135]
        ]

        for i, ((x, y), scale, angle_x) in enumerate(handrails):
            pos = Point3(x, y, handrail_h)
            hpr = Vec3(angle_x, 0, 0)
            self.block(f'handrail_{i}', walls, pos, scale, hpr=hpr, bitmask=Mask.fence)

        poles_xy = [
            [(5.875, 1), (5.875, 0), (5.875, -1), (5.875, -1.875)],
            [(4.9, -2.9), (3.9, -3.9), (2.9, -4.9), (1.9, -5.875)],
            [(-1, -5.875), (0, -5.875), (1, -5.875)]
        ]

        for i, poles in enumerate(poles_xy):
            if i < len(poles_xy) - 1:
                poles += [(-x, y) for x, y in poles]
            for j, (x, y) in enumerate(poles):
                pos = Point3(x, y, handrail_h)
                self.pole(f'pole_{i}', metal, pos, Vec3(0.2, 0.2, 2), Vec2(2, 1), bitmask=Mask.poles)

        # doors on the 1st floor
        door_scale = Vec3(2, 0.25, 4.0)
        y = 1.75
        z = 3.0

        # left
        wall1_l = self.block('wall1_l', invisible, Point3(-3, y, z), door_scale, hide=True)
        door1_l = self.block('door1_l', metal, Point3(-1, y, z), door_scale, bitmask=Mask.door, active=True)
        # right
        wall1_r = self.block('wall1_r', invisible, Point3(3, y, z), door_scale, hide=True)
        door1_r = self.block('door1_r', metal, Point3(1, y, z), door_scale, bitmask=Mask.door, active=True)

        x = door_scale.x / 2
        slider1_1 = self.slider(door1_l, wall1_l, Point3(-x, 0, 0), Point3(x, 0, 0))
        slider1_2 = self.slider(door1_r, wall1_r, Point3(x, 0, 0), Point3(-x, 0, 0))
        self.sensor_1 = self.door_sensor('tower_sensor1', invisible, Point3(0, 1, 0.75), Vec3(4, 2, 0.5), BitMask32.bit(5),
                                         ElevatorDoorSensor, Point3(0, 3.5, 0.5), slider1_1, slider1_2)

        # doors on the 2nd floor
        z = 15
        # left
        wall2_l = self.block('wall2_l', invisible, Point3(-3, y, z), door_scale, hide=True)
        door2_l = self.block('door2_l', metal, Point3(-1, y, z), door_scale, bitmask=Mask.door, active=True)
        # right
        wall2_r = self.block('wall1_r', invisible, Point3(3, y, z), door_scale, hide=True)
        door2_r = self.block('door1_r', metal, Point3(1, y, z), door_scale, bitmask=Mask.door, active=True)

        x = door_scale.x / 2
        slider2_1 = self.slider(door2_l, wall2_l, Point3(-x, 0, 0), Point3(x, 0, 0))
        slider2_2 = self.slider(door2_r, wall2_r, Point3(x, 0, 0), Point3(-x, 0, 0))
        self.sensor_2 = self.door_sensor('tower_sensor2', invisible, Point3(0, 1, 12.75), Vec3(4, 2, 0.5), Mask.sensor,
                                         ElevatorDoorSensor, Point3(0, 3.5, 12.5), slider2_1, slider2_2)

        # elevator
        self.cage = self.block('room_elevator', floor, Point3(0, 3.5, 0.5), Vec3(4, 1, 3), hpr=Vec3(0, 90, 0))
        self.cage.node().set_kinematic(True)
        self.elevator = Elevator(self.world, self.cage, self.sensor_1, self.sensor_2)
        self.room_camera('room_elevator_camera', room_camera, Point3(0, 3.5, 16.875))

        floor.set_texture(self.floor_tex)
        walls.set_texture(self.walls_tex)
        metal.set_texture(self.metal_tex)

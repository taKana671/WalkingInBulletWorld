import math
from enum import Enum
from itertools import product, chain

from panda3d.core import Vec3, Vec2, Point3
from panda3d.core import CardMaker, Texture, TextureStage
from panda3d.core import BitMask32, TransformState
from panda3d.core import NodePath, PandaNode
from panda3d.bullet import BulletConvexHullShape, BulletBoxShape, BulletSphereShape
from panda3d.bullet import BulletTriangleMeshShape, BulletTriangleMesh
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletConeTwistConstraint

from create_geomnode import Cube, DecagonalPrism, RightTriangularPrism, Tube, RingShape, SphericalShape


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

    @property
    def path(self):
        return f'textures/{self.value}'


class Block(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparent_to(parent)
        self.model = model.copy_to(self)
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)
        end, tip = self.model.get_tight_bounds()
        self.node().add_shape(BulletBoxShape((tip - end) / 2))
        self.set_collide_mask(bitmask)


class InvisibleLift(NodePath):

    def __init__(self, name, shape, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        # self.reparent_to(parent)
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)
        self.node().add_shape(shape)
        self.set_collide_mask(bitmask)
        self.node().set_kinematic(True)
        self.hide()


class Plane(NodePath):

    def __init__(self, name, parent, model, pos):
        super().__init__(BulletRigidBodyNode(name))
        self.reparent_to(parent)
        self.model = model
        self.model.reparent_to(self)
        self.set_pos(pos)

        end, tip = self.model.get_tight_bounds()
        self.node().add_shape(BulletBoxShape((tip - end) / 2))
        self.set_collide_mask(BitMask32.bit(1))


class Convex(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparent_to(parent)
        self.model = model.copy_to(self)
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)
        shape = BulletConvexHullShape()
        shape.add_geom(self.model.node().get_geom(0))
        self.node().add_shape(shape)
        self.set_collide_mask(bitmask)


class Ring(NodePath):

    def __init__(self, name, parent, model, pos, hpr, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparent_to(parent)
        self.model = model.copy_to(self)
        mesh = BulletTriangleMesh()
        mesh.add_geom(self.model.node().get_geom(0))
        shape = BulletTriangleMeshShape(mesh, dynamic=False)

        self.node().add_shape(shape)
        self.set_collide_mask(bitmask)
        self.set_pos(pos)
        self.set_hpr(hpr)
        self.set_scale(scale)


class Sphere(NodePath):

    def __init__(self, name, parent, model, pos, scale, bitmask):
        super().__init__(BulletRigidBodyNode(name))
        self.reparent_to(parent)
        self.model = model.copy_to(self)
        end, tip = self.model.get_tight_bounds()
        size = tip - end
        self.node().add_shape(BulletSphereShape(size.z / 2))
        self.set_collide_mask(bitmask)
        self.set_pos(pos)
        self.set_scale(scale)


class Materials:

    _textures = dict()

    def __init__(self, world):
        self.world = world
        self.cube = Cube()
        self.cylinder = DecagonalPrism()
        self.right_triangle_prism = RightTriangularPrism()
        self.sphere = SphericalShape(segments=42)

    def texture(self, image):
        if image not in self._textures:
            tex = base.loader.load_texture(image.path)
            tex.set_wrap_u(Texture.WM_repeat)
            tex.set_wrap_v(Texture.WM_repeat)
            self._textures[image] = tex

        return self._textures[image]

    def block(self, name, parent, pos, scale, hpr=None, horizontal=True, active_always=False, bitmask=BitMask32.bit(1)):
        if not hpr:
            hpr = Vec3(0, 0, 0) if horizontal else Vec3(90, 0, 0)

        block = Block(name, parent, self.cube, pos, hpr, scale, bitmask)
        su = (scale.x * 2 + scale.y * 2) / 4
        sv = scale.z / 4
        block.set_tex_scale(TextureStage.get_default(), su, sv)

        if active_always:
            block.node().set_mass(1)
            block.node().set_deactivation_enabled(False)

        self.world.attach(block.node())
        return block

    def lift(self, name, parent, overlap_obj, bitmask=BitMask32.bit(4)):
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

    def knob(self, parent, left_hinge):
        x = 0.4 if left_hinge else -0.4
        pos = Point3(x, 0, 0)
        hpr = Vec3(90, 0, 0)
        scale = Vec3(1.5, 0.05, 0.05)
        knob = Block('knob', parent, self.cube, pos, hpr, scale, BitMask32.bit(1))
        knob.set_color(0, 0, 0, 1)

    def door(self, name, parent, pos, scale, static_body, hpr=None, horizontal=True, left_hinge=True):
        door = self.block(name, parent, pos, scale, hpr, horizontal, active_always=True, bitmask=BitMask32.allOn())
        self.knob(door, left_hinge)

        end, tip = door.get_tight_bounds()
        door_size = tip - end
        end, tip = static_body.get_tight_bounds()
        static_size = tip - end

        door_x = -(door_size.x / 2) if left_hinge else door_size.x / 2
        wall_x = static_size.x / 2 if left_hinge else -static_size.x / 2

        twist = BulletConeTwistConstraint(
            static_body.node(),
            door.node(),
            TransformState.make_pos(Point3(wall_x, static_size.y / 2, 0)),
            TransformState.make_pos(Point3(door_x, door_size.y / 2, 0)),
        )

        twist.setLimit(60, 60, 0, softness=0.1, bias=0.1, relaxation=8.0)
        self.world.attach_constraint(twist)

    def pole(self, name, parent, pos, scale, tex_scale, hpr=None, vertical=True, bitmask=BitMask32.bit(3), hide=False):
        if not hpr:
            hpr = Vec3(0, 0, 0) if vertical else Vec3(0, 90, 0)

        pole = Convex(name, parent, self.cylinder, pos, hpr, scale, bitmask)
        pole.set_tex_scale(TextureStage.get_default(), tex_scale)

        if hide:
            pole.hide()

        self.world.attach(pole.node())
        return pole

    def triangular_prism(self, name, parent, pos, hpr, scale, tex_scale=None, bitmask=BitMask32.bit(1), hide=False):
        prism = Convex(name, parent, self.right_triangle_prism, pos, hpr, scale, bitmask)

        if tex_scale:
            prism.set_tex_scale(TextureStage.get_default(), tex_scale)
        if hide:
            prism.hide()

        self.world.attach(prism.node())
        return prism

    def room_camera(self, name, parent, pos):
        room_camera = self.block(name, parent, pos, Vec3(0.25, 0.25, 0.25))
        room_camera.set_color((0, 0, 0, 1))
        return room_camera

    def plane(self, name, parent, pos, rows, cols, size=2):
        model = NodePath(PandaNode(f'{name}Model'))
        card = CardMaker('card')
        half = size / 2
        card.set_frame(-half, half, -half, half)

        for r in range(rows):
            for c in range(cols):
                g = model.attach_new_node(card.generate())
                g.setP(-90)
                x = (c - cols / 2) * size
                y = (r - rows / 2) * size
                g.set_pos(x, y, 0)

        plane = Plane(name, parent, model, pos)
        self.world.attach(plane.node())
        return plane

    def point_on_circumference(self, angle, radius):
        rad = math.radians(angle)
        x = math.cos(rad) * radius
        y = math.sin(rad) * radius
        return x, y

    def tube(self, name, parent, geomnode, pos, scale, hpr=None, horizontal=True):
        if not hpr:
            hpr = Vec3(0, 90, 0) if horizontal else Vec3(90, 0, 0)

        tube = Ring(name, parent, geomnode, pos, hpr, scale, BitMask32.allOn())
        self.world.attach(tube.node())
        return tube

    def ring_shape(self, name, parent, geomnode, pos, scale=Vec3(1), hpr=None, hor=True, tex_scale=None, bitmask=BitMask32.all_on()):
        if not hpr:
            hpr = Vec3(0, 90, 0) if hor else Vec3(90, 0, 0)

        ring = Ring(name, parent, geomnode, pos, hpr, scale, bitmask)
        if tex_scale:
            ring.set_tex_scale(TextureStage.get_default(), tex_scale)

        self.world.attach(ring.node())
        return ring

    def sphere_shape(self, name, parent, pos, scale, bitmask=BitMask32.bit(1)):
        sphere = Sphere(name, parent, self.sphere, pos, scale, bitmask)
        self.world.attach(sphere.node())
        return sphere


class StoneHouse(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('stoneHouse'))
        self.house.reparent_to(parent)
        self.house.set_pos(center)
        self.house.set_h(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.FIELD_STONE)    # for walls
        self.floor_tex = self.texture(Images.IRON)          # for floors, steps and roof
        self.door_tex = self.texture(Images.BOARD)          # for doors
        self.column_tex = self.texture(Images.CONCRETE)     # for columns
        self.fence_tex = self.texture(Images.METALBOARD)

    def build(self):
        self.make_textures()
        walls = NodePath('walls')
        walls.reparent_to(self.house)
        floors = NodePath('floors')
        floors.reparent_to(self.house)
        doors = NodePath('doors')
        doors.reparent_to(self.house)
        columns = NodePath('columns')
        columns.reparent_to(self.house)
        fences = NodePath('fences')
        fences.reparent_to(self.house)
        invisible = NodePath('invisible')
        invisible.reparent_to(self.house)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self.house)

        # columns
        gen = (Point3(x, y, -3) for x, y in product((-15, 15), (-11, 11)))
        for i, pos in enumerate(gen):
            self.pole(f'column_{i}', columns, pos, Vec3(1, 1, 9), Vec2(1, 1))

        # the 1st floor outside
        pos_scale = [
            [Point3(-11, 0, 0), Vec3(10, 1, 24)],          # left
            [Point3(11, 0, 0), Vec3(10, 1, 24)],           # right
            [Point3(0, -10, 0), Vec3(12, 1, 4)],           # front
            [Point3(0, 10, 0), Vec3(12, 1, 4)]             # back
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'floor1_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0))

        # room and room camera on the 1st floor
        self.block('room1', floors, Point3(0, 0, 0), Vec3(12, 1, 16), hpr=Vec3(0, 90, 0))
        self.room_camera('room1_camera', room_camera, Point3(0, 0, 6.25))

        # right and left walls on the 1st floor
        pos_scale = [
            [Point3(-5.75, 0, 3.5), Vec3(16, 0.5, 6)],          # left
            [Point3(5.75, 0, 1.5), Vec3(16, 0.5, 2)],           # right under
            [Point3(5.75, 3, 3.5), Vec3(10, 0.5, 2)],           # right middle back
            [Point3(5.75, -7, 3.5), Vec3(2, 0.5, 2)],           # right front
            [Point3(5.75, 0, 5.5), Vec3(16, 0.5, 2)],           # right top
            [Point3(-13.75, -4.25, 7), Vec3(8.5, 0.5, 13)]      # left side of the steps
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall1_side{i}', walls, pos, scale, horizontal=False)

        # front and rear walls on the 1st floor
        pos_scale = [
            [Point3(0, 8.25, 3.5), Vec3(12, 0.5, 6)],           # rear
            [Point3(0, -8.25, 5.5), Vec3(12, 0.5, 2)],          # front top
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall1_fr{i}', walls, pos, scale)

        wall1_l = self.block('wall1_fl', walls, Point3(-4, -8.25, 2.5), Vec3(4, 0.5, 4))    # front left
        wall1_r = self.block('wall1_fr', walls, Point3(4, -8.25, 2.5), Vec3(4, 0.5, 4))     # front right

        # 2nd floor
        pos_scale = [
            [Point3(4, -4.25, 6.75), Vec3(20, 0.5, 8.5)],
            [Point3(-9.75, -1, 6.75), Vec3(7.5, 0.5, 2)]
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'floor2_{i}', floors, pos, scale, hpr=Vec3(0, 90, 0))

        # room and room camera on the 2nd floor
        self.block('room2', floors, Point3(-4, 4.25, 6.75), Vec3(20, 0.5, 8.5), hpr=Vec3(0, 90, 0))
        self.room_camera('room2_camera', room_camera, Point3(-10, 4, 13))

        # balcony fence
        pos_scale_hpr = [
            [Point3(4, -8.25, 7.5), Vec3(0.5, 1, 20), Vec3(0, 90, 90)],
            [Point3(-5.75, -5, 7.5), Vec3(0.5, 1, 6), Vec3(0, 90, 0)],
            [Point3(13.75, -4, 7.5), Vec3(0.5, 1, 8), Vec3(0, 90, 0)],
            [Point3(10, 0.25, 7.25), Vec3(0.5, 1.5, 8), Vec3(0, 90, 90)]
        ]
        for i, (pos, scale, hpr) in enumerate(pos_scale_hpr):
            self.block(f'balcony_{i}', floors, pos, scale, hpr=hpr)

        # left and right walls on the 2nd floor
        pos_scale = [
            [Point3(-13.75, 4, 8), Vec3(8, 0.5, 2)],         # left
            [Point3(-13.75, 1.5, 10), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 6.5, 10), Vec3(3, 0.5, 2)],      # left
            [Point3(-13.75, 4, 12), Vec3(8, 0.5, 2)],        # left
            [Point3(5.75, 4.25, 10), Vec3(7.5, 0.5, 6)]      # right
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall2_side{i}', walls, pos, scale, horizontal=False)

        # front and rear walls on the 2nd floor
        wall2_l = self.block('wall2_l', walls, Point3(-12.5, 0.25, 9), Vec3(2, 0.5, 4))

        pos_scale = [
            [Point3(-4, 8.25, 10), Vec3(20, 0.5, 6)],        # rear
            [Point3(-7.25, 0.25, 9), Vec3(2.5, 0.5, 4)],     # front
            [Point3(-9.75, 0.25, 12), Vec3(7.5, 0.5, 2)],    # front
            [Point3(0, 0.25, 8), Vec3(12, 0.5, 2)],          # front
            [Point3(-4, 0.25, 10), Vec3(4, 0.5, 2)],         # front
            [Point3(4, 0.25, 10), Vec3(4, 0.5, 2)],          # front
            [Point3(0, 0.25, 12), Vec3(12, 0.5, 2)]          # front
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall2_fr{i}', walls, pos, scale)

        # roof
        self.block('roof', floors, Point3(-4, 4.25, 13.25), Vec3(20, 8.5, 0.5))

        # steps that leads to the 2nd floor
        for i in range(6):
            pos = Point3(-9.75, -7.5 + i, 1 + i)
            block = self.block(f'step_2{i}', floors, pos, Vec3(7.5, 1, 1), hpr=Vec3(0, 90, 0))
            self.lift(f'lift_2{i}', invisible, block)

        # steps that leade to the 1st floor
        x_diffs = [15.9, -15.9]

        for i in range(5):
            pos = Point3(0, 12.5 + i, 0 - i)
            block = self.block(f'step_1{i}', floors, pos, Vec3(32, 1, 1), hpr=Vec3(0, 90, 0))
            if i > 0:
                self.lift(f'lift_1{i}', invisible, block)

            # falling preventions
            for j, x_diff in enumerate(x_diffs):
                f_pos = pos + Vec3(x_diff, 0, 1.5)
                self.block(f'step_fence_{i}{j}', fences, f_pos, Vec3(0.15, 0.15, 2.1), bitmask=BitMask32.bit(3))

            # handrails
            if i == 2:
                for k, x_diff in enumerate(x_diffs):
                    rail_pos = pos + Vec3(x_diff, 0, 2.5)
                    self.block(
                        f'handrail_{i}{k}', fences, rail_pos, Vec3(0.15, 0.15, 5.7), Vec3(0, 45, 0), bitmask=BitMask32.bit(3)
                    )

        # slope for the 1st step
        self.triangular_prism('hidden_slope', invisible, Point3(-9.75, -8.5, 1), Vec3(-90, 90, 0), Vec3(1, 1, 7.5), hide=True)

        # doors
        doors_data = [
            [Point3(-1, -8.25, 2.5), Vec3(2, 0.5, 4), wall1_l, True],    # left door of the room on the 1st floor
            [Point3(1, -8.25, 2.5), Vec3(2, 0.5, 4), wall1_r, False],    # left door of the room on the 1st floor
            [Point3(-10, 0.25, 9), Vec3(3, 0.5, 4), wall2_l, True]       # foor ofr the room on the 2nd floor
        ]
        for i, (pos, scale, body, hinge) in enumerate(doors_data):
            self.door(f'door_{i}', doors, pos, scale, body, horizontal=True, left_hinge=hinge)

        doors.set_texture(self.door_tex)
        walls.set_texture(self.wall_tex)
        floors.set_texture(self.floor_tex)
        columns.set_texture(self.column_tex)
        fences.set_texture(self.fence_tex)
        # Child nodes of the self.house are combined together into one node
        # (maybe into the node lastly parented to self.house?).
        self.house.flatten_strong()


class BrickHouse(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.house = NodePath(PandaNode('brickHouse'))
        self.house.reparent_to(parent)
        self.house.set_pos(center)
        self.house.set_h(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.BRICK)      # for walls
        self.floor_tex = self.texture(Images.CONCRETE)  # for floors
        self.roof_tex = self.texture(Images.IRON)       # for roofs
        self.door_tex = self.texture(Images.BOARD)      # for doors

    def build(self):
        self.make_textures()
        floors = NodePath('foundation')
        floors.reparent_to(self.house)
        walls = NodePath('wall')
        walls.reparent_to(self.house)
        roofs = NodePath('roof')
        roofs.reparent_to(self.house)
        doors = NodePath('door')
        doors.reparent_to(self.house)
        invisible = NodePath('invisible')
        invisible.reparent_to(self.house)
        room_camera = NodePath('room_camera')
        room_camera.reparent_to(self.house)

        # room floors
        pos_scale = [
            [Point3(0, 0, 0), Vec3(13, 9, 3)],     # big room
            [Point3(3, -6.5, 0), Vec3(7, 4, 3)],   # small room
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'room_brick{i}', floors, pos, scale)

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

        # rear and front walls
        wall1_l = self.block('wall1_l', walls, Point3(1, -8.25, 3.25), Vec3(2, 0.5, 3.5))

        pos_scale = [
            [Point3(0, 4.25, 5.5), Vec3(12, 0.5, 8)],        # rear
            [Point3(5, -8.25, 3.25), Vec3(2, 0.5, 3.5)],     # front right
            [Point3(3, -8.25, 5.25), Vec3(6, 0.5, 0.5)],     # front_top
            [Point3(-1.5, -4.25, 5.5), Vec3(2, 0.5, 8)],     # back room front right
            [Point3(-5.25, -4.25, 5.5), Vec3(1.5, 0.5, 8)],  # back room front left
            [Point3(-3.5, -4.25, 3.0), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(-3.5, -4.25, 8.0), Vec3(2, 0.5, 3)],     # back room front under
            [Point3(3, -4.25, 7.5), Vec3(7, 0.5, 4)],        # back room front
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall1_fr{i}', walls, pos, scale)

        # side walls
        pos_scale = [
            [Point3(-0.25, -6.25, 3.5), Vec3(4.5, 0.5, 4)],    # left
            [Point3(-6.25, -3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(-6.25, 0, 3.0), Vec3(3, 0.5, 3)],
            [Point3(-6.25, 0, 8.0), Vec3(3, 0.5, 3)],
            [Point3(6.25, -6.25, 3.5), Vec3(4.5, 0.5, 4)],     # right
            [Point3(6.25, -2.75, 5.5), Vec3(2.5, 0.5, 8)],
            [Point3(6.25, 3, 5.5), Vec3(3, 0.5, 8)],
            [Point3(6.25, 0, 3.0), Vec3(3, 0.5, 3)],
            [Point3(6.25, 0, 8.0), Vec3(3, 0.5, 3)]
        ]
        for i, (pos, scale) in enumerate(pos_scale):
            self.block(f'wall1_side{i}', walls, pos, scale, horizontal=False)

        # roofs
        pos_scale = [
            ((Point3(3, -6.5, 5.75 + 0.25 * i), Vec3(7 - i, 4 - i, 0.5)) for i in range(2)),  # small room
            ((Point3(0, 0, 9.75 + 0.25 * i), Vec3(13 - i, 9 - i, 0.5)) for i in range(2)),    # big room
        ]
        for i, (pos, scale) in enumerate(chain(*pos_scale)):
            self.block(f'roof_{i}', roofs, pos, scale)

        # doors
        self.door('door_1', doors, Point3(3, -8.25, 3.25), Vec3(2, 0.5, 3.5), wall1_l)

        floors.set_texture(self.floor_tex)
        walls.set_texture(self.wall_tex)
        roofs.set_texture(self.roof_tex)
        doors.set_texture(self.door_tex)
        self.house.flatten_strong()


class Terrace(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.terrace = NodePath(PandaNode('terrace'))
        self.terrace.reparent_to(parent)
        self.terrace.set_pos(center)
        self.terrace.set_h(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.LAYINGBROCK)    # for walls
        self.floor_tex = self.texture(Images.COBBLESTONES)  # for floor
        self.roof_tex = self.texture(Images.IRON)           # for roofs
        self.steps_tex = self.texture(Images.METALBOARD)    # for steps

    def build(self):
        self.make_textures()
        floors = NodePath('floors')
        floors.reparent_to(self.terrace)
        walls = NodePath('walls')
        walls.reparent_to(self.terrace)
        roofs = NodePath('roofs')
        roofs.reparent_to(self.terrace)
        steps = NodePath('steps')
        steps.reparent_to(self.terrace)
        lifts = NodePath('lifts')
        lifts.reparent_to(self.terrace)

        # the 1st floor
        self.block('floor1', floors, Point3(0, 0, 0), Vec3(16, 0.5, 12), hpr=Vec3(0, 90, 0))

        # walls
        self.block('wall1_r', walls, Point3(-5.5, 5.75, 3.25), Vec3(5, 0.5, 6))                       # rear
        self.block('wall1_s', walls, Point3(-7.75, 3.25, 3.25), Vec3(4.5, 0.5, 6), horizontal=False)  # side

        # columns
        gen = (Point3(x, y, 2) for x, y in [(-7.5, -5.5), (7.5, -5.5), (7.5, 5.5)])
        for i, pos in enumerate(gen):
            self.pole(f'column_{i}', roofs, pos, Vec3(0.25, 0.25, 16), Vec2(1, 3))

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
            self.block(f'prevention_{i}', roofs, pos, scale, horizontal=hor)

        # spiral center pole
        center = Point3(9, 1.5, 3.5)
        self.pole('center_pole', roofs, center, Vec3(1, 1, 16), Vec2(1, 3), bitmask=BitMask32.bit(1))
        sphere_pos = center + Vec3(0, 0, 5.6)
        self.sphere_shape('pole_sphere', roofs, sphere_pos, Vec3(0.6))

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
                self.block(f'spiral_fence_{i}{j}', steps, f_pos, f_scale, bitmask=BitMask32.bit(3))

        # handrail of spiral staircase
        pos = center - Vec3(0, 0, 0.5)
        hpr = Vec3(-101, 0, 0)
        geomnode = RingShape(segs_rcnt=14, slope=0.5, ring_radius=4.3, section_radius=0.15)
        self.ring_shape('handrail', steps, geomnode, pos, hpr=hpr, bitmask=BitMask32.bit(3))

        # slope of the 1st step
        self.triangular_prism(
            'hidden_slope', lifts, Point3(7.75, -1, 0.5), Vec3(180, 90, 0), Vec3(0.5, 0.5, 4), hide=True
        )
        # entrance slope
        self.triangular_prism(
            'entrance_slope', floors, Point3(-9.5, -2.5, 0), Vec3(180, 90, 0), Vec3(3, 0.5, 7), tex_scale=Vec2(3, 2)
        )

        walls.set_texture(self.wall_tex)
        floors.set_texture(self.floor_tex)
        roofs.set_texture(self.roof_tex)
        steps.set_texture(self.steps_tex)
        self.terrace.flatten_strong()


class Observatory(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.observatory = NodePath(PandaNode('observatory'))
        self.observatory.reparent_to(parent)
        self.observatory.set_pos(center)
        self.observatory.set_h(h)

    def make_textures(self):
        self.steps_tex = self.texture(Images.METALBOARD)
        self.landing_tex = self.texture(Images.CONCRETE2)
        self.posts_tex = self.texture(Images.IRON)

    def build(self):
        self.make_textures()
        steps = NodePath('steps')
        steps.reparent_to(self.observatory)
        landings = NodePath('landings')
        landings.reparent_to(self.observatory)
        posts = NodePath('posts')
        posts.reparent_to(self.observatory)
        invisible = NodePath('invisible')
        invisible.reparent_to(self.observatory)

        # spiral center pole
        center = Point3(10, 0, 9)
        self.pole('spiral_center', posts, center, Vec3(1, 1, 40), Vec2(1, 3), bitmask=BitMask32.bit(1))
        sphere_pos = center + Vec3(0, 0, 12.7)
        self.sphere_shape('pole_sphere', posts, sphere_pos, Vec3(0.6))

        # spiral staircase
        steps_num = 19                # the number of steps
        s_scale = Vec3(4, 2.5, 0.5)   # scale of a triangular prism

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
                self.block(f'spiral_fence_{i}{j}', steps, f_pos, f_scale, bitmask=BitMask32.bit(3))

        # handrail of spiral staircase
        pos = center - Vec3(0, 0, 6)
        hpr = Vec3(-101, 0, 0)
        geomnode = RingShape(segs_rcnt=38, slope=0.5, ring_radius=4.3, section_radius=0.15)
        self.ring_shape('handrail', steps, geomnode, pos, hpr=hpr, bitmask=BitMask32.bit(3))

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

        # posts supporting landings
        tex_scale = Vec2(1, 3)
        z_length = {
            1: (6, 30),
            2: (5, 24),
            3: (4, 18),
            4: (3, 12),
            5: (1.5, 6),
        }
        for key, (z, length) in z_length.items():
            landing_pos = landing_positions[key]
            support_pos = Point3(landing_pos.x, landing_pos.y, z)
            scale = Vec3(0.2, 0.2, length)
            self.pole(f'support_{i}', posts, support_pos, scale, tex_scale)

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

        # a slope for the lowest step
        self.triangular_prism('hidden_slope', invisible, Point3(-15.75, 2.5, 1.25), Vec3(180, 90, 0), Vec3(1, 1, 4), hide=True)

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
                self.ring_shape(f'landing_fence_{k}{i}', steps, geomnode, fence_pos, hpr=hpr, bitmask=BitMask32.bit(3))

        steps.set_texture(self.steps_tex)
        landings.set_texture(self.landing_tex)
        posts.set_texture(self.posts_tex)
        self.observatory.flatten_strong()


class Bridge(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.bridge = NodePath(PandaNode('bridge'))
        self.bridge.reparent_to(parent)
        self.bridge.set_pos(center)
        self.bridge.set_h(h)

    def make_textures(self):
        self.bridge_tex = self.texture(Images.IRON)         # for bridge girder
        self.column_tex = self.texture(Images.CONCRETE)     # for columns
        self.fence_tex = self.texture(Images.METALBOARD)    # for fences

    def build(self):
        self.make_textures()
        girders = NodePath('girders')
        girders.reparent_to(self.bridge)
        columns = NodePath('columns')
        columns.reparent_to(self.bridge)
        fences = NodePath('fences')
        fences.reparent_to(self.bridge)
        lifts = NodePath('lift')
        lifts.reparent_to(self.bridge)

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
            pos = Point3(x, y, -3)
            self.pole(f'column_{i}', columns, pos, Vec3(1, 1, 9), Vec2(1, 1))

        # steps
        diffs = [1.9, -1.9]

        for i in range(5):
            pos = Point3(0, -20.5 - i, -1 - i)
            block = self.block(f'step_{i}', girders, pos, Vec3(4, 1, 1))
            self.lift(f'lift_{i}', lifts, block)

            # falling preventions
            for j, diff in enumerate(diffs):
                f_pos = pos + Vec3(diff, 0, 1.5)
                self.block(f'step_fence_{i}{j}', fences, f_pos, Vec3(0.15, 0.15, 2.1), bitmask=BitMask32.bit(3))

            # handrails
            if i == 2:
                for k, diff_x in enumerate(diffs):
                    rail_pos = pos + Vec3(diff_x, 0, 2.5)
                    self.block(
                        f'handrail_{i}{k}', fences, rail_pos, Vec3(0.15, 0.15, 5.7), Vec3(0, -45, 0), bitmask=BitMask32.bit(3)
                    )

        # bridge rails
        pos_scale = [
            [((x, y) for x in (-1.875, 1.875) for y in (-11.875, 11.875)), Vec3(16.25, 0.25, 0.5)],
            [((x, 0) for x in (3.875, -3.875)), Vec3(8.0, 0.25, 0.5)],
            [((x, y) for x in (-2.875, 2.875) for y in (3.875, -3.875)), Vec3(0.25, 1.75, 0.5)]
        ]
        for i, (gen, scale) in enumerate(pos_scale):
            for j, (x, y) in enumerate(gen):
                pos = Point3(x, y, 1.75)
                self.block(
                    f'bridge_rail_{i}{j}', girders, pos, scale, horizontal=False, bitmask=BitMask32.bit(3)
                )
        pos_xy = [
            ((x, y + i) for i in range(17) for x in (1.875, -1.875) for y in (3.875, -19.875)),
            ((x, y) for x in (3.875, -3.875) for y in (3.875, -3.875))
        ]
        for i, (x, y) in enumerate(chain(*pos_xy)):
            pos = Point3(x, y, 1)
            self.block(
                f'rail_block_{i}', girders, pos, Vec3(0.25, 0.25, 1), horizontal=False, bitmask=BitMask32.bit(3)
            )

        girders.set_texture(self.bridge_tex)
        columns.set_texture(self.column_tex)
        fences.set_texture(self.fence_tex)
        self.bridge.flatten_strong()


class Tunnel(Materials):

    def __init__(self, world, parent, center, h=0):
        super().__init__(world)
        self.tunnel = NodePath(PandaNode('tunnel'))
        self.tunnel.reparent_to(parent)
        self.tunnel.set_pos(center)
        self.tunnel.set_h(h)

    def make_textures(self):
        self.wall_tex = self.texture(Images.IRON)           # for tunnel
        self.metal_tex = self.texture(Images.METALBOARD)
        self.pedestal_tex = self.texture(Images.FIELD_STONE)

    def build(self):
        self.make_textures()
        walls = NodePath('wall')
        walls.reparent_to(self.tunnel)
        metal = NodePath('rings')
        metal.reparent_to(self.tunnel)
        pedestals = NodePath('pedestals')
        pedestals.reparent_to(self.tunnel)
        invisible = NodePath('invisible')
        invisible.reparent_to(self.tunnel)

        # tunnel
        geomnode = Tube(height=20)
        self.tube('tunnel', walls, geomnode, Point3(0, 0, 0), Vec3(4, 4, 4))

        # both ends of the tunnel
        positions = [Point3(0, 0, 0), Point3(0, -80, 0)]
        geomnode = RingShape(ring_radius=0.5, section_radius=0.05)

        for i, pos in enumerate(positions):
            self.ring_shape(f'edge_{i}', walls, geomnode, pos, scale=Vec3(4), tex_scale=Vec2(2))

        # steps
        steps_num = 4
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
                    self.block(f'fence_{i}{j}', metal, f_pos, Vec3(0.15, 0.15, 2), bitmask=BitMask32.bit(3))

                # invisible slope of the lowest step
                if i == steps_num - 1:
                    slope_y = pos.y + 1 if start_y > 0 else pos.y - 1
                    hpr = Vec3(0, 90, 90) if start_y > 0 else Vec3(0, 180, 90)
                    pos.y = slope_y
                    self.triangular_prism('hidden_slope', invisible, pos, hpr, Vec3(1, 1, 4), hide=True)

        # handrails
        for x, y in ((x, y) for y in [2.3, -82.3] for x in diffs):
            hpr = (0, 45, 0) if y > 0 else (0, -45, 0)
            pos = Point3(x, y, -1.63)
            self.block(f'handrail_{i}{j}', metal, pos, Vec3(0.15, 0.15, 4.5), hpr=hpr, bitmask=BitMask32.bit(3))

        # rings supporting tunnel
        geomnode = RingShape(ring_radius=0.8, section_radius=0.1)

        for i in range(5):
            y = -0.7 - i * 19.65
            ring_pos = Point3(0, y, 0)
            self.ring_shape(f'ring_{i}', metal, geomnode, ring_pos, scale=Vec3(5), tex_scale=Vec2(2, 4))

            # culumn supporting ring
            col_pos = Point3(0, y, -7.3)
            self.block(f'column_{i}', pedestals, col_pos, Vec3(2, 2, 6))

            # poles supporting ring
            for j, (x, z) in enumerate([(0, 3), (0, -3), (3, 0), (-3, 0)]):
                pole_pos = Point3(x, y, z)
                hpr = Vec3(0, 0, 0) if x == 0 else Vec3(90, 90, 0)
                self.pole(f'pole_{i}{j}', metal, pole_pos, Vec3(0.5, 0.5, 3), Vec2(1, 1), hpr=hpr)

        walls.set_texture(self.wall_tex)
        metal.set_texture(self.metal_tex)
        pedestals.set_texture(self.pedestal_tex)
        self.tunnel.flatten_strong()
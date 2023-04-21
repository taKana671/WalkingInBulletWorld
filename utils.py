from panda3d.core import LineSegs, NodePath


def create_line_node(from_pos, to_pos, color, thickness=2.0):
    """Return a NodePath for line node.
       Args:
            from_pos (Vec3): the point where a line starts;
            to_pos (Vec3): the point where a line ends;
            color (LColor): the line color;
            thickness (float): the line thickness;
    """
    lines = LineSegs()
    lines.set_color(color)
    lines.move_to(from_pos)
    lines.draw_to(to_pos)
    lines.set_thickness(thickness)
    node = lines.create()
    return NodePath(node)


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance
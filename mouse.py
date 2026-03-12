import math
import pygame
import sys
import random
import pymunk
from queue import Queue


UPDATE_MS = 10
CAMERA_SPEED = 5

class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    @classmethod
    def from_angle(cls, rot: float, offset: float):
        return cls(
            math.cos(rot) * offset,
            math.sin(rot) * offset
        )

    def copy(self):
        return Point(self.x, self.y)

    def _coerce(self, other):
        if isinstance(other, Point):
            return other.x, other.y
        if isinstance(other, (int, float)):
            return other, other
        return NotImplemented

    def __add__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(self.x + ox, self.y + oy)

    def __sub__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(self.x - ox, self.y - oy)

    def __mul__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(self.x * ox, self.y * oy)

    def __truediv__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(self.x / ox, self.y / oy)

    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(ox - self.x, oy - self.y)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __rtruediv__(self, other):
        vals = self._coerce(other)
        if vals is NotImplemented:
            return NotImplemented
        ox, oy = vals
        return Point(ox / self.x, oy / self.y)

def get_distance(p1: Point, p2: Point):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.sqrt(dx * dx + dy * dy)

def get_direction(p1: Point, p2: Point):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.atan2(dy, dx)

class Polygon:
    def __init__(self, global_position, rot: float, size: float, points, color):
        self.__global_position = global_position.copy()
        self.__rot = rot
        self.__size = size
        self.__points = points
        self.__color = color

    # ----- global_position -----
    def get_global_position(self):
        return self.__global_position

    def set_global_position(self, pos):
        self.__global_position = pos.copy()

    # ----- rotation -----
    def get_rotation(self):
        return self.__rot

    def set_rotation(self, rot: float):
        self.__rot = rot

    # ----- size -----
    def get_size(self):
        return self.__size

    def set_size(self, size: float):
        self.__size = size

    # ----- points -----
    def get_points(self):
        return self.__points

    def set_points(self, points):
        self.__points = points

    # ----- color -----
    def get_color(self):
        return self.__color

    def set_color(self, color):
        self.__color = color

    def add_to_obstacle_container(self, obstacle_container):
        obstacle_container.add_obstacle(self)

    def draw(self, surface, camera_position, width=0):
        transformed = []

        cos_r = math.cos(self.__rot)
        sin_r = math.sin(self.__rot)

        for p in self.__points:
            x = p.x * self.__size
            y = p.y * self.__size

            xr = x * cos_r - y * sin_r
            yr = x * sin_r + y * cos_r

            xr += self.__global_position.x - camera_position.x
            yr += self.__global_position.y - camera_position.y

            transformed.append((xr, yr))

        pygame.draw.polygon(surface, self.__color, transformed, width)


    def compute_aabb(self):
        cos_r = math.cos(self.__rot)
        sin_r = math.sin(self.__rot)

        xs = []
        ys = []

        for p in self.__points:
            x = p.x * self.__size
            y = p.y * self.__size

            xr = x * cos_r - y * sin_r
            yr = x * sin_r + y * cos_r

            xs.append(xr + self.__global_position.x)
            ys.append(yr + self.__global_position.y)

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        return (min_x, min_y, max_x, max_y)
    
class Segment:
    def __init__(self, start: Point, end: Point, color=(255, 255, 255), width: int = 1):
        self.__start = start.copy()
        self.__end = end.copy()
        self.__color = color
        self.__width = width

    # ----- start -----
    def get_start(self):
        return self.__start.copy()

    def set_start(self, p: Point):
        self.__start = p.copy()

    # ----- end -----
    def get_end(self):
        return self.__end.copy()

    def set_end(self, p: Point):
        self.__end = p.copy()

    # ----- color -----
    def get_color(self):
        return self.__color

    def set_color(self, color):
        self.__color = color

    # ----- width -----
    def get_width(self):
        return self.__width

    def set_width(self, width: int):
        self.__width = width

    def draw(self, surface, camera_position):
        x1 = self.__start.x - camera_position.x
        y1 = self.__start.y - camera_position.y

        x2 = self.__end.x - camera_position.x
        y2 = self.__end.y - camera_position.y

        pygame.draw.line(
            surface,
            self.__color,
            (x1, y1),
            (x2, y2),
            self.__width
        )

    def shave_start(self, distance: float) -> bool:
        dx = self.__end.x - self.__start.x
        dy = self.__end.y - self.__start.y

        length = math.hypot(dx, dy)
        if length <= 0 or distance >= length:
            return False

        t = distance / length

        self.__start = Point(
            self.__start.x + dx * t,
            self.__start.y + dy * t
        )

        return True


    def shave_end(self, distance: float) -> bool:
        dx = self.__end.x - self.__start.x
        dy = self.__end.y - self.__start.y

        length = math.hypot(dx, dy)
        if length <= 0 or distance >= length:
            return False

        t = distance / length

        self.__end = Point(
            self.__end.x - dx * t,
            self.__end.y - dy * t
        )

        return True

    def to_polygon(self):
        dx = self.__end.x - self.__start.x
        dy = self.__end.y - self.__start.y

        length = math.hypot(dx, dy)
        rot = math.atan2(dy, dx)

        center = Point(
            (self.__start.x + self.__end.x) * 0.5,
            (self.__start.y + self.__end.y) * 0.5
        )

        half_length = length * 0.5
        half_thickness = self.__width * 0.5

        return Polygon(
            global_position=center,
            rot=rot,
            size=1.0,
            points=[
                Point(-half_length, -half_thickness),
                Point( half_length, -half_thickness),
                Point( half_length,  half_thickness),
                Point(-half_length,  half_thickness),
            ],
            color=self.__color
        )

def generate_random_map(width, height, object_count, obstacle_container, seed):
    rng = random.Random(seed)

    half_w = width * 0.5
    half_h = height * 0.5

    for _ in range(object_count):
        shape_type = rng.choice(["square", "triangle"])

        x = rng.uniform(-half_w, half_w)
        y = rng.uniform(-half_h, half_h)

        rot = rng.uniform(0.0, 2.0 * math.pi)
        size = rng.uniform(10.0, 50.0)

        color = (
            rng.randint(80, 255),
            rng.randint(80, 255),
            rng.randint(80, 255)
        )

        if shape_type == "square":
            poly = Polygon(
                global_position=Point(x, y),
                rot=rot,
                size=size,
                points=[
                    Point(-2, -1),
                    Point(2, -1),
                    Point(2, 1),
                    Point(-2, 1)
                ],
                color=color
            )
        else:
            poly = Polygon(
                global_position=Point(x, y),
                rot=rot,
                size=size,
                points=[
                    Point(-1, -1),
                    Point(-1, 1),
                    Point(2, 0)
                ],
                color=color
            )

        poly.add_to_obstacle_container(obstacle_container)

class ObstacleContainer:
    def __init__(self):
        self.__space = pymunk.Space()
        self.__shape_to_polygon = {}
        self.__polygon_to_shape = {}

    def add_obstacle(self, polygon):
        pos = polygon.get_global_position()
        rot = polygon.get_rotation()
        size = polygon.get_size()

        cos_r = math.cos(rot)
        sin_r = math.sin(rot)

        verts = []
        for p in polygon.get_points():
            x = p.x * size
            y = p.y * size

            xr = x * cos_r - y * sin_r
            yr = x * sin_r + y * cos_r

            verts.append((xr + pos.x, yr + pos.y))

        body = self.__space.static_body
        shape = pymunk.Poly(body, verts)

        self.__space.add(shape)
        self.__shape_to_polygon[shape] = polygon
        self.__polygon_to_shape[polygon] = shape

        return shape

    def remove_obstacle(self, polygon):
        shape = self.__polygon_to_shape[polygon]

        self.__space.remove(shape)
        del self.__shape_to_polygon[shape]
        del self.__polygon_to_shape[polygon]

    def query_box(self, min_x, min_y, max_x, max_y):
        bb = pymunk.BB(min_x, min_y, max_x, max_y)
        shapes = self.__space.bb_query(bb, pymunk.ShapeFilter())

        result = []
        seen = set()

        for shape in shapes:
            poly = self.__shape_to_polygon.get(shape)
            if poly is not None and poly not in seen:
                seen.add(poly)
                result.append(poly)

        return result

    def get_obstacles_on_screen(self, game):
        camera = game.get_camera_position()
        screen_size = game.get_screen_size()

        min_x = camera.x
        min_y = camera.y
        max_x = camera.x + screen_size.x
        max_y = camera.y + screen_size.y

        return self.query_box(min_x, min_y, max_x, max_y)

    def draw_obstacles(self, game):
        screen = game.get_screen()
        camera_position = game.get_camera_position()

        for obstacle in self.get_obstacles_on_screen(game):
            obstacle.draw(screen, camera_position)

    def raycast_first(self, start: Point, end: Point):
        # First: detect if start is already inside a shape
        point_hits = self.__space.point_query(
            (start.x, start.y),
            0.0,
            pymunk.ShapeFilter()
        )

        for hit in point_hits:
            # In Pymunk/Chipmunk, point-query distance is negative when inside
            if hit.distance <= 0:
                shape = hit.shape
                poly = self.__shape_to_polygon.get(shape)
                return {
                    "polygon": poly,
                    "point": start.copy(),
                    "normal": Point(0, 0),
                    "alpha": 0.0,
                    "distance": 0.0
                }

        # Otherwise do the normal raycast
        hit = self.__space.segment_query_first(
            (start.x, start.y),
            (end.x, end.y),
            0.0,
            pymunk.ShapeFilter()
        )

        if hit is None:
            return None

        shape = hit.shape
        poly = self.__shape_to_polygon.get(shape)

        return {
            "polygon": poly,
            "point": Point(hit.point.x, hit.point.y),
            "normal": Point(hit.normal.x, hit.normal.y),
            "alpha": hit.alpha,
            "distance": math.hypot(
                hit.point.x - start.x,
                hit.point.y - start.y
            )
        }

def generate_line_from_point(point: Point, rot: float, obstacle_container, max_distance=1000):
    start = point.copy()

    direction = Point.from_angle(rot, max_distance)
    far_point = start + direction

    hit = obstacle_container.raycast_first(start, far_point)

    if hit is None:
        end = far_point
    else:
        end = hit["point"]

    return start, end

def draw_ray_fan(
    screen,
    camera_position,
    obstacle_container,
    origin: Point,
    center_rot: float,
    fov_radians: float,
    ray_count: int,
    max_distance=1000,
    color_a=(255, 255, 0),
    color_b=(255, 0, 0),
    switch_distance=200,
    width=2
):
    if ray_count <= 0:
        return

    if ray_count == 1:
        angles = [center_rot]
    else:
        start_rot = center_rot - (fov_radians / 2.0)
        step = fov_radians / (ray_count - 1)
        angles = [start_rot + i * step for i in range(ray_count)]

    for rot in angles:
        start, end = generate_line_from_point(
            origin,
            rot,
            obstacle_container,
            max_distance=max_distance
        )

        dx = end.x - start.x
        dy = end.y - start.y
        dist = math.hypot(dx, dy)

        if dist <= switch_distance:
            Segment(start, end, color=color_a, width=width).draw(screen, camera_position)
            continue

        # split point
        t = switch_distance / dist
        mid = Point(
            start.x + dx * t,
            start.y + dy * t
        )

        # first segment
        Segment(start, mid, color=color_a, width=width).draw(screen, camera_position)

        # second segment
        Segment(mid, end, color=color_b, width=width).draw(screen, camera_position)

class RRTNode:
    def __init__(self, parent, position: Point, game):
        cat_pos = game.get_cat().get_head_position()
        self.parent = parent
        self.position = position.copy()
        self.distance_to_cat = get_distance(position, cat_pos)
        self.viewable_by_cat = False

    def update_viewable_by_cat(self, game):
        cat_pos = game.get_cat().get_head_position()
        hit = game.get_obstacle_container().raycast_first(cat_pos, self.position)
        self.viewable_by_cat = hit is None

    def draw(self, game):
        cat_pos = game.get_cat().get_head_position()

        hit = game.get_obstacle_container().raycast_first(cat_pos, self.position)
        viewable = (hit is None)

        distance = get_distance(self.position, cat_pos)

        if viewable:
            max_range = game.get_preferences().motion_viewable_range
            t = min(distance / max_range, 1.0)

            # bright green when close, darker green when far
            green = int(255 - (200 * t))   # 255 -> 100
            color = (0, green, 0)
        else:
            color = (255, 0, 0)

        square = Polygon(
            global_position=self.position,
            rot=0.0,
            size=4,
            points=[
                Point(-1, -1),
                Point(1, -1),
                Point(1, 1),
                Point(-1, 1)
            ],
            color=color
        )

        square.draw(game.get_screen(), game.get_camera_position())

def create_rrt(game, start_pos=Point(166, 0), step_size=50, search_size=1050, rays_per_step=10):
    total_segments = []

    node_queue = Queue()

    start_node = RRTNode(None, start_pos, game)
    node_queue.put(start_node)

    nodes = [start_node]

    steps = 0

    while (not node_queue.empty()) and steps < search_size:
        inner_segments = []

        current_node = node_queue.get()
        current_point = current_node.position

        for i in range(rays_per_step):
            steps += 1
            angle = (i / rays_per_step) * (2 * math.pi)

            start, end = generate_line_from_point(
                current_point,
                angle,
                game.get_obstacle_container(),
                max_distance=step_size
            )

            segment = Segment(start, end, color=(0, 100, 0), width=2)
            segment.shave_start(6)
            segment.shave_end(3)

            real_end = segment.get_end()
            is_line_left = segment.shave_end(3)

            if not is_line_left:
                continue

            polygon_segment = segment.to_polygon()

            inner_segments.append(polygon_segment)
            total_segments.append(polygon_segment)

            new_node = RRTNode(current_node, real_end, game)
            new_node.update_viewable_by_cat(game)

            nodes.append(new_node)
            node_queue.put(new_node)

        for segment in inner_segments:
            game.get_obstacle_container().add_obstacle(segment)

    for segment in total_segments:
        game.get_obstacle_container().remove_obstacle(segment)
    
    for node in nodes:
        node.update_viewable_by_cat(game)
        node.draw(game)

    return nodes

def draw_rrt(nodes: [RRTNode], game):
    for node in nodes:
        node.draw(game)

class Mouse:
    def __init__(self, global_pos=Point(50, 0)):
        self.__global_pos = global_pos.copy()
        self.__rot = 0
        self.__SPEED = 4
        self.__rrt = []

    def draw(self, game):
        body = Polygon(
            global_position=self.__global_pos,
            rot=self.__rot,
            size=5,
            points=[
                Point(0, -1),
                Point(0, 1),
                Point(2, 0)
            ],
            color=(255, 255, 255)
        )
        draw_rrt(self.__rrt, game)
        body.draw(game.get_screen(), game.get_camera_position())
        

    def tick(self, game):
        self.__rrt = create_rrt(game, self.__global_pos)
        keys = pygame.key.get_pressed()

        move = Point(0, 0)

        if keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_DOWN]:
            move.y += 1

        if move.x != 0 or move.y != 0:
            length = math.hypot(move.x, move.y)
            move = move / length
            self.__global_pos += move * self.__SPEED 


class Cat:
    def __init__(self, global_pos=Point(0, 0)):
        self.__head_rot = 0.0
        self.__body_rot = 0.0
        self.__global_pos = global_pos.copy()

        self.__MAX_BODY_ROT_DELTA = 0.08
        self.__MAX_HEAD_ROT_DELTA = 0.18
        self.__MAX_HEAD_OFFSET = 1.3
        self.__MAX_MOVE_SPEED = 4.0
        self.__HEAD_OFFSET = 30

    def get_position(self):
        return self.__global_pos.copy()
    
    def get_head_position(self):
        return self.__global_pos + Point.from_angle(self.__body_rot, self.__HEAD_OFFSET)

    def draw(self, game):
        head = Polygon(
            global_position=(self.get_head_position()),
            rot=self.__head_rot,
            size=20,
            points=[
                Point(0, -1),
                Point(0, 1),
                Point(2, 0)
            ],
            color=(247, 134, 27)
        )

        body = Polygon(
            global_position=self.__global_pos,
            rot=self.__body_rot,
            size=20,
            points=[
                Point(-2, -0.6),
                Point(-2, 0.6),
                Point(2, 0.6),
                Point(2, -0.6)
            ],
            color=(255, 146, 56)
        )

        draw_ray_fan(
            screen=game.get_screen(),
            camera_position=game.get_camera_position(),
            obstacle_container=game.get_obstacle_container(),
            origin=self.get_head_position(),
            center_rot=self.__head_rot,
            fov_radians=2.5,
            ray_count=100,
            max_distance=1000,
            color_a=(70, 70, 70),
            color_b=(50, 50, 50),
            switch_distance=200,
            width=2
        )

        body.draw(game.get_screen(), game.get_camera_position())
        head.draw(game.get_screen(), game.get_camera_position())

    def __wrap_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def __rotate_towards(self, current, target, max_delta):
        diff = self.__wrap_angle(target - current)

        if diff > max_delta:
            diff = max_delta
        elif diff < -max_delta:
            diff = -max_delta

        return self.__wrap_angle(current + diff)

    def __clamp_head_to_body_range(self):
        diff = self.__wrap_angle(self.__head_rot - self.__body_rot)

        if diff > self.__MAX_HEAD_OFFSET:
            self.__head_rot = self.__wrap_angle(self.__body_rot + self.__MAX_HEAD_OFFSET)
        elif diff < -self.__MAX_HEAD_OFFSET:
            self.__head_rot = self.__wrap_angle(self.__body_rot - self.__MAX_HEAD_OFFSET)

    def tick(self, game):
        move_forward = pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_SPACE]

        screen_size = game.get_screen_size()
        screen_center = screen_size / 2

        mx, my = pygame.mouse.get_pos()
        cursor_pos = Point(mx, my)

        to_cursor = cursor_pos - screen_center

        # Mouse direction in screen-space, with cat assumed at center of screen
        if not (to_cursor.x == 0 and to_cursor.y == 0):
            target_rot = math.atan2(to_cursor.y, to_cursor.x)

            # Body only turns when moving
            if move_forward:
                self.__body_rot = self.__rotate_towards(
                    self.__body_rot,
                    target_rot,
                    self.__MAX_BODY_ROT_DELTA
                )

            # Head always tries to track cursor
            self.__head_rot = self.__rotate_towards(
                self.__head_rot,
                target_rot,
                self.__MAX_HEAD_ROT_DELTA
            )

        # Head must stay within allowed range of body
        self.__clamp_head_to_body_range()

        if move_forward:
            self.__global_pos += Point.from_angle(self.__body_rot, self.__MAX_MOVE_SPEED)


class Preferences:
    def __init__(self):
        self.stationary_range = 200
        self.motion_viewable_range = 600
        
class Game:
    def __init__(self):
        self.__obstacle_container = ObstacleContainer()
        self.__clock = pygame.time.Clock()
        self.__last_update = pygame.time.get_ticks()
        self.__cat = Cat()
        self.__mouse = Mouse()
        self.__preferences = Preferences()
        
        pygame.init()
        self.__current_screen_size = Point(1000, 800)
        self.__screen = pygame.display.set_mode((
            int(self.__current_screen_size.x),
            int(self.__current_screen_size.y)
        ))

        generate_random_map(
            seed=0,
            width=10000,
            height=10000,
            object_count=4000,
            obstacle_container=self.__obstacle_container
        )

        self.__run_game()
    
    def get_cat(self):
        return self.__cat

    def get_preferences(self):
        return self.__preferences

    def get_obstacle_container(self):
        return self.__obstacle_container

    def get_screen(self):
        return self.__screen

    def __run_game(self):
        create_rrt(self)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            now = pygame.time.get_ticks()

            if now - self.__last_update >= UPDATE_MS:
                self.__tick()
                self.__last_update = now

            self.__screen.fill((30, 30, 30))
            self.__obstacle_container.draw_obstacles(self)
            self.__cat.draw(self)
            self.__mouse.draw(self)
            pygame.display.flip()
            self.__clock.tick(120)

    def __tick(self):
        self.__cat.tick(self)
        self.__mouse.tick(self)


    def get_camera_position(self):
        return self.__cat.get_position() - (self.__current_screen_size / 2)
    
    def get_screen_size(self):
        return self.__current_screen_size.copy()

def main():
    Game()


if __name__ == "__main__":
    main()
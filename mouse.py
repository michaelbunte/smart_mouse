import math
import pygame
import sys
import random
from rtree import index

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

    def __compute_aabb_center(self):
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

        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5

        return Point(cx, cy)

    def add_to_obstacle_container(self, obstacle_container):
        bbox = self.compute_aabb()
        obstacle_container.add_obstacle(self, bbox)

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
        self.__index = index.Index()
        self.__obstacles = {}
        self.__next_id = 0

    def add_obstacle(self, obstacle, bbox):
        obstacle_id = self.__next_id
        self.__next_id += 1

        self.__index.insert(obstacle_id, bbox)
        self.__obstacles[obstacle_id] = (obstacle, bbox)

        return obstacle_id

    def remove_obstacle(self, obstacle_id):
        obstacle, bbox = self.__obstacles[obstacle_id]
        self.__index.delete(obstacle_id, bbox)
        del self.__obstacles[obstacle_id]

    def query_box(self, min_x, min_y, max_x, max_y):
        ids = self.__index.intersection((min_x, min_y, max_x, max_y))
        return [self.__obstacles[i][0] for i in ids]

    def get_obstacles_on_screen(self, game):
        camera = game.get_camera_position()
        screen_size = game.get_screen_size()

        min_x = camera.x
        min_y = camera.y
        max_x = camera.x + screen_size.x
        max_y = camera.y + screen_size.y

        ids = self.__index.intersection((min_x, min_y, max_x, max_y))
        return [self.__obstacles[i][0] for i in ids]

    def draw_obstacles(self, game):
        screen = game.get_screen()
        camera_position = game.get_camera_position()

        obstacles = self.get_obstacles_on_screen(game)

        for obstacle in obstacles:
            obstacle.draw(screen, camera_position)
    
class Cat:
    def __init__(self, global_pos=Point(0, 0)):
        self.__head_rot = 0.0
        self.__body_rot = 0.0
        self.global_pos = global_pos.copy()
        self.max_rot_delta = 0.08  # radians per tick

    def get_position(self):
        return self.global_pos.copy()

    def draw(self, game):
        head = Polygon(
            global_position=(self.global_pos + Point.from_angle(self.__body_rot, 30)),
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
            global_position=self.global_pos,
            rot=self.__body_rot,
            size=20,
            points=[
                Point(-2, -0.6),
                Point(-2, 0.6),
                Point( 2, 0.6),
                Point( 2, -0.6)
            ],
            color=(255, 146, 56)
        )

        body.draw(
            game.get_screen(),
            game.get_camera_position()
        )

        head.draw(
            game.get_screen(),
            game.get_camera_position()
        )

    def _wrap_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def tick(self, game):
        screen_size = game.get_screen_size()
        screen_center = screen_size / 2

        mx, my = pygame.mouse.get_pos()
        mouse_pos = Point(mx, my)

        to_mouse = mouse_pos - screen_center

        # Avoid unstable atan2(0, 0) behavior when cursor is exactly centered
        if to_mouse.x == 0 and to_mouse.y == 0:
            return

        target_rot = math.atan2(to_mouse.y, to_mouse.x)

        angle_diff = self._wrap_angle(target_rot - self.__head_rot)

        if angle_diff > self.max_rot_delta:
            angle_diff = self.max_rot_delta
        elif angle_diff < -self.max_rot_delta:
            angle_diff = -self.max_rot_delta

        self.__head_rot = self._wrap_angle(self.__head_rot + angle_diff)

class Game:
    def __init__(self):
        self.__camera_position = Point(0.0, 0.0)
        self.__obstacle_container = ObstacleContainer()
        self.__clock = pygame.time.Clock()
        self.__last_update = pygame.time.get_ticks()
        self.__cat = Cat()
        
        pygame.init()
        self.__current_screen_size = Point(800, 600)
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
    
    def get_screen(self):
        return self.__screen

    def __run_game(self):
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
            pygame.display.flip()
            self.__clock.tick(120)

    def __tick(self):
        mouse_buttons = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()

        if mouse_buttons[0]:
            mx, my = pygame.mouse.get_pos()

        self.__cat.tick(self)


    def get_camera_position(self):
        # return self.__camera_position.copy()
            return self.__cat.get_position() - (self.__current_screen_size / 2)
        # return self.__cat.get_position()
    
    def get_screen_size(self):
        return self.__current_screen_size.copy()

def main():
    Game()


if __name__ == "__main__":
    main()
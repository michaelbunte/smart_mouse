import pygame
import sys

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# class screen_object:
    

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Arrow Key Box Control")

clock = pygame.time.Clock()

box_size = 80
box = pygame.Rect(WIDTH // 2, HEIGHT // 2, box_size, box_size)

UPDATE_MS = 10
last_update = pygame.time.get_ticks()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    now = pygame.time.get_ticks()

    if now - last_update >= UPDATE_MS:
        last_update = now

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            box.x -= 1

        if keys[pygame.K_RIGHT]:
            box.x += 1

        if keys[pygame.K_UP]:
            box.y -= 1

        if keys[pygame.K_DOWN]:
            box.y += 1

    screen.fill((30, 30, 30))
    pygame.draw.rect(screen, (200, 100, 100), box)

    pygame.display.flip()
    clock.tick(120)
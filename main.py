import json
import random
import sys
from pathlib import Path

import pygame

CELL_SIZE = 20

DEFAULT_THEME = {
    "bg": [15, 15, 15],
    "grid": [30, 30, 30],
    "snake": [80, 200, 120],
    "snake_head": [140, 230, 160],
    "food": [220, 80, 80],
    "wall": [120, 120, 140],
    "text": [230, 230, 230],
}

DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

OPPOSITE = {
    (0, -1): (0, 1),
    (0, 1): (0, -1),
    (-1, 0): (1, 0),
    (1, 0): (-1, 0),
}


def load_config(path):
    with open(path) as f:
        return json.load(f)


def expand_walls(wall_specs, cols, rows):
    walls = set()
    for spec in wall_specs:
        kind = spec.get("type")
        if kind == "rect":
            x, y, w, h = spec["x"], spec["y"], spec["width"], spec["height"]
            for dx in range(w):
                for dy in range(h):
                    walls.add((x + dx, y + dy))
        elif kind == "cells":
            for cell in spec["cells"]:
                walls.add(tuple(cell))
        elif kind == "border":
            for x in range(cols):
                walls.add((x, 0))
                walls.add((x, rows - 1))
            for y in range(rows):
                walls.add((0, y))
                walls.add((cols - 1, y))
        else:
            raise ValueError(f"Unknown wall type: {kind!r}")
    return walls


def random_food(cols, rows, snake, walls):
    free = [
        (x, y)
        for x in range(cols)
        for y in range(rows)
        if (x, y) not in snake and (x, y) not in walls
    ]
    return random.choice(free) if free else None


def draw_grid(surface, cols, rows, color):
    w = cols * CELL_SIZE
    h = rows * CELL_SIZE
    for x in range(0, w + 1, CELL_SIZE):
        pygame.draw.line(surface, color, (x, 0), (x, h))
    for y in range(0, h + 1, CELL_SIZE):
        pygame.draw.line(surface, color, (0, y), (w, y))


def draw_cell(surface, pos, color):
    rect = pygame.Rect(
        pos[0] * CELL_SIZE, pos[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE
    )
    pygame.draw.rect(surface, color, rect)


def build_snake(start, direction, length):
    snake = []
    for i in range(length):
        snake.append((start[0] - i * direction[0], start[1] - i * direction[1]))
    return snake


def play_level(level, theme, font):
    cols = level["grid_cols"]
    rows = level["grid_rows"]
    fps = level.get("fps", 15)
    wrap = level.get("wrap_walls", False)
    walls = expand_walls(level.get("walls", []), cols, rows)

    direction = DIRECTIONS[level.get("snake_direction", "right")]
    snake = build_snake(
        tuple(level["snake_start"]),
        direction,
        level.get("snake_length", 3),
    )
    food = random_food(cols, rows, set(snake), walls)
    score = 0
    target = level["score_to_advance"]
    pending_direction = direction

    width = cols * CELL_SIZE
    height = rows * CELL_SIZE
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", score
            if event.type == pygame.KEYDOWN:
                new_dir = None
                if event.key in (pygame.K_UP, pygame.K_w):
                    new_dir = DIRECTIONS["up"]
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    new_dir = DIRECTIONS["down"]
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    new_dir = DIRECTIONS["left"]
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    new_dir = DIRECTIONS["right"]
                elif event.key == pygame.K_ESCAPE:
                    return "quit", score
                if new_dir and new_dir != OPPOSITE[direction]:
                    pending_direction = new_dir

        direction = pending_direction
        head = snake[0]
        new_head = (head[0] + direction[0], head[1] + direction[1])
        if wrap:
            new_head = (new_head[0] % cols, new_head[1] % rows)

        out_of_bounds = (
            new_head[0] < 0
            or new_head[0] >= cols
            or new_head[1] < 0
            or new_head[1] >= rows
        )
        hit_wall = new_head in walls
        hit_self = new_head in snake[:-1]

        if out_of_bounds or hit_wall or hit_self:
            return "dead", score

        snake.insert(0, new_head)
        if food is not None and new_head == food:
            score += 1
            if score >= target:
                return "complete", score
            food = random_food(cols, rows, set(snake), walls)
        else:
            snake.pop()

        screen.fill(theme["bg"])
        draw_grid(screen, cols, rows, theme["grid"])
        for w in walls:
            draw_cell(screen, w, theme["wall"])
        if food is not None:
            draw_cell(screen, food, theme["food"])
        for i, segment in enumerate(snake):
            color = theme["snake_head"] if i == 0 else theme["snake"]
            draw_cell(screen, segment, color)

        title = font.render(
            f"{level['name']}  |  {score}/{target}",
            True,
            theme["text"],
        )
        screen.blit(title, (10, 10))

        pygame.display.flip()
        clock.tick(fps)


def show_message(theme, big_font, font, title, subtitle):
    screen = pygame.display.get_surface()
    screen.fill(theme["bg"])
    width, height = screen.get_size()
    t = big_font.render(title, True, theme["text"])
    s = font.render(subtitle, True, theme["text"])
    screen.blit(t, (width // 2 - t.get_width() // 2, height // 2 - t.get_height()))
    screen.blit(s, (width // 2 - s.get_width() // 2, height // 2 + 10))
    pygame.display.flip()


def wait_for_key():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                return "next"


def merge_theme(base, override):
    return {**base, **(override or {})}


def main():
    config_path = Path(__file__).parent / "levels.json"
    config = load_config(config_path)
    base_theme = merge_theme(DEFAULT_THEME, config.get("theme"))
    levels = config["levels"]
    if not levels:
        print("No levels defined in levels.json", file=sys.stderr)
        sys.exit(1)

    pygame.init()
    pygame.display.set_caption("Snake")
    font = pygame.font.SysFont(None, 28)
    big_font = pygame.font.SysFont(None, 64)

    i = 0
    while i < len(levels):
        level = levels[i]
        theme = merge_theme(base_theme, level.get("theme"))
        status, score = play_level(level, theme, font)

        if status == "quit":
            break
        if status == "dead":
            show_message(
                theme, big_font, font,
                "Game Over",
                f"Score {score}  -  any key to retry, ESC to quit",
            )
            if wait_for_key() == "quit":
                break
            continue
        if status == "complete":
            if i + 1 < len(levels):
                show_message(
                    theme, big_font, font,
                    f"Level {i + 1} Complete!",
                    "Press any key for next level",
                )
            else:
                show_message(
                    theme, big_font, font,
                    "You Win!",
                    "Press any key to quit",
                )
            if wait_for_key() == "quit":
                break
            i += 1

    pygame.quit()


if __name__ == "__main__":
    main()

import json
import random
import sys
import time
from pathlib import Path

import pygame

CELL_SIZE = 26
MENU_SIZE = (760, 760)
RENDER_FPS = 60

SPEED_PRESETS = {
    "Slow": 8,
    "Normal": 12,
    "Fast": 16,
    "Insane": 22,
}
DEFAULT_SPEED = "Normal"
DEFAULT_NUM_APPLES = 1
MAX_APPLES = 15

COLORS = {
    "bg": (45, 69, 35),
    "field_light": (170, 215, 81),
    "field_dark": (162, 209, 73),
    "snake": (74, 117, 44),
    "snake_eye": (20, 20, 20),
    "apple": (231, 71, 29),
    "apple_dark": (179, 48, 21),
    "apple_stem": (138, 95, 54),
    "apple_leaf": (92, 139, 54),
    "wall": (176, 176, 184),
    "wall_edge": (118, 118, 126),
    "text": (240, 240, 240),
    "text_dim": (200, 200, 200),
    "select": (255, 215, 90),
    "panel": (0, 0, 0, 140),
}

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIR_NAMES = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


class Settings:
    def __init__(self):
        self.speed = DEFAULT_SPEED
        self.num_apples = DEFAULT_NUM_APPLES

    @property
    def tick_rate(self):
        return SPEED_PRESETS[self.speed]


def expand_walls(specs, cols, rows):
    walls = set()
    for spec in specs:
        kind = spec.get("type")
        if kind == "rect":
            for dx in range(spec["width"]):
                for dy in range(spec["height"]):
                    walls.add((spec["x"] + dx, spec["y"] + dy))
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


def lerp(a, b, t):
    return a + (b - a) * t


def cell_center_smooth(prev, cur, progress):
    if abs(cur[0] - prev[0]) > 1 or abs(cur[1] - prev[1]) > 1:
        # wrap happened — snap to current cell
        return (
            cur[0] * CELL_SIZE + CELL_SIZE / 2,
            cur[1] * CELL_SIZE + CELL_SIZE / 2,
        )
    return (
        lerp(prev[0], cur[0], progress) * CELL_SIZE + CELL_SIZE / 2,
        lerp(prev[1], cur[1], progress) * CELL_SIZE + CELL_SIZE / 2,
    )


def make_field_background(cols, rows):
    surf = pygame.Surface((cols * CELL_SIZE, rows * CELL_SIZE))
    for y in range(rows):
        for x in range(cols):
            color = COLORS["field_light"] if (x + y) % 2 == 0 else COLORS["field_dark"]
            pygame.draw.rect(
                surf, color,
                pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE),
            )
    return surf


def draw_walls(screen, walls):
    for (x, y) in walls:
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, COLORS["wall"], rect)
        pygame.draw.rect(screen, COLORS["wall_edge"], rect, 2)


def draw_apple(screen, pos):
    cx = pos[0] * CELL_SIZE + CELL_SIZE // 2
    cy = pos[1] * CELL_SIZE + CELL_SIZE // 2 + 1
    r = int(CELL_SIZE * 0.36)
    pygame.draw.circle(screen, COLORS["apple"], (cx, cy), r)
    pygame.draw.circle(
        screen, COLORS["apple_dark"],
        (cx + r // 3, cy + r // 4), max(2, r // 3),
    )
    pygame.draw.line(
        screen, COLORS["apple_stem"],
        (cx, cy - r + 1), (cx + 2, cy - r - 4), 2,
    )
    leaf = [
        (cx + 2, cy - r - 1),
        (cx + r, cy - r - 3),
        (cx + 2, cy - r + 3),
    ]
    pygame.draw.polygon(screen, COLORS["apple_leaf"], leaf)


def draw_snake(screen, snake, prev_snake, direction, progress):
    if len(snake) > len(prev_snake):
        anchor = snake[1] if len(snake) > 1 else snake[0]
        aligned = [anchor] + prev_snake
    else:
        aligned = prev_snake

    positions = [
        cell_center_smooth(aligned[i] if i < len(aligned) else snake[i],
                           snake[i], progress)
        for i in range(len(snake))
    ]

    color = COLORS["snake"]
    body_thickness = int(CELL_SIZE * 0.82)
    half = body_thickness // 2
    corner_radius = body_thickness // 3

    # Bridges between consecutive segments (axis-aligned rects)
    for i in range(len(positions) - 1):
        a, b = positions[i], positions[i + 1]
        if abs(a[0] - b[0]) > CELL_SIZE * 1.5 or abs(a[1] - b[1]) > CELL_SIZE * 1.5:
            continue
        if abs(a[0] - b[0]) >= abs(a[1] - b[1]):
            x_min, x_max = sorted([a[0], b[0]])
            y_mid = (a[1] + b[1]) / 2
            rect = pygame.Rect(
                int(x_min), int(y_mid - half),
                int(x_max - x_min), body_thickness,
            )
        else:
            y_min, y_max = sorted([a[1], b[1]])
            x_mid = (a[0] + b[0]) / 2
            rect = pygame.Rect(
                int(x_mid - half), int(y_min),
                body_thickness, int(y_max - y_min),
            )
        pygame.draw.rect(screen, color, rect)

    # Square caps at each interior segment center (fills corner gaps cleanly)
    for i, pos in enumerate(positions):
        if i == 0 or i == len(positions) - 1:
            continue
        rect = pygame.Rect(0, 0, body_thickness, body_thickness)
        rect.center = (int(pos[0]), int(pos[1]))
        pygame.draw.rect(screen, color, rect)

    # Rounded head and tail
    hx, hy = positions[0]
    head_rect = pygame.Rect(0, 0, body_thickness, body_thickness)
    head_rect.center = (int(hx), int(hy))
    pygame.draw.rect(screen, color, head_rect, border_radius=corner_radius)

    if len(positions) >= 2:
        tx, ty = positions[-1]
        tail_rect = pygame.Rect(0, 0, body_thickness, body_thickness)
        tail_rect.center = (int(tx), int(ty))
        pygame.draw.rect(screen, color, tail_rect, border_radius=corner_radius)

    # Eyes — two black dots facing the direction of travel
    dx, dy = direction
    perp = (-dy, dx)
    eye_forward = body_thickness // 5
    eye_side = body_thickness // 4
    eye_r = max(2, body_thickness // 9)
    for sign in (-1, 1):
        ecx = hx + dx * eye_forward + perp[0] * sign * eye_side
        ecy = hy + dy * eye_forward + perp[1] * sign * eye_side
        pygame.draw.circle(screen, COLORS["snake_eye"], (int(ecx), int(ecy)), eye_r)


def draw_hud_bar(screen, text, font):
    w = screen.get_width()
    bar = pygame.Surface((w, 36), pygame.SRCALPHA)
    bar.fill(COLORS["panel"])
    screen.blit(bar, (0, 0))
    surf = font.render(text, True, COLORS["text"])
    screen.blit(surf, (12, 8))


def draw_overlay(screen, big_font, sub_font, title, subtitle):
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    t = big_font.render(title, True, COLORS["text"])
    s = sub_font.render(subtitle, True, COLORS["text_dim"])
    screen.blit(t, (w // 2 - t.get_width() // 2, h // 2 - 50))
    screen.blit(s, (w // 2 - s.get_width() // 2, h // 2 + 20))


class GameState:
    def __init__(self, level, settings):
        self.cols = level["grid_cols"]
        self.rows = level["grid_rows"]
        self.wrap = level.get("wrap_walls", False)
        self.walls = expand_walls(level.get("walls", []), self.cols, self.rows)
        self.direction = DIR_NAMES[level.get("snake_direction", "right")]
        self.pending_direction = self.direction
        self.snake = self._build_snake(
            tuple(level["snake_start"]),
            self.direction,
            level.get("snake_length", 3),
        )
        self.prev_snake = list(self.snake)
        self.foods = set()
        self._spawn_foods(settings.num_apples)
        self.score = 0
        self.target = level.get("score_to_advance")
        self.tick_interval = 1.0 / settings.tick_rate
        self.last_tick = time.time()
        self.dead = False
        self.complete = False

    def _build_snake(self, start, direction, length):
        return [
            (start[0] - i * direction[0], start[1] - i * direction[1])
            for i in range(length)
        ]

    def _spawn_foods(self, target_count):
        occupied = set(self.snake) | self.walls | self.foods
        free = [
            (x, y) for x in range(self.cols) for y in range(self.rows)
            if (x, y) not in occupied
        ]
        random.shuffle(free)
        while len(self.foods) < target_count and free:
            self.foods.add(free.pop())

    def handle_key(self, key):
        new_dir = None
        if key in (pygame.K_UP, pygame.K_w):
            new_dir = UP
        elif key in (pygame.K_DOWN, pygame.K_s):
            new_dir = DOWN
        elif key in (pygame.K_LEFT, pygame.K_a):
            new_dir = LEFT
        elif key in (pygame.K_RIGHT, pygame.K_d):
            new_dir = RIGHT
        if new_dir and new_dir != OPPOSITE[self.direction]:
            self.pending_direction = new_dir

    def tick(self, num_apples):
        if self.dead or self.complete:
            return
        self.prev_snake = list(self.snake)
        self.direction = self.pending_direction
        hx, hy = self.snake[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])
        if self.wrap:
            new_head = (new_head[0] % self.cols, new_head[1] % self.rows)

        out_of_bounds = (
            new_head[0] < 0 or new_head[0] >= self.cols
            or new_head[1] < 0 or new_head[1] >= self.rows
        )
        will_die = (
            out_of_bounds
            or new_head in self.walls
            or new_head in self.snake[:-1]
        )

        self.snake.insert(0, new_head)
        if (not will_die) and new_head in self.foods:
            self.foods.remove(new_head)
            self.score += 1
            self._spawn_foods(num_apples)
            if self.target and self.score >= self.target:
                self.complete = True
        else:
            self.snake.pop()

        if will_die:
            self.dead = True

    def tick_progress(self):
        return min(1.0, (time.time() - self.last_tick) / self.tick_interval)

    def maybe_tick(self, num_apples):
        if time.time() - self.last_tick >= self.tick_interval:
            self.tick(num_apples)
            self.last_tick = time.time()


def play(level, settings, hud_label):
    cols = level["grid_cols"]
    rows = level["grid_rows"]
    screen = pygame.display.set_mode((cols * CELL_SIZE, rows * CELL_SIZE))
    pygame.display.set_caption("Snakey")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 26)
    big_font = pygame.font.SysFont(None, 72)
    sub_font = pygame.font.SysFont(None, 32)

    music_rel = level.get("music")
    if music_rel and pygame.mixer.get_init():
        music_path = Path(__file__).parent / music_rel
        if music_path.exists():
            try:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.play(-1)
            except pygame.error as e:
                print(f"Could not play {music_path}: {e}", file=sys.stderr)
        else:
            print(f"Music file not found: {music_path}", file=sys.stderr)

    try:
        return _play_loop(
            GameState(level, settings), level, settings, hud_label,
            screen, clock, font, big_font, sub_font,
        )
    finally:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()


def _play_loop(state, level, settings, hud_label, screen, clock, font, big_font, sub_font):
    cols = level["grid_cols"]
    rows = level["grid_rows"]
    field_bg = make_field_background(cols, rows)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if state.dead and event.key == pygame.K_r:
                    state = GameState(level, settings)
                    continue
                if state.complete and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "complete"
                state.handle_key(event.key)

        state.maybe_tick(settings.num_apples)

        screen.blit(field_bg, (0, 0))
        draw_walls(screen, state.walls)
        for food in state.foods:
            draw_apple(screen, food)
        draw_snake(
            screen, state.snake, state.prev_snake,
            state.direction, state.tick_progress(),
        )

        target_text = f" / {state.target}" if state.target else ""
        draw_hud_bar(
            screen,
            f"{hud_label}    Score: {state.score}{target_text}    Speed: {settings.speed}    Apples: {settings.num_apples}",
            font,
        )

        if state.dead:
            draw_overlay(screen, big_font, sub_font, "Game Over", "R = retry    ESC = menu")
        elif state.complete:
            draw_overlay(
                screen, big_font, sub_font,
                "Level Complete!", "Enter = continue    ESC = menu",
            )

        pygame.display.flip()
        clock.tick(RENDER_FPS)


def menu_screen(title, options, current_index=0, subtitle=None):
    screen = pygame.display.set_mode(MENU_SIZE)
    pygame.display.set_caption("Snakey")
    title_font = pygame.font.SysFont(None, 88)
    option_font = pygame.font.SysFont(None, 40)
    hint_font = pygame.font.SysFont(None, 22)
    sub_font = pygame.font.SysFont(None, 28)
    clock = pygame.time.Clock()
    selected = current_index

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return -1
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return -1
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT, pygame.K_d):
                    return selected

        screen.fill(COLORS["bg"])
        w, h = screen.get_size()
        t_surf = title_font.render(title, True, COLORS["text"])
        screen.blit(t_surf, (w // 2 - t_surf.get_width() // 2, 80))

        if subtitle:
            s_surf = sub_font.render(subtitle, True, COLORS["text_dim"])
            screen.blit(s_surf, (w // 2 - s_surf.get_width() // 2, 170))

        start_y = 240
        for i, opt in enumerate(options):
            label = opt if isinstance(opt, str) else f"{opt[0]}:   {opt[1]}"
            color = COLORS["select"] if i == selected else COLORS["text"]
            surf = option_font.render(label, True, color)
            y = start_y + i * 56
            x = w // 2 - surf.get_width() // 2
            screen.blit(surf, (x, y))
            if i == selected:
                pygame.draw.polygon(
                    screen, COLORS["select"],
                    [(x - 30, y + 10), (x - 14, y + 22), (x - 30, y + 34)],
                )

        hint = hint_font.render(
            "Arrow keys = navigate    Enter = select    ESC = back",
            True, COLORS["text_dim"],
        )
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 36))

        pygame.display.flip()
        clock.tick(RENDER_FPS)


def options_menu(settings):
    speeds = list(SPEED_PRESETS.keys())
    sel = 0
    while True:
        options = [
            ("Snake Speed", settings.speed),
            ("Apples on screen", str(settings.num_apples)),
            "Back",
        ]
        choice = menu_screen("Options", options, current_index=sel,
                             subtitle="Enter to cycle values")
        if choice == -1 or choice == 2:
            return
        sel = choice
        if choice == 0:
            i = speeds.index(settings.speed)
            settings.speed = speeds[(i + 1) % len(speeds)]
        elif choice == 1:
            settings.num_apples = (settings.num_apples % MAX_APPLES) + 1


def level_select(levels):
    options = [
        f"{lv['name']}  -  {lv.get('score_to_advance', '?')} apples"
        for lv in levels
    ] + ["Back"]
    choice = menu_screen("Select Level", options)
    if choice == -1 or choice == len(levels):
        return None
    return choice


def show_win_screen():
    screen = pygame.display.set_mode(MENU_SIZE)
    big_font = pygame.font.SysFont(None, 96)
    sub_font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                return
        screen.fill(COLORS["bg"])
        w, h = screen.get_size()
        t = big_font.render("YOU WIN!", True, COLORS["select"])
        s = sub_font.render("Press any key to return to menu", True, COLORS["text_dim"])
        screen.blit(t, (w // 2 - t.get_width() // 2, h // 2 - 60))
        screen.blit(s, (w // 2 - s.get_width() // 2, h // 2 + 30))
        pygame.display.flip()
        clock.tick(RENDER_FPS)


FREE_ROAM_LEVEL = {
    "name": "Free Roam",
    "grid_cols": 30,
    "grid_rows": 30,
    "wrap_walls": False,
    "walls": [],
    "snake_start": [15, 15],
    "snake_direction": "right",
    "snake_length": 3,
}


def main_menu(levels, settings):
    while True:
        choice = menu_screen(
            "SNAKEY",
            ["Play Levels", "Free Roam", "Options", "Quit"],
            subtitle=f"Speed: {settings.speed}    Apples: {settings.num_apples}",
        )
        if choice == -1 or choice == 3:
            return
        if choice == 0:
            idx = level_select(levels)
            if idx is None:
                continue
            i = idx
            quit_all = False
            while i < len(levels):
                result = play(levels[i], settings, levels[i]["name"])
                if result == "quit":
                    quit_all = True
                    break
                if result == "menu":
                    break
                if result == "complete":
                    i += 1
            if quit_all:
                return
            if i >= len(levels):
                show_win_screen()
        elif choice == 1:
            while True:
                result = play(FREE_ROAM_LEVEL, settings, "Free Roam")
                if result == "quit":
                    return
                if result == "menu":
                    break
        elif choice == 2:
            options_menu(settings)


def main():
    config_path = Path(__file__).parent / "levels.json"
    config = json.loads(config_path.read_text())
    levels = config["levels"]
    if not levels:
        print("No levels defined in levels.json", file=sys.stderr)
        sys.exit(1)

    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error as e:
        print(f"Audio init failed - game will run without sound: {e}", file=sys.stderr)
    settings = Settings()
    main_menu(levels, settings)
    pygame.quit()


if __name__ == "__main__":
    main()

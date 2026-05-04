# Snakey

A classic grid-based Snake game built with Python and Pygame, featuring multiple levels that are fully designed and configured through a JSON file. No code changes required to add new levels, walls, or themes.

## Features

- Classic discrete-grid snake mechanics (no sub-cell motion)
- Multi-level progression with per-level grid size, speed, and obstacles
- Level design driven by `levels.json` — edit it, run the game
- Three wall primitives: full borders, rectangles, and individual cells
- Optional edge wraparound per level
- Per-level color theme overrides
- Self-collision and 180-degree-turn protection
- Retry on death, advance on completion, win screen at the end

## Requirements

- macOS, Linux, or Windows
- [`uv`](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.12 (managed automatically by `uv`)

## Setup

Clone the repo and sync dependencies — `uv` handles the Python install and virtual environment for you.

```bash
git clone git@github.com:audreetan/snakey.git
cd snakey
uv sync
```

That creates a `.venv/` with Python 3.12 and installs Pygame from the lockfile.

## Running the game

```bash
uv run main.py
```

`uv run` executes the script inside the project's virtual environment — no need to manually activate anything.

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move snake |
| ESC | Quit |
| Any key (on Game Over / Level Complete) | Continue |

## Gameplay

- Eat food (red square) to grow the snake and increase your score.
- Hit `score_to_advance` for the level to clear it and move to the next.
- Touching a wall or your own body ends the run for that level.
- After dying you can retry the same level, or press ESC to quit.
- Beat all levels to see the win screen.

## Designing your own levels

All level data lives in `levels.json`. Edit it freely and re-run the game.

### Top-level structure

```json
{
  "theme": { ... global colors ... },
  "levels": [ ... level objects ... ]
}
```

### Level fields

| Field | Type | Description |
|---|---|---|
| `name` | string | Title shown in the HUD |
| `grid_cols` | int | Grid width in cells |
| `grid_rows` | int | Grid height in cells |
| `fps` | int | Game speed (cells the snake moves per second) |
| `wrap_walls` | bool | If `true`, the snake wraps around screen edges; if `false`, edges are deadly |
| `walls` | array | Wall specs (see below) |
| `snake_start` | `[col, row]` | Starting head position |
| `snake_direction` | `"up"` / `"down"` / `"left"` / `"right"` | Starting direction |
| `snake_length` | int | Starting body length |
| `score_to_advance` | int | Food eaten to clear the level |
| `theme` | object | (optional) Per-level color overrides |

### Wall types

```json
{ "type": "border" }
```
Adds walls around the entire grid perimeter.

```json
{ "type": "rect", "x": 5, "y": 5, "width": 3, "height": 3 }
```
Solid rectangle of walls. `x`/`y` is the top-left cell.

```json
{ "type": "cells", "cells": [[5, 5], [6, 5], [7, 5]] }
```
Individual cells. Use this for irregular shapes.

### Theme keys

All colors are `[r, g, b]` arrays (0-255):

| Key | What it colors |
|---|---|
| `bg` | Background |
| `grid` | Grid lines |
| `snake` | Snake body |
| `snake_head` | Snake head |
| `food` | Food cell |
| `wall` | Wall cells |
| `text` | HUD and end-screen text |

Top-level `theme` sets global defaults; a `theme` block inside a level overrides specific keys for that level only.

### Example level

```json
{
  "name": "Level 6: My Custom Level",
  "grid_cols": 24,
  "grid_rows": 18,
  "fps": 14,
  "wrap_walls": false,
  "walls": [
    { "type": "border" },
    { "type": "rect", "x": 10, "y": 8, "width": 4, "height": 2 }
  ],
  "snake_start": [3, 9],
  "snake_direction": "right",
  "snake_length": 3,
  "score_to_advance": 8,
  "theme": {
    "snake": [200, 100, 200]
  }
}
```

## Project structure

```
snakey/
  main.py            # Game loop, rendering, level orchestration
  levels.json        # Level definitions and theme
  pyproject.toml     # Project metadata and dependencies
  uv.lock            # Pinned dependency versions
  .python-version    # Pinned Python version (3.12)
```

## Tips for level design

- Keep `score_to_advance` reasonable for the available open space — a 20x20 grid full of obstacles can't fit 30 food spawns realistically.
- `fps` 10-12 is relaxed; 14-16 is challenging; 18+ is hectic on small grids.
- `wrap_walls: true` works best on open levels; combining it with interior walls makes for interesting strategy.
- Test new wall layouts at low `fps` first to confirm the snake can actually navigate them.

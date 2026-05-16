# slide-games

[![PyPI](https://img.shields.io/pypi/v/slide-games)](https://pypi.org/project/slide-games/)
[![CI](https://github.com/sahilmenon/slide-games/actions/workflows/ci.yml/badge.svg)](https://github.com/sahilmenon/slide-games/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

A Python framework for building interactive arcade games that run entirely inside Google Slides.

Each reachable game state becomes one slide. Directional buttons are hyperlinks that jump between slides. Players open the presentation in **Presentation mode** and navigate with the on-screen arrows.

---

## How it works

```
define game logic  →  BFS discovers all states  →  one slide per state
    ↓                                                       ↓
BaseGame subclass          builder.py              Google Slides API

nav buttons wired with hyperlinks  →  play in Presentation mode (Ctrl+Shift+F5)
```

State spaces grow quickly when collectibles are involved (Pac-Man with *n* pellets has `positions × 2ⁿ` states). The package enforces a `max_states` cap (default 1 000) to catch runaway games before they hit the API.

---

## Installation

```bash
pip install slide-games
```

### Prerequisites — Google Cloud credentials

Follow these steps once per Google account.

#### 1. Create a project

1. Open [console.cloud.google.com](https://console.cloud.google.com).
2. Click the project dropdown at the top-left → **New Project**.
3. Give it any name → **Create**.

#### 2. Enable the Google Slides API

1. In the left sidebar go to **APIs & Services** → **Library**.
2. Search for **Google Slides API** → click it → **Enable**.

#### 3. Configure the OAuth consent screen

1. Left sidebar → **APIs & Services** → **OAuth consent screen**.
2. Select **External** → **Create**.
3. Fill in *App name* (anything, e.g. `slide-games`), *User support email*, and *Developer contact email*.
4. Click **Save and Continue** through all remaining steps until you reach the dashboard.

#### 4. Create OAuth credentials

1. Left sidebar → **APIs & Services** → **Credentials**.
2. Click **+ Create Credentials** → **OAuth client ID**.
3. Application type: **Desktop app** → **Create**.
4. In the confirmation dialog click **Download JSON**.
5. Rename the downloaded file to `credentials.json` and place it in the directory where you run your script.

#### 5. First run

The first time you call `build_presentation()` a browser tab opens asking you to sign in and grant access. After you approve, a `token.json` is saved alongside `credentials.json` so you won't be prompted again.

> **Never commit `credentials.json` or `token.json` to version control.**
> Both are listed in `.gitignore` by default.

---

## Quick start

### Single-level maze

```python
from slide_games import build_presentation, MazeGame, generate_maze, DARK

maze = generate_maze(20, 16, algorithm="backtracker", seed=7)
url  = build_presentation(MazeGame(maze), title="Maze", theme=DARK, max_states=700)
print(url)
```

### Multi-level campaign

`build_campaign` links the win slide of each level to the starting position of the next, creating a seamless campaign.

```python
from slide_games import build_campaign, MazeGame, generate_maze, DARK

levels = [
    MazeGame(generate_maze(20, 16, algorithm="backtracker", seed=7)),   # Easy
    MazeGame(generate_maze(25, 20, algorithm="prim",        seed=42)),  # Medium
    MazeGame(generate_maze(30, 24, algorithm="kruskal",     seed=99)),  # Hard
]

url = build_campaign(levels, title="Maze Quest", theme=DARK, max_states=1500)
print(url)
```

---

## Building a custom game

Subclass `BaseGame` and implement three methods. The package handles state discovery, slide creation, rendering, and linking.

```python
from slide_games import BaseGame, build_presentation

class MyGame(BaseGame):
    def get_initial_state(self):
        """Return the starting state (any hashable object)."""
        ...

    def get_transitions(self, state):
        """Return {direction: next_state_or_None} for all four directions.

        Use None for blocked directions — the button is rendered but grayed out.
        """
        return {
            "up":    ...,
            "down":  ...,
            "left":  ...,
            "right": ...,
        }

    def is_terminal(self, state) -> bool:
        """Return True when the game is won (or lost)."""
        ...

url = build_presentation(MyGame(), title="My Game")
```

### Custom rendering

Override `render()` to draw fully custom visuals using a pygame-like API. The D-pad buttons and win banner are still added automatically — keep content above `y = NAV_RESERVED_Y` (~820 px) to avoid overlap.

```python
from slide_games import BaseGame, build_presentation, SCREEN_W, NAV_RESERVED_Y
from slide_games.gfx import Color, Rect, draw

class MyGame(BaseGame):
    ...

    def render(self, surface, state) -> None:
        # 1920 × 1080 virtual coordinate space
        surface.fill(Color(10, 10, 40))
        draw.rect(surface, Color(0, 200, 100),
                  Rect(state.x * 80, state.y * 80, 70, 70),
                  border_radius=10)
        draw.text(surface, f"Score: {state.score}",
                  Rect(20, 20, 400, 50),
                  color=Color(255, 255, 255), font_size=28, bold=True)
```

Available drawing functions:

| Function | Description |
|----------|-------------|
| `surface.fill(color)` | Fill background |
| `draw.rect(surface, color, Rect(x,y,w,h), border_radius=0, width=0)` | Rectangle (filled or outline) |
| `draw.circle(surface, color, (cx,cy), radius, width=0)` | Circle (filled or outline) |
| `draw.line(surface, color, (x1,y1), (x2,y2), width=1)` | Line segment |
| `draw.lines(surface, color, points, width=1, closed=False)` | Multi-segment polyline |
| `draw.triangle(surface, color, rect, direction="up", width=0)` | Triangle — direction: `"up"` `"down"` `"left"` `"right"` |
| `draw.shape(surface, color, shape_type, rect, width=0)` | Any Google Slides built-in shape (`"DIAMOND"`, `"STAR_5"`, `"HEXAGON"`, …) |
| `draw.progress_bar(surface, rect, value, max_value, fg_color, bg_color, border_radius=0)` | Filled progress bar |
| `draw.text(surface, text, rect, color, font_size=24, bold=False, italic=False, align="LEFT", vertical_align="MIDDLE")` | Text label |

`Color` supports arithmetic and conversion helpers: `lerp(other, t)`, `darken(f)`, `lighten(f)`, `with_alpha(a)`, `grayscale()`, `complementary()`.

`Rect` helpers: `scale_by(fx, fy)`, `padded(px, py)`, `clip(other)`, `union(other)`, `fit(other)`, `clamp(other)`, `contains(other)`, plus midpoint properties (`midleft`, `midright`, `midtop`, `midbottom`).

`Vector2` provides a full 2D vector type: arithmetic operators, `normalize()`, `dot()`, `cross()`, `distance_to()`, `lerp()`, `rotate(degrees)`, `reflect()`, `from_polar()`.

See [examples/snake_demo.py](https://github.com/sahilmenon/slide-games/blob/main/examples/snake_demo.py), [examples/pacman_demo.py](https://github.com/sahilmenon/slide-games/blob/main/examples/pacman_demo.py), and [examples/sokoban_demo.py](https://github.com/sahilmenon/slide-games/blob/main/examples/sokoban_demo.py) for complete rendering examples.

### Lightweight rendering hooks

For games that use the default grid renderer, override these instead of `render()`:

```python
def get_cell_color(self, state, ch: str, is_player: bool) -> dict | None:
    """Return an RGB dict to override a cell's fill, or None for the theme default."""
    if is_player:
        return {"red": 1.0, "green": 0.0, "blue": 0.5}
    return None

def get_cell_image_url(self, state, ch: str, is_player: bool) -> str | None:
    """Return a public image URL to overlay on a cell, or None."""
    if is_player:
        return "https://example.com/hero.png"
    return None

def get_extra_shapes(self, state) -> list[dict]:
    """Return extra shapes to draw on top of the grid."""
    return [
        {"type": "ellipse", "x": 2.1, "y": 1.1, "w": 0.8, "h": 0.8,
         "color": {"red": 1.0, "green": 0.0, "blue": 0.0}},
    ]

def show_win_banner(self, state) -> bool:
    """Return False to suppress the win banner (e.g. for loss states)."""
    return self.pellets <= state.eaten and state.player != state.ghost
```

---

## API reference

### `build_presentation`

```python
build_presentation(
    game,                              # BaseGame instance
    title="Slide Game",                # presentation title
    theme=DARK,                        # Theme object
    credentials_file="credentials.json",
    verbose=True,                      # print progress to stdout
    max_states=1_000,                  # hard cap — raises ValueError if exceeded
    progress_callback=None,            # fn(done, total, phase) — phase is "building" or "sending"
    retry_callback=None,               # fn(remaining_seconds) — called during rate-limit waits
) -> str                               # URL of the created presentation
```

### `build_campaign`

```python
build_campaign(
    games,                             # list[BaseGame] — one per level, in order
    title="Slide Game",
    theme=DARK,
    credentials_file="credentials.json",
    verbose=True,
    max_states=1_000,                  # per-level cap
    progress_callback=None,
    retry_callback=None,
) -> str                               # URL of the created presentation
```

The win slide of each level includes a **Next Level ►** button that jumps to the next level's starting position. The final level's win slide shows only "YOU WIN!" with no next-level button.

### Progress callbacks

```python
def my_progress(done: int, total: int, phase: str) -> None:
    # phase == "building"  →  done/total are state counts
    # phase == "sending"   →  done/total are API request counts
    print(f"{phase}: {done}/{total}")

def my_retry(remaining_seconds: int) -> None:
    print(f"Rate limited — retrying in {remaining_seconds}s")

url = build_campaign(levels, progress_callback=my_progress, retry_callback=my_retry)
```

---

## Named colours

The package exports 40+ named `Color` constants for convenience:

```python
from slide_games import (
    BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA,
    ORANGE, PURPLE, GRAY, LIGHT_GRAY, DARK_GRAY,
    GOLD, SILVER, BROWN, PINK, HOT_PINK, NAVY, TEAL,
    CORAL, SALMON, TOMATO, VIOLET, INDIGO, CRIMSON,
    SKY_BLUE, SLATE_GRAY, MINT, TURQUOISE, # … and more
)
```

---

## Themes

| Name     | Style                      |
|----------|----------------------------|
| `DARK`   | Dark navy/blue (default)   |
| `PACMAN` | Classic black + blue walls |
| `RETRO`  | Dark with orange walls     |

Create a custom theme:

```python
from slide_games import Theme
from slide_games.themes import rgb

MY_THEME = Theme(
    name="my_theme",
    background=rgb(10, 10, 30),
    wall=rgb(80, 40, 120),
    floor=rgb(20, 20, 50),
    player=rgb(255, 100, 0),
    goal=rgb(0, 220, 120),
    pellet=rgb(200, 200, 200),
    btn_active=rgb(80, 40, 120),
    btn_inactive=rgb(40, 40, 60),
    btn_text=rgb(255, 255, 255),
    title_text=rgb(255, 200, 50),
    win_text=rgb(255, 200, 50),
)
```

---

## State space guide

| Game type | States | Notes |
|-----------|--------|-------|
| Maze, 16×16 | ~511 | passable cells only |
| Maze, 20×16 | ~639 | |
| Maze, 25×20 | ~999 | |
| Snake, 3×3 grid | ~517 | all self-avoiding walk prefixes |
| Snake, 4×4 grid | ~5 000 | grows quickly with grid size |
| Pac-Man, 9×7, 2 pellets | ~491 | player × ghost × pellet states |
| Pac-Man, 15×11, 2 pellets | ~2 700 | positions × 2² pellet states |
| Sokoban, 7×7, 1 box | ~500 | player × box positions |
| Sokoban, 7×7, 2 boxes | ~5 000 | player × box² configurations |

Pass a higher `max_states` when you know the count is safe. BFS state discovery runs locally and is fast; the slow part is uploading content to the Google Slides API.

---

## Performance

The sending phase uploads slide content via `batchUpdate` calls to the Google Slides API (quota: **60 write calls/minute per user**). The builder uses a **global token-bucket rate limiter** (≤50 calls/minute, shared across all concurrent `build_campaign` calls) and sends up to **5 batches concurrently** (500 requests each) per demo. Requests retry automatically on rate-limit (429) and transient connection errors with exponential backoff.

For typical presentations (~500 states):
- Building phase (pure Python, BFS + rendering): a few seconds
- Sending phase (network-bound): roughly 1–3 minutes depending on API latency

---

## Running the demos

```bash
python examples/run_all_demos.py
```

Builds all four demos **in parallel** (~500 states each), with a live progress table that updates in real time. Each demo's URL is printed the moment it finishes.

| Demo | Grid / Level | ~States |
|------|-------------|---------|
| Maze Quest | 16×16 maze | 511 |
| Snake | 3×3 grid | 517 |
| Pac-Man | 9×7 figure-8 maze, 2 pellets | 491 |
| Sokoban | 7×7, 1 box | 600 |

Individual demos:

```bash
python examples/maze_demo.py
python examples/snake_demo.py
python examples/pacman_demo.py
python examples/sokoban_demo.py
```

---

## Running tests

```bash
pytest                             # run all tests
pytest --cov=slide_games           # with coverage report
```

No Google API credentials are required — all API calls are mocked.

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, code style, and PR guidelines. To report a security vulnerability, see [SECURITY.md](SECURITY.md).

Optional pre-commit hooks (ruff + mypy on every commit) — setup instructions in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## Publishing to PyPI

```bash
python -m build
twine upload dist/*
```

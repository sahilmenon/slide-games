"""Snake — eat the apple to grow and fill the grid!

Real snake mechanics: one apple at a time.  The snake moves normally —
the tail drops on every step unless the head lands on the apple, in
which case the snake grows by one.  After each apple is eaten the next
one spawns at the first empty cell in row-major order (top-left to
bottom-right), guaranteeing it is never inside the snake.

Demonstrates:
  - Color.lerp() for a smooth tail-to-head body gradient
  - Color.lighten() for per-segment shine highlights
  - draw.lines() to draw a connecting spine through body centres
  - draw.triangle() as a direction arrow on the head
  - draw.progress_bar() for the fill-the-grid HUD bar
  - Vector2 for head-direction computation

Win: fill the entire 2 × 5 grid (eat all 9 apples).
Lose: move into your own body → death slide → press any arrow to try again.
Moving into a wall is blocked (button stays disabled).

Grid: 2 × 5  (10 cells).
Approximate state count: ~502.

Run::

    python examples/snake_demo.py
"""
from __future__ import annotations
from dataclasses import dataclass
from slide_games import (
    build_presentation, BaseGame, Position,
    Color, Rect, Vector2, draw, SCREEN_W, NAV_RESERVED_Y,
)
from slide_games.themes import rgb, Theme


# ── layout ────────────────────────────────────────────────────────────────────

GRID_W, GRID_H = 2, 5

_CELL = min(
    (SCREEN_W - 200) // GRID_W,
    (NAV_RESERVED_Y - 120) // GRID_H,
)
_OX = (SCREEN_W - _CELL * GRID_W) // 2
_OY = 30

# ── colours ───────────────────────────────────────────────────────────────────

_BG         = Color(  8,  16,  8)
_GRID_BG    = Color( 18,  36, 18)
_GRID_LINE  = Color( 32,  58, 32)
_HEAD_COLOR = Color(  0, 245, 100)
_TAIL_COLOR = Color(  0,  80, 30)   # lerp start for body gradient
_FOOD_RED   = Color(190,  38,  38)
_FOOD_SHINE = Color(245, 110, 110)
_HUD_COLOR  = Color( 80, 255, 120)
_BAR_BG     = Color( 25,  50, 25)


# ── state ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SnakeState:
    body:  tuple[Position, ...]   # head first
    apple: Position | None        # None when grid is full (win)
    dead:  bool = False           # True = self-collision death screen


# ── helpers ───────────────────────────────────────────────────────────────────

_DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


# Single canonical dead state — all self-collisions map here; all 4 arrows try again
_DEAD = SnakeState(body=(Position(0, 0),), apple=None, dead=True)


def _current_apple(body_set: set, grid_w: int, grid_h: int) -> Position | None:
    """First empty cell in row-major order; None if grid is full (win)."""
    for y in range(grid_h):
        for x in range(grid_w):
            p = Position(x, y)
            if p not in body_set:
                return p
    return None


# ── game ──────────────────────────────────────────────────────────────────────

class SnakeGame(BaseGame):
    """Real snake: one apple at a time, tail drops unless eating.

    Win by growing the snake until it fills the whole grid.
    Moving into a wall or yourself leads to an error slide (Try Again).
    """

    def __init__(self, grid_w: int = GRID_W, grid_h: int = GRID_H):
        self.grid_w = grid_w
        self.grid_h = grid_h

    def get_initial_state(self) -> SnakeState:
        body = (Position(0, 0),)
        apple = _current_apple(set(body), self.grid_w, self.grid_h)
        return SnakeState(body=body, apple=apple)

    def get_transitions(self, state: SnakeState) -> dict[str, SnakeState | None]:
        if state.dead:
            init = self.get_initial_state()
            return {d: init for d in _DIRS}
        if self.is_terminal(state):
            return {d: None for d in _DIRS}

        body_set = set(state.body)
        apple    = state.apple
        tail     = state.body[-1]

        # Block the reverse direction (can't do 180°)
        blocked: str | None = None
        if len(state.body) > 1:
            nx, ny = state.body[1].x, state.body[1].y
            for d, (dx, dy) in _DIRS.items():
                if state.body[0].x + dx == nx and state.body[0].y + dy == ny:
                    blocked = d
                    break

        result: dict[str, SnakeState | None] = {}
        for d, (dx, dy) in _DIRS.items():
            if d == blocked:
                result[d] = None
                continue
            nh = Position(state.body[0].x + dx, state.body[0].y + dy)
            if not (0 <= nh.x < self.grid_w and 0 <= nh.y < self.grid_h):
                result[d] = None                        # wall
            elif nh in body_set and nh != tail:
                result[d] = _DEAD                       # self-collision → death screen
            elif nh == apple:
                new_body = (nh, *state.body)
                next_apple = _current_apple(set(new_body), self.grid_w, self.grid_h)
                result[d] = SnakeState(new_body, next_apple)        # grow
            else:
                result[d] = SnakeState((nh, *state.body[:-1]), apple)  # move
        return result

    def is_terminal(self, state: SnakeState) -> bool:
        return state.apple is None and not state.dead

    # ── render ────────────────────────────────────────────────────────────────

    def render(self, surface, state: SnakeState) -> None:
        if state.dead:
            surface.fill(_BG)
            cy = NAV_RESERVED_Y // 2 - 40
            draw.text(surface, "GAME OVER",
                      Rect(0, cy - 40, SCREEN_W, 80),
                      color=_FOOD_RED, font_size=64, bold=True, align="CENTER")
            draw.text(surface, "Press any arrow to try again",
                      Rect(0, cy + 50, SCREEN_W, 40),
                      color=_HUD_COLOR, font_size=22, align="CENTER")
            return

        cell = _CELL
        ox, oy = _OX, _OY
        pad = max(8, cell // 14)

        surface.fill(_BG)

        # Grid background
        draw.rect(surface, _GRID_BG,
                  Rect(ox, oy, cell * self.grid_w, cell * self.grid_h))

        # Grid lines
        for i in range(1, self.grid_w):
            x = ox + i * cell
            draw.line(surface, _GRID_LINE, (x, oy),
                      (x, oy + cell * self.grid_h), 2)
        for j in range(1, self.grid_h):
            y = oy + j * cell
            draw.line(surface, _GRID_LINE, (ox, y),
                      (ox + cell * self.grid_w, y), 2)

        # Single apple — fixed position until eaten
        apple = state.apple
        if apple is not None:
            cx = ox + apple.x * cell + cell // 2
            cy = oy + apple.y * cell + cell // 2
            r  = max(8, cell // 7)
            draw.circle(surface, _FOOD_RED,   (cx, cy), r)
            draw.circle(surface, _FOOD_SHINE,
                        (cx - r // 3, cy - r // 3), max(2, r // 4))

        # Spine — draw.lines() connecting body-segment centres (drawn first, behind segments)
        if len(state.body) >= 2:
            spine_pts = [
                (ox + seg.x * cell + cell // 2, oy + seg.y * cell + cell // 2)
                for seg in state.body
            ]
            draw.lines(surface, _TAIL_COLOR.darken(0.5), spine_pts,
                       width=max(3, cell // 10))

        # Snake body — smooth gradient via Color.lerp(), highlight via Color.lighten()
        n = len(state.body)
        for i, seg in enumerate(reversed(state.body)):
            is_head = (i == n - 1)
            t = i / max(n - 1, 1)
            color = _HEAD_COLOR if is_head else _TAIL_COLOR.lerp(_HEAD_COLOR, t)
            sx = ox + seg.x * cell + pad
            sy = oy + seg.y * cell + pad
            sw = cell - 2 * pad
            draw.rect(surface, color, Rect(sx, sy, sw, sw),
                      border_radius=max(6, cell // 10))
            # Shine highlight via Color.lighten()
            hl   = color.lighten(0.18)
            bpad = max(2, pad // 3)
            draw.rect(surface, hl,
                      Rect(sx + bpad, sy + bpad, sw - 2 * bpad,
                           max(2, sw // 6)))

        # Eyes on head
        if state.body:
            head = state.body[0]
            hx   = ox + head.x * cell + cell // 2
            hy   = oy + head.y * cell + cell // 2
            er   = max(5, cell // 11)
            off  = cell // 5
            for ex, ey in [(hx - off, hy - off), (hx + off, hy - off)]:
                draw.circle(surface, Color(10, 10, 10), (ex, ey), er)
                draw.circle(surface, Color(255, 255, 255),
                            (ex - er // 3, ey - er // 3), max(2, er // 3))

        # Direction arrow — draw.triangle() on head, using Vector2 for direction
        if len(state.body) >= 2:
            head_seg = state.body[0]
            neck_seg = state.body[1]
            dv = Vector2(head_seg.x - neck_seg.x, head_seg.y - neck_seg.y)
            if abs(dv.x) >= abs(dv.y):
                d_str = "right" if dv.x > 0 else "left"
            else:
                d_str = "down" if dv.y > 0 else "up"
            hx = ox + head_seg.x * cell + cell // 2
            hy = oy + head_seg.y * cell + cell // 2
            tr = max(8, cell // 7)
            draw.triangle(surface, Color(255, 255, 200),
                          Rect(hx - tr, hy - tr, tr * 2, tr * 2), direction=d_str)

        # HUD
        total  = self.grid_w * self.grid_h
        eaten  = len(state.body) - 1
        pct    = int(100 * len(state.body) / total)
        bar_y  = oy + cell * self.grid_h + 14
        bar_w  = cell * self.grid_w

        # Fill bar via draw.progress_bar()
        draw.progress_bar(surface, Rect(ox, bar_y + 34, bar_w, 18),
                          len(state.body), total, _HEAD_COLOR, _BAR_BG,
                          border_radius=8)
        draw.text(surface, f"Apples  {eaten} / {total - 1}   —   {pct}% full",
                  Rect(ox, bar_y, bar_w, 34),
                  color=_HUD_COLOR, font_size=20, bold=True, align="CENTER")


# ── theme + run ───────────────────────────────────────────────────────────────

SNAKE_THEME = Theme(
    name="snake",
    background=rgb(8, 16, 8),
    wall=rgb(30, 30, 30),
    floor=rgb(18, 36, 18),
    player=rgb(0, 200, 80),
    goal=rgb(185, 38, 38),
    pellet=rgb(185, 38, 38),
    btn_active=rgb(0, 130, 55),
    btn_inactive=rgb(28, 50, 28),
    btn_text=rgb(255, 255, 255),
    title_text=rgb(0, 220, 80),
    win_text=rgb(0, 245, 100),
)

if __name__ == "__main__":
    game   = SnakeGame()
    states = game.get_all_states()
    print(f"State count: {len(states)}")
    url = build_presentation(game, title="Snake", theme=SNAKE_THEME,
                             max_states=len(states) + 1)
    print(url)

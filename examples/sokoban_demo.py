"""Sokoban — push the box onto its target.

Demonstrates:
  - Vector2.distance_to() for box-to-target proximity
  - Color.lerp() to tint the box towards green as it nears its target
  - draw.shape() for the target marker (DIAMOND instead of cross)
  - draw.lines() for subtle floor-grid lines
  - draw.progress_bar() for the boxes-on-target HUD

Level (7 × 7)::

    #######     S = player start
    #.    #     B = box
    #     #     . = target square
    #  B  #
    #     #
    #  S  #
    #######

Solution hint: navigate above the box and push it left then up.
Approximate state count: ~600.

Run::

    python examples/sokoban_demo.py
"""
from __future__ import annotations
from dataclasses import dataclass
from slide_games import build_presentation, BaseGame, Position, Vector2
from slide_games.gfx import Color, Rect, draw, SCREEN_W, NAV_RESERVED_Y
from slide_games.themes import rgb, Theme


# ── colours ───────────────────────────────────────────────────────────────────

_BG          = Color( 30,  25,  20)
_FLOOR       = Color( 55,  48,  40)
_FLOOR_EDGE  = Color( 45,  38,  30)
_WALL        = Color( 60,  55,  50)
_WALL_FACE   = Color( 95,  85,  72)
_WALL_SHADOW = Color( 40,  35,  28)
_BOX         = Color(150,  85,  25)
_BOX_SHINE   = Color(195, 130,  60)
_BOX_ON_TGT  = Color( 55, 165,  55)
_BOX_ON_SHIN = Color( 95, 210,  95)
_TARGET      = Color(215, 180,  45)
_PLAYER      = Color(255, 215,   0)
_PLAYER_DARK = Color(180, 145,   0)
_PUPIL       = Color( 15,  15,  15)


# ── state ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SokoState:
    player: Position
    boxes:  frozenset[Position]


# ── game ──────────────────────────────────────────────────────────────────────

_DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

LEVEL_STR = """\
#######
#.    #
#     #
#  B  #
#     #
#  S  #
#######"""


class SokobanGame(BaseGame):
    """Sokoban: push every box onto a target square to win."""

    def __init__(self, level_str: str):
        rows = level_str.splitlines()
        self.grid_h = len(rows)
        self.grid_w = max(len(r) for r in rows)
        rows = [r.ljust(self.grid_w) for r in rows]

        walls:   set[Position] = set()
        targets: set[Position] = set()
        boxes:   set[Position] = set()
        start = Position(1, 1)

        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                pos = Position(x, y)
                if ch == "#":
                    walls.add(pos)
                elif ch == ".":
                    targets.add(pos)
                elif ch == "B":
                    boxes.add(pos)
                elif ch == "S":
                    start = pos
                elif ch == "X":          # box pre-placed on target
                    targets.add(pos)
                    boxes.add(pos)

        self.walls:       frozenset[Position] = frozenset(walls)
        self.targets:     frozenset[Position] = frozenset(targets)
        self._start:      Position            = start
        self._init_boxes: frozenset[Position] = frozenset(boxes)

    def get_initial_state(self) -> SokoState:
        return SokoState(self._start, self._init_boxes)

    def get_transitions(self, state: SokoState) -> dict[str, SokoState | None]:
        result: dict[str, SokoState | None] = {}
        for d, (dx, dy) in _DIRS.items():
            np = state.player.move(dx, dy)
            if np in self.walls:
                result[d] = None
            elif np in state.boxes:
                pushed = np.move(dx, dy)
                if pushed in self.walls or pushed in state.boxes:
                    result[d] = None
                else:
                    new_boxes = (state.boxes - {np}) | {pushed}
                    result[d] = SokoState(np, frozenset(new_boxes))
            else:
                result[d] = SokoState(np, state.boxes)
        return result

    def is_terminal(self, state: SokoState) -> bool:
        return self.targets.issubset(state.boxes)

    # ── rendering ─────────────────────────────────────────────────────────────

    def render(self, surface, state: SokoState) -> None:
        cell = min(
            (SCREEN_W - 100) // self.grid_w,
            (NAV_RESERVED_Y - 80) // self.grid_h,
        )
        ox = (SCREEN_W - cell * self.grid_w) // 2
        oy = max(10, (NAV_RESERVED_Y - 80 - cell * self.grid_h) // 2)
        pad = max(2, cell // 20)

        surface.fill(_BG)

        # ── floor background ──────────────────────────────────────────────
        draw.rect(surface, _FLOOR,
                  Rect(ox, oy, cell * self.grid_w, cell * self.grid_h))

        # ── grid cells ────────────────────────────────────────────────────
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                pos = Position(x, y)
                cx = ox + x * cell
                cy = oy + y * cell

                if pos in self.walls:
                    draw.rect(surface, _WALL, Rect(cx, cy, cell, cell))

                elif pos in self.targets and pos not in state.boxes:
                    # Target marker — DIAMOND shape via draw.shape()
                    dh = max(6, cell // 3)
                    mx, my = cx + cell // 2, cy + cell // 2
                    draw.shape(surface, _TARGET, "DIAMOND",
                               Rect(mx - dh, my - dh, dh * 2, dh * 2))

        # ── boxes — colour lerped toward green via Color.lerp() + Vector2 ─
        max_possible = Vector2(self.grid_w, self.grid_h).magnitude

        for box in state.boxes:
            cx = ox + box.x * cell
            cy = oy + box.y * cell
            on = box in self.targets

            if on:
                box_color = _BOX_ON_TGT
            else:
                # Proximity to nearest target via Vector2.distance_to()
                bv = Vector2(box.x, box.y)
                if self.targets:
                    min_dist  = min(bv.distance_to(Vector2(t.x, t.y))
                                    for t in self.targets)
                    proximity = max(0.0, 1.0 - min_dist / max_possible)
                else:
                    proximity = 0.0
                box_color = _BOX.lerp(_BOX_ON_TGT, proximity * 0.45)

            draw.rect(surface, box_color,
                      Rect(cx + pad, cy + pad, cell - 2*pad, cell - 2*pad),
                      border_radius=max(3, cell // 10))

        # ── player ────────────────────────────────────────────────────────
        px = ox + state.player.x * cell + cell // 2
        py = oy + state.player.y * cell + cell // 2
        r  = cell // 2 - pad * 2

        draw.circle(surface, _PLAYER, (px, py), r)

        # ── HUD — progress bar via draw.progress_bar() ────────────────────
        done  = sum(1 for b in state.boxes if b in self.targets)
        total = len(self.targets)
        hud_y = oy + cell * self.grid_h + 8
        draw.progress_bar(surface, Rect(ox, hud_y, cell * self.grid_w, 22),
                          done, total, _BOX_ON_TGT, Color(35, 28, 22),
                          border_radius=5)
        draw.text(surface, f"Boxes on target:  {done} / {total}",
                  Rect(ox, hud_y + 26, cell * self.grid_w, 26),
                  color=_TARGET, font_size=16, bold=True, align="CENTER")


# ── theme + run ───────────────────────────────────────────────────────────────

SOKOBAN_THEME = Theme(
    name="sokoban",
    background=rgb(30, 25, 20),
    wall=rgb(60, 55, 50),
    floor=rgb(55, 48, 40),
    player=rgb(255, 215, 0),
    goal=rgb(55, 165, 55),
    pellet=rgb(215, 180, 45),
    btn_active=rgb(140, 90, 30),
    btn_inactive=rgb(50, 42, 32),
    btn_text=rgb(255, 240, 200),
    title_text=rgb(255, 215, 0),
    win_text=rgb(80, 220, 80),
)

if __name__ == "__main__":
    game = SokobanGame(LEVEL_STR)
    states = game.get_all_states()
    print(f"State count: {len(states)}")
    url = build_presentation(game, title="Sokoban", theme=SOKOBAN_THEME,
                             max_states=len(states) + 1)
    print(url)

"""Pac-Man — eat both pellets before Blinky catches you!

Blinky (the red ghost) takes one BFS step toward your *current* position each
turn you move.  If you ever end up on the same cell as Blinky, you're caught —
press any arrow to restart.  Collect both pellets to win.

Demonstrates:
  - Vector2.distance_to() for live player-ghost proximity
  - Color.lerp() to tint the ghost orange-red as danger increases
  - draw.lines() for a decorative border around the maze
  - draw.triangle() as a direction indicator on Blinky
  - draw.progress_bar() for the pellet-collection HUD

Level: 9 × 7  figure-8 maze (~491 reachable states)
Ghost: BFS shortest-path chase of current player position
Win:   eat both pellets without being caught

Run::

    python examples/pacman_demo.py
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from slide_games import (
    build_presentation, BaseGame, Position,
    Color, Rect, Vector2, draw, SCREEN_W, NAV_RESERVED_Y,
)
from slide_games.themes import rgb, Theme


# ── level ─────────────────────────────────────────────────────────────────────
#
#   S = player start    p = pellet    . = floor    # = wall
#
LEVEL_STR = """\
#########
#S.....p#
#.#####.#
#.......#
#.#####.#
#.....p.#
#########"""

GHOST_START = Position(7, 5)   # Blinky starts bottom-right


# ── state ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GhostPacState:
    player: Position
    ghost:  Position
    eaten:  frozenset[Position]   # pellets collected so far


# ── helpers ───────────────────────────────────────────────────────────────────

_DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _parse_level(s: str):
    lines   = [ln for ln in s.splitlines() if ln.strip()]
    grid    = [list(row) for row in lines]
    start   = None
    pellets = []
    floor   = set()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != "#":
                floor.add(Position(x, y))
                if ch == "S":
                    start = Position(x, y)
                elif ch == "p":
                    pellets.append(Position(x, y))
    return grid, start, frozenset(pellets), frozenset(floor)


def _precompute_steps(floor: frozenset) -> dict:
    """For every (src, target) return the one BFS step src should take."""
    table: dict = {}
    for src in floor:
        prev: dict = {src: None}
        q = deque([src])
        while q:
            pos = q.popleft()
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nb = Position(pos.x + dx, pos.y + dy)
                if nb in floor and nb not in prev:
                    prev[nb] = pos
                    q.append(nb)
        for tgt in floor:
            if tgt == src:
                table[(src, tgt)] = src
            elif tgt not in prev:
                table[(src, tgt)] = src          # disconnected — stay
            else:
                step = tgt
                while prev[step] != src:
                    step = prev[step]
                table[(src, tgt)] = step
    return table


# ── game ──────────────────────────────────────────────────────────────────────

class GhostPacmanGame(BaseGame):
    """Pac-Man with one chasing ghost (Blinky).

    Each turn the player picks a direction.  Simultaneously, Blinky takes one
    BFS step toward the player's *current* position.  If the player and Blinky
    end up on the same cell the state is a loss — press any arrow to restart.
    Win by eating all pellets.
    """

    def __init__(self, level_str: str = LEVEL_STR,
                 ghost_start: Position = GHOST_START):
        self.grid, self._pstart, self.pellets, self._floor = _parse_level(level_str)
        self._gstart = ghost_start
        self._steps  = _precompute_steps(self._floor)

    def get_initial_state(self) -> GhostPacState:
        return GhostPacState(self._pstart, self._gstart, frozenset())

    def get_transitions(self, state: GhostPacState) -> dict:
        if self.is_terminal(state):
            return {d: None for d in _DIRS}

        result = {}
        for d, (dx, dy) in _DIRS.items():
            np = Position(state.player.x + dx, state.player.y + dy)
            if np not in self._floor:
                result[d] = None          # wall
                continue
            # Ghost chases the player's CURRENT position (one step behind)
            ng = self._steps[(state.ghost, state.player)]
            new_eaten = (state.eaten | {np}) if np in self.pellets else state.eaten
            result[d] = GhostPacState(np, ng, new_eaten)
        return result

    def is_terminal(self, state: GhostPacState) -> bool:
        return self.pellets <= state.eaten or state.player == state.ghost

    def show_win_banner(self, state: GhostPacState) -> bool:
        return self.pellets <= state.eaten and state.player != state.ghost

    # ── render ────────────────────────────────────────────────────────────────

    def render(self, surface, state: GhostPacState) -> None:
        rows = len(self.grid)
        cols = len(self.grid[0])
        cell = min(
            (SCREEN_W - 120) // cols,
            (NAV_RESERVED_Y - 80) // rows,
        )
        ox = (SCREEN_W - cell * cols) // 2
        oy = 20

        # ── caught overlay ────────────────────────────────────────────────
        if state.player == state.ghost:
            surface.fill(Color(10, 0, 0))
            cx, cy = SCREEN_W // 2, NAV_RESERVED_Y // 2 - 60
            gr = 100
            draw.circle(surface, Color(220, 40, 40), (cx, cy), gr)
            for ex_off in (-gr // 3, gr // 3):
                draw.circle(surface, Color(255, 255, 255),
                            (cx + ex_off, cy - gr // 5), max(5, gr // 5))
                draw.circle(surface, Color(20, 20, 200),
                            (cx + ex_off, cy - gr // 5), max(3, gr // 9))
            draw.circle(surface, Color(255, 220, 0), (cx + gr + 30, cy), 40)
            draw.circle(surface, Color(10, 0, 0),    (cx + gr + 55, cy), 20)
            draw.text(surface, "CAUGHT!",
                      Rect(0, cy + gr + 20, SCREEN_W, 90),
                      color=Color(255, 60, 60), font_size=64, bold=True,
                      align="CENTER")
            draw.text(surface, "Press any arrow to try again",
                      Rect(0, cy + gr + 115, SCREEN_W, 50),
                      color=Color(200, 120, 120), font_size=22,
                      align="CENTER")
            return

        surface.fill(Color(0, 0, 0))

        # Maze border via draw.lines()
        m = 3
        draw.lines(surface, Color(50, 50, 200), [
            (ox - m,            oy - m),
            (ox + cell*cols+m,  oy - m),
            (ox + cell*cols+m,  oy + cell*rows+m),
            (ox - m,            oy + cell*rows+m),
        ], width=3, closed=True)

        # Floor cells
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch != "#":
                    draw.rect(surface, Color(22, 22, 70),
                              Rect(ox + x*cell + 1, oy + y*cell + 1,
                                   cell - 2, cell - 2))

        # Uneaten pellets
        for p in self.pellets:
            if p not in state.eaten:
                cx = ox + p.x*cell + cell//2
                cy = oy + p.y*cell + cell//2
                r  = max(4, cell // 7)
                draw.circle(surface, Color(255, 255, 200), (cx, cy), r)
                draw.circle(surface, Color(255, 255, 120),
                            (cx - r//3, cy - r//3), max(2, r//3))

        # Player-ghost proximity via Vector2.distance_to()
        pv   = Vector2(state.player.x, state.player.y)
        gv   = Vector2(state.ghost.x,  state.ghost.y)
        dist = pv.distance_to(gv)
        # danger: 1.0 when adjacent, 0.0 when 5+ cells away
        danger = max(0.0, 1.0 - dist / 5.0)

        # Blinky — ghost colour lerps from deep-red to bright-orange as danger rises
        ghost_color = Color(220, 40, 40).lerp(Color(255, 140, 0), danger)
        gx = ox + state.ghost.x*cell + cell//2
        gy = oy + state.ghost.y*cell + cell//2
        gr = max(6, cell * 2 // 5)
        draw.circle(surface, ghost_color, (gx, gy), gr)
        for ex_off in (-gr//3, gr//3):
            draw.circle(surface, Color(255, 255, 255),
                        (gx+ex_off, gy-gr//5), max(3, gr//5))
            draw.circle(surface, Color(20, 20, 200),
                        (gx+ex_off, gy-gr//5), max(2, gr//9))

        # Ghost direction arrow via draw.triangle() + Vector2
        chase_vec = pv - gv
        if chase_vec.magnitude > 0:
            cv = chase_vec.normalize()
            if abs(cv.x) >= abs(cv.y):
                tri_dir = "right" if cv.x > 0 else "left"
            else:
                tri_dir = "down" if cv.y > 0 else "up"
            tr = max(5, gr // 3)
            draw.triangle(surface, Color(255, 255, 255),
                          Rect(gx - tr, gy - tr, tr * 2, tr * 2),
                          direction=tri_dir)

        # Player — yellow Pac-Man
        px = ox + state.player.x*cell + cell//2
        py = oy + state.player.y*cell + cell//2
        pr = max(6, cell * 2 // 5)
        draw.circle(surface, Color(255, 220, 0), (px, py), pr)
        draw.circle(surface, Color(0, 0, 0),
                    (px + pr//2, py), max(2, pr // 4))  # mouth cutout

        # HUD — pellet progress bar via draw.progress_bar()
        hud_y = oy + rows * cell + 12
        draw.progress_bar(surface, Rect(ox, hud_y, cell*cols, 18),
                          len(state.eaten), len(self.pellets),
                          Color(255, 255, 100), Color(30, 30, 80),
                          border_radius=8)
        draw.text(surface, f"Pellets  {len(state.eaten)} / {len(self.pellets)}",
                  Rect(ox, hud_y + 22, cell * cols, 26),
                  color=Color(255, 220, 50), font_size=22,
                  bold=True, align="CENTER")


# ── theme + run ───────────────────────────────────────────────────────────────

PAC_THEME = Theme(
    name="ghost_pacman",
    background=rgb(0,   0,   0),
    wall=       rgb(20,  20,  20),
    floor=      rgb(22,  22,  70),
    player=     rgb(255, 220,  0),
    goal=       rgb(255, 255, 200),
    pellet=     rgb(255, 255, 200),
    btn_active= rgb(60,  60,  180),
    btn_inactive=rgb(25, 25,  60),
    btn_text=   rgb(255, 255, 255),
    title_text= rgb(255, 220,  0),
    win_text=   rgb(255, 255, 100),
)

if __name__ == "__main__":
    game = GhostPacmanGame()
    states = game.get_all_states()
    print(f"State count: {len(states)}")
    url = build_presentation(game, title="Pac-Man", theme=PAC_THEME,
                             max_states=len(states) + 1)
    print(url)

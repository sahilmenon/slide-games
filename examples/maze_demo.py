"""Maze — navigate from S to G using the arrow buttons.

Demonstrates:
  - MazeGame subclass with a fully custom render()
  - draw.shape() for the player (DIAMOND) and goal (STAR_5)
  - draw.triangle() as a live compass arrow pointing toward the exit
  - draw.progress_bar() showing proximity to the goal
  - Color.lerp() for distance-based wall shading (applied to the background)
  - Local 7 × 7 view window (fog-of-war): only the area around the player is
    revealed; walls fill as the slide background, saving ~94 % of API requests
  - Vector2 for goal-direction calculation
  - draw.lines() for a decorative border around the maze

Level: 16 × 16  backtracker maze (~511 reachable states)

Run::

    python examples/maze_demo.py
"""
from slide_games import build_presentation, MazeGame, generate_maze, Position
from slide_games.gfx import Color, Rect, Vector2, draw, SCREEN_W, NAV_RESERVED_Y
from slide_games.themes import rgb, Theme


# ── colours ───────────────────────────────────────────────────────────────────

_BG        = Color( 10,  12,  20)
_WALL_FAR  = Color( 22,  32,  58)   # wall colour far from goal
_WALL_NEAR = Color( 38,  55,  95)   # wall colour near goal (lerp target)
_FLOOR     = Color( 15,  19,  34)
_PLAYER    = Color( 80, 200, 255)
_GOAL_CLR  = Color(255, 200,  50)
_COMPASS   = Color(255, 120,  60)
_BAR_FG    = Color( 80, 200, 255)
_BAR_BG    = Color( 20,  28,  50)
_BORDER    = Color( 45,  70, 130)
_HUD_TEXT  = Color(140, 175, 215)

_HUD_H = 80   # pixels reserved below the maze for HUD


# ── custom game ───────────────────────────────────────────────────────────────

class CustomMazeGame(MazeGame):
    """MazeGame with a fully custom render() that showcases the new drawing API."""

    def render(self, surface, state: Position) -> None:
        level = self.level
        cols, rows = level.width, level.height
        goal = level.find("G")

        # Local view window: show (2R+1)×(2R+1) cells centred on the player.
        # Walls are the slide background (no per-cell wall rects needed).
        R    = 3          # radius → 7×7 view
        VIEW = 2 * R + 1  # 7

        cell = min(
            (SCREEN_W - 80) // VIEW,
            (NAV_RESERVED_Y - _HUD_H - 10) // VIEW,
        )
        ox = (SCREEN_W - cell * VIEW) // 2
        oy = 8

        # ── closeness to goal for Color.lerp() ───────────────────────────
        if goal:
            max_d = rows + cols
            d_to_goal = abs(state.x - goal.x) + abs(state.y - goal.y)
            closeness = max(0.0, 1.0 - d_to_goal / max_d)
        else:
            closeness = 1.0

        # Wall colour via Color.lerp() fills the slide background — no per-cell
        # wall rects required; walls simply show through as the background.
        wall_color = _WALL_FAR.lerp(_WALL_NEAR, closeness)
        surface.fill(wall_color)

        # ── decorative border via draw.lines() ────────────────────────────
        m = 4
        draw.lines(surface, _BORDER, [
            (ox - m,             oy - m),
            (ox + cell*VIEW + m, oy - m),
            (ox + cell*VIEW + m, oy + cell*VIEW + m),
            (ox - m,             oy + cell*VIEW + m),
        ], width=4, closed=True)

        # ── local view: only floor cells in the (2R+1)² window ───────────
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                gx, gy = state.x + dx, state.y + dy
                if 0 <= gx < cols and 0 <= gy < rows:
                    if level.get(Position(gx, gy)) not in ("#", " "):
                        cx = ox + (dx + R) * cell
                        cy = oy + (dy + R) * cell
                        draw.rect(surface, _FLOOR, Rect(cx, cy, cell, cell))

        # ── goal — STAR_5 only when within view ──────────────────────────
        if (goal and
                abs(goal.x - state.x) <= R and
                abs(goal.y - state.y) <= R):
            gr = max(10, cell * 2 // 5)
            gx_px = ox + (goal.x - state.x + R) * cell + cell // 2
            gy_px = oy + (goal.y - state.y + R) * cell + cell // 2
            draw.shape(surface, _GOAL_CLR, "STAR_5",
                       Rect(gx_px - gr, gy_px - gr, gr * 2, gr * 2))

        # ── player — DIAMOND always at view centre ────────────────────────
        pr = max(10, cell * 2 // 5)
        sx = ox + R * cell + cell // 2
        sy = oy + R * cell + cell // 2
        draw.shape(surface, _PLAYER, "DIAMOND",
                   Rect(sx - pr, sy - pr, pr * 2, pr * 2))

        # ── HUD ───────────────────────────────────────────────────────────
        hud_y = oy + VIEW * cell + 10

        # Compass: draw.triangle() pointing toward goal via Vector2
        if goal and (goal.x != state.x or goal.y != state.y):
            dv = Vector2(goal.x - state.x, goal.y - state.y).normalize()
            if abs(dv.x) >= abs(dv.y):
                tri_dir = "right" if dv.x > 0 else "left"
            else:
                tri_dir = "down" if dv.y > 0 else "up"
            ar = max(14, cell // 3)
            draw.triangle(surface, _COMPASS,
                          Rect(SCREEN_W // 2 - ar, hud_y, ar * 2, ar),
                          direction=tri_dir)
            hud_y += ar + 8

        bar_w = cell * VIEW
        draw.progress_bar(surface, Rect(ox, hud_y, bar_w, 18),
                          int(closeness * 100), 100,
                          _BAR_FG, _BAR_BG, border_radius=9)
        draw.text(surface, "Proximity to exit",
                  Rect(ox, hud_y + 22, bar_w, 22),
                  color=_HUD_TEXT, font_size=14, align="CENTER")


# ── theme ─────────────────────────────────────────────────────────────────────

MAZE_THEME = Theme(
    name="maze_custom",
    background=rgb(10, 12, 20),
    wall=rgb(38, 55, 95),
    floor=rgb(15, 19, 34),
    player=rgb(80, 200, 255),
    goal=rgb(255, 200, 50),
    pellet=rgb(255, 200, 50),
    btn_active=rgb(50, 80, 140),
    btn_inactive=rgb(18, 24, 44),
    btn_text=rgb(200, 220, 255),
    title_text=rgb(80, 200, 255),
    win_text=rgb(255, 200, 50),
)

if __name__ == "__main__":
    maze  = generate_maze(16, 16, algorithm="backtracker", seed=7)
    game  = CustomMazeGame(maze)
    states = game.get_all_states()
    print(f"State count: {len(states)}")
    url = build_presentation(game, title="Maze", theme=MAZE_THEME,
                             max_states=len(states) + 1)
    print(url)

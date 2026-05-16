"""slide-games: Build interactive Google Slides arcade games in Python.

Quick start::

    from slide_games import build_presentation, MazeGame, Level, DARK

    level = Level.from_string(\"\"\"
    ##########
    #S.......#
    #.######.#
    #.......G#
    ##########
    \"\"\")

    url = build_presentation(MazeGame(level), title="My Maze", theme=DARK)
    print(url)

Custom games::

    from slide_games import build_presentation, BaseGame

    class MyGame(BaseGame):
        def get_initial_state(self): ...
        def get_transitions(self, state): ...   # return {dir: next_state | None}
        def is_terminal(self, state): ...

    url = build_presentation(MyGame(), title="My Game")
"""

__version__ = "0.1.0"

from .builder import build_campaign, build_presentation
from .games import ARROWS, DIRECTIONS, BaseGame, MazeGame, PacmanGame, PacmanState
from .gfx import (
    AQUA,
    # core colours
    BLACK,
    BLUE,
    BROWN,
    CHOCOLATE,
    CORAL,
    CRIMSON,
    CYAN,
    DARK_GRAY,
    DEEP_PINK,
    FUCHSIA,
    # extended palette
    GOLD,
    GRAY,
    GREEN,
    HOT_PINK,
    INDIGO,
    KHAKI,
    LIGHT_GRAY,
    LIME,
    MAGENTA,
    MAROON,
    MINT,
    NAV_RESERVED_Y,
    NAVY,
    OLIVE,
    ORANGE,
    ORCHID,
    PINK,
    PURPLE,
    RED,
    SALMON,
    SCREEN_H,
    # screen constants
    SCREEN_W,
    SILVER,
    SKY_BLUE,
    SLATE_GRAY,
    TAN,
    TEAL,
    TOMATO,
    TURQUOISE,
    VIOLET,
    WHITE,
    YELLOW,
    Color,
    Rect,
    Surface,
    Vector2,
    draw,
)
from .maze_gen import generate_maze
from .models import Level, Position
from .themes import DARK, PACMAN, RETRO, Theme

__all__ = [
    "build_presentation",
    "build_campaign",
    # maze generation
    "generate_maze",
    # games
    "BaseGame",
    "MazeGame",
    "PacmanGame",
    "PacmanState",
    "DIRECTIONS",
    "ARROWS",
    # models
    "Level",
    "Position",
    # themes
    "DARK",
    "PACMAN",
    "RETRO",
    "Theme",
    # pygame-like drawing API
    "Color",
    "Rect",
    "Surface",
    "draw",
    "Vector2",
    # core named colours
    "BLACK",
    "WHITE",
    "RED",
    "GREEN",
    "BLUE",
    "YELLOW",
    "CYAN",
    "MAGENTA",
    "ORANGE",
    "PURPLE",
    "GRAY",
    "LIGHT_GRAY",
    "DARK_GRAY",
    # extended palette
    "GOLD",
    "SILVER",
    "BROWN",
    "PINK",
    "HOT_PINK",
    "DEEP_PINK",
    "NAVY",
    "TEAL",
    "MAROON",
    "OLIVE",
    "LIME",
    "AQUA",
    "FUCHSIA",
    "CORAL",
    "SALMON",
    "TOMATO",
    "VIOLET",
    "INDIGO",
    "CRIMSON",
    "KHAKI",
    "ORCHID",
    "TURQUOISE",
    "CHOCOLATE",
    "TAN",
    "SKY_BLUE",
    "SLATE_GRAY",
    "MINT",
    # screen constants
    "SCREEN_W",
    "SCREEN_H",
    "NAV_RESERVED_Y",
]

from __future__ import annotations

from ..models import Level, Position
from .base import DIRECTIONS, BaseGame


class MazeGame(BaseGame):
    """Navigate through a maze from S to G.

    Example level string::

        ##########
        #S.......#
        #.######.#
        #.......G#
        ##########
    """

    def __init__(self, level: Level):
        self.level = level
        self._start = level.find("S") or Position(1, 1)

    def get_initial_state(self) -> Position:
        return self._start

    def get_transitions(self, pos: Position) -> dict[str, Position | None]:
        return {
            d: (pos.move(dx, dy) if self.level.is_passable(pos.move(dx, dy)) else None)
            for d, (dx, dy) in DIRECTIONS.items()
        }

    def is_terminal(self, pos: Position) -> bool:
        return self.level.get(pos) == "G"

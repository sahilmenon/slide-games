from __future__ import annotations

from dataclasses import dataclass

from ..models import Level, Position
from .base import DIRECTIONS, BaseGame


@dataclass(frozen=True)
class PacmanState:
    position: Position
    eaten: frozenset[Position]


class PacmanGame(BaseGame):
    """Pac-Man style game: eat all pellets to win.

    Use ``max_pellets`` to cap the number of tracked pellets and keep the
    state space manageable (state count = positions × 2^pellets).

    Example level string (S=start, p=pellet, G=goal/ghost)::

        #########
        #S.p.p.p#
        #.#####.#
        #p.....G#
        #########
    """

    def __init__(self, level: Level, max_pellets: int = 10):
        self.level = level
        self._start = level.find("S") or Position(1, 1)
        all_pellets = level.find_all("p")
        self.pellets: frozenset[Position] = frozenset(all_pellets[:max_pellets])

    def get_initial_state(self) -> PacmanState:
        return PacmanState(self._start, frozenset())

    def get_transitions(self, state: PacmanState) -> dict[str, PacmanState | None]:
        result: dict[str, PacmanState | None] = {}
        for d, (dx, dy) in DIRECTIONS.items():
            new_pos = state.position.move(dx, dy)
            if self.level.is_passable(new_pos):
                if new_pos in self.pellets:
                    new_eaten = state.eaten | frozenset([new_pos])
                else:
                    new_eaten = state.eaten
                result[d] = PacmanState(new_pos, new_eaten)
            else:
                result[d] = None
        return result

    def is_terminal(self, state: PacmanState) -> bool:
        return self.pellets.issubset(state.eaten)

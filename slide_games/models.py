from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def move(self, dx: int, dy: int) -> Position:
        return Position(self.x + dx, self.y + dy)


@dataclass
class Level:
    """Simple grid-based level.

    Cell characters:
      '#'  wall       '.'  floor
      'S'  start      'G'  goal
      'p'  pellet     ' '  void (treated as wall)
    """

    grid: list[list[str]]

    @classmethod
    def from_string(cls, s: str) -> Level:
        return cls(grid=[list(line) for line in s.strip().splitlines()])

    @property
    def width(self) -> int:
        return max(len(row) for row in self.grid)

    @property
    def height(self) -> int:
        return len(self.grid)

    def get(self, pos: Position) -> str:
        if 0 <= pos.y < self.height and 0 <= pos.x < len(self.grid[pos.y]):
            return self.grid[pos.y][pos.x]
        return "#"

    def is_passable(self, pos: Position) -> bool:
        return self.get(pos) not in ("#", " ")

    def find(self, ch: str) -> Position | None:
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == ch:
                    return Position(x, y)
        return None

    def find_all(self, ch: str) -> list[Position]:
        return [
            Position(x, y)
            for y, row in enumerate(self.grid)
            for x, cell in enumerate(row)
            if cell == ch
        ]

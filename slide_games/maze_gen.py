"""Algorithmic maze generation.

All generators return a :class:`~slide_games.models.Level` ready for
:class:`~slide_games.games.maze.MazeGame`.

The Level grid is always ``(2*width+1) × (2*height+1)`` characters — each maze
cell occupies an odd-indexed position and the even-indexed positions are walls
or carved passages.

Usage::

    from slide_games.maze_gen import generate_maze
    from slide_games import MazeGame, build_presentation, DARK

    level = generate_maze(width=12, height=9, algorithm="backtracker", seed=42)
    url = build_presentation(MazeGame(level), title="Generated Maze", theme=DARK)
"""

from __future__ import annotations

import random

from .models import Level


def generate_maze(
    width: int = 10,
    height: int = 8,
    algorithm: str = "backtracker",
    seed: int | None = None,
    start: tuple[int, int] = (0, 0),
    goal: tuple[int, int] | None = None,
) -> Level:
    """Generate a random perfect maze and return it as a :class:`~slide_games.models.Level`.

    Args:
        width: Passable columns.  Actual Level grid width = ``2*width + 1``.
        height: Passable rows.  Actual Level grid height = ``2*height + 1``.
        algorithm:
            ``"backtracker"`` — iterative DFS; long winding corridors, few
            dead ends (default).
            ``"prim"`` — randomised Prim's; short passages, many branches.
            ``"kruskal"`` — randomised Kruskal's; uniform spanning tree.
        seed: Integer seed for reproducibility.  ``None`` = random each time.
        start: ``(col, row)`` of the start cell in *maze* coordinates
            (not the expanded grid).  Defaults to top-left ``(0, 0)``.
        goal: ``(col, row)`` of the goal cell.  Defaults to bottom-right
            ``(width-1, height-1)``.

    Returns:
        A :class:`~slide_games.models.Level` with ``'#'`` walls, ``'.'``
        floors, ``'S'`` start, ``'G'`` goal.

    Raises:
        ValueError: For invalid dimensions, bad ``start``/``goal``, or unknown
            ``algorithm``.
    """
    if width < 1 or height < 1:
        raise ValueError("width and height must each be >= 1")

    sx, sy = start
    if not (0 <= sx < width and 0 <= sy < height):
        raise ValueError(f"start {start} is outside the maze ({width}×{height})")

    if goal is None:
        goal = (width - 1, height - 1)
    gx, gy = goal
    if not (0 <= gx < width and 0 <= gy < height):
        raise ValueError(f"goal {goal} is outside the maze ({width}×{height})")

    if start == goal:
        raise ValueError("start and goal must be different cells")

    rng = random.Random(seed)

    # Expanded grid: (2*width+1) cols × (2*height+1) rows, all walls initially.
    gw = 2 * width + 1
    gh = 2 * height + 1
    grid: list[list[str]] = [["#"] * gw for _ in range(gh)]

    # Open every cell centre.
    for cy in range(height):
        for cx in range(width):
            grid[2 * cy + 1][2 * cx + 1] = "."

    _ALGORITHMS = {
        "backtracker": _backtracker,
        "prim": _prim,
        "kruskal": _kruskal,
    }
    if algorithm not in _ALGORITHMS:
        raise ValueError(
            f"Unknown algorithm {algorithm!r}. Choose one of: {', '.join(_ALGORITHMS)}"
        )
    _ALGORITHMS[algorithm](grid, width, height, rng)

    grid[2 * sy + 1][2 * sx + 1] = "S"
    grid[2 * gy + 1][2 * gx + 1] = "G"

    return Level.from_string("\n".join("".join(row) for row in grid))


# ── algorithms ────────────────────────────────────────────────────────────────


def _carve(grid: list[list[str]], cx: int, cy: int, dx: int, dy: int) -> None:
    """Open the wall between cell (cx, cy) and its neighbour (cx+dx, cy+dy)."""
    grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = "."


def _backtracker(grid: list[list[str]], w: int, h: int, rng: random.Random) -> None:
    """Iterative depth-first search (recursive backtracker).

    Produces mazes with long winding corridors and a single, often
    distant, solution path.
    """
    visited = [[False] * w for _ in range(h)]
    stack = [(0, 0)]
    visited[0][0] = True
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    while stack:
        cx, cy = stack[-1]
        unvisited = [
            (cx + dx, cy + dy, dx, dy)
            for dx, dy in dirs
            if 0 <= cx + dx < w and 0 <= cy + dy < h and not visited[cy + dy][cx + dx]
        ]
        if unvisited:
            nx, ny, dx, dy = rng.choice(unvisited)
            _carve(grid, cx, cy, dx, dy)
            visited[ny][nx] = True
            stack.append((nx, ny))
        else:
            stack.pop()


def _prim(grid: list[list[str]], w: int, h: int, rng: random.Random) -> None:
    """Randomised Prim's algorithm.

    Produces mazes with many short branches radiating from a central
    trunk — visually bushier than backtracker.
    """
    visited = [[False] * w for _ in range(h)]
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    sx, sy = rng.randint(0, w - 1), rng.randint(0, h - 1)
    visited[sy][sx] = True

    # Each frontier entry: (from_cx, from_cy, to_cx, to_cy)
    frontier = [
        (sx, sy, sx + dx, sy + dy) for dx, dy in dirs if 0 <= sx + dx < w and 0 <= sy + dy < h
    ]

    while frontier:
        idx = rng.randrange(len(frontier))
        frontier[idx], frontier[-1] = frontier[-1], frontier[idx]
        fx, fy, tx, ty = frontier.pop()

        if visited[ty][tx]:
            continue

        _carve(grid, fx, fy, tx - fx, ty - fy)
        visited[ty][tx] = True

        for dx, dy in dirs:
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                frontier.append((tx, ty, nx, ny))


def _kruskal(grid: list[list[str]], w: int, h: int, rng: random.Random) -> None:
    """Randomised Kruskal's algorithm.

    Treats each cell as a set and merges them by randomly removing
    walls — produces a uniform spanning tree with no statistical bias
    toward any path structure.
    """
    parent = list(range(w * h))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        # path compression
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a: int, b: int) -> bool:
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        parent[ra] = rb
        return True

    walls = [
        (cx, cy, cx + dx, cy + dy)
        for cy in range(h)
        for cx in range(w)
        for dx, dy in ((1, 0), (0, 1))
        if cx + dx < w and cy + dy < h
    ]
    rng.shuffle(walls)

    for fx, fy, tx, ty in walls:
        if union(fy * w + fx, ty * w + tx):
            _carve(grid, fx, fy, tx - fx, ty - fy)

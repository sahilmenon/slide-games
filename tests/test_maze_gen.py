"""Tests for algorithmic maze generation."""

import pytest

from slide_games.games.maze import MazeGame
from slide_games.maze_gen import generate_maze
from slide_games.models import Level, Position

# ── helpers ───────────────────────────────────────────────────────────────────


def _all_reachable_from(level: Level, pos: Position) -> set[Position]:
    """BFS from pos over passable cells; returns all reachable positions."""
    visited = {pos}
    queue = [pos]
    while queue:
        cur = queue.pop(0)
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nb = Position(cur.x + dx, cur.y + dy)
            if nb not in visited and level.is_passable(nb):
                visited.add(nb)
                queue.append(nb)
    return visited


# ── basic contract ────────────────────────────────────────────────────────────


class TestGenerateMazeContract:
    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_returns_level(self, algo):
        level = generate_maze(4, 4, algorithm=algo, seed=0)
        assert isinstance(level, Level)

    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_grid_dimensions(self, algo):
        level = generate_maze(width=5, height=3, algorithm=algo, seed=1)
        assert level.width == 2 * 5 + 1
        assert level.height == 2 * 3 + 1

    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_has_start_and_goal(self, algo):
        level = generate_maze(5, 5, algorithm=algo, seed=2)
        starts = level.find_all("S")
        goals = level.find_all("G")
        assert len(starts) == 1
        assert len(goals) == 1

    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_perfect_maze_is_fully_connected(self, algo):
        """Every passable cell is reachable from S (perfect maze = connected)."""
        level = generate_maze(6, 5, algorithm=algo, seed=3)
        start = level.find("S")
        reachable = _all_reachable_from(level, start)
        passable = {
            Position(x, y)
            for y in range(level.height)
            for x in range(level.width)
            if level.is_passable(Position(x, y))
        }
        assert reachable == passable

    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_goal_reachable_from_start(self, algo):
        level = generate_maze(5, 5, algorithm=algo, seed=4)
        game = MazeGame(level)
        states = game.get_all_states()
        goal = level.find("G")
        assert goal in states


# ── reproducibility ───────────────────────────────────────────────────────────


class TestSeedReproducibility:
    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_same_seed_same_maze(self, algo):
        a = generate_maze(6, 6, algorithm=algo, seed=99)
        b = generate_maze(6, 6, algorithm=algo, seed=99)
        assert a.grid == b.grid

    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_different_seeds_usually_differ(self, algo):
        a = generate_maze(8, 8, algorithm=algo, seed=1)
        b = generate_maze(8, 8, algorithm=algo, seed=2)
        assert a.grid != b.grid


# ── custom start / goal ───────────────────────────────────────────────────────


class TestCustomStartGoal:
    def test_custom_start_position(self):
        level = generate_maze(5, 5, seed=0, start=(2, 2))
        start = level.find("S")
        assert start == Position(2 * 2 + 1, 2 * 2 + 1)

    def test_custom_goal_position(self):
        level = generate_maze(5, 5, seed=0, goal=(1, 3))
        goal = level.find("G")
        assert goal == Position(2 * 1 + 1, 2 * 3 + 1)

    def test_default_goal_is_bottom_right(self):
        w, h = 4, 3
        level = generate_maze(w, h, seed=0)
        goal = level.find("G")
        assert goal == Position(2 * (w - 1) + 1, 2 * (h - 1) + 1)

    def test_out_of_bounds_start_raises(self):
        with pytest.raises(ValueError, match="start"):
            generate_maze(4, 4, start=(5, 0))

    def test_out_of_bounds_goal_raises(self):
        with pytest.raises(ValueError, match="goal"):
            generate_maze(4, 4, goal=(0, 10))

    def test_start_equals_goal_raises(self):
        with pytest.raises(ValueError):
            generate_maze(4, 4, start=(1, 1), goal=(1, 1))


# ── validation ────────────────────────────────────────────────────────────────


class TestValidation:
    def test_zero_width_raises(self):
        with pytest.raises(ValueError):
            generate_maze(0, 4)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError):
            generate_maze(4, 0)

    def test_unknown_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unknown algorithm"):
            generate_maze(4, 4, algorithm="bogus")

    def test_1x1_maze(self):
        """Degenerate case: single cell, start == goal not allowed but 1×1 is fine
        if start and goal differ — which they can't for a 1×1 maze."""
        with pytest.raises(ValueError):
            generate_maze(1, 1)  # start=(0,0) == goal=(0,0)


# ── MazeGame compatibility ────────────────────────────────────────────────────


class TestMazeGameIntegration:
    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_can_build_maze_game(self, algo):
        level = generate_maze(5, 4, algorithm=algo, seed=7)
        game = MazeGame(level)
        assert game.get_initial_state() == level.find("S")
        assert game.is_terminal(level.find("G"))

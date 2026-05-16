from slide_games.games.base import ARROWS, DIRECTIONS
from slide_games.games.maze import MazeGame
from slide_games.games.pacman import PacmanGame, PacmanState
from slide_games.models import Level, Position

# ── fixtures ──────────────────────────────────────────────────────────────────

MAZE = Level.from_string("""\
#####
#S..#
#.###
#..G#
#####""")
# S=(1,1)  G=(3,3)
# From (1,1): right=(2,1)✓  down=(1,2)✓  up=wall  left=wall

PACMAN_LEVEL = Level.from_string("""\
#####
#Sp.#
#..p#
#####""")
# S=(1,1)  pellets at (2,1) and (3,2)


# ── BaseGame contract ─────────────────────────────────────────────────────────


class TestBaseGameContract:
    def test_all_four_directions_returned(self):
        game = MazeGame(MAZE)
        t = game.get_transitions(Position(1, 1))
        assert set(t.keys()) == {"up", "down", "left", "right"}

    def test_directions_constant_keys(self):
        assert set(DIRECTIONS.keys()) == {"up", "down", "left", "right"}

    def test_arrows_constant_keys(self):
        assert set(ARROWS.keys()) == {"up", "down", "left", "right"}

    def test_initial_state_is_first_bfs_result(self):
        game = MazeGame(MAZE)
        states = game.get_all_states()
        assert states[0] == game.get_initial_state()

    def test_all_states_reachable_and_passable(self):
        game = MazeGame(MAZE)
        for s in game.get_all_states():
            assert MAZE.is_passable(s)

    def test_bfs_no_duplicates(self):
        game = MazeGame(MAZE)
        states = game.get_all_states()
        assert len(states) == len(set(states))


# ── MazeGame ─────────────────────────────────────────────────────────────────


class TestMazeGame:
    def test_initial_state(self):
        assert MazeGame(MAZE).get_initial_state() == Position(1, 1)

    def test_transitions_passable_directions(self):
        t = MazeGame(MAZE).get_transitions(Position(1, 1))
        assert t["right"] == Position(2, 1)
        assert t["down"] == Position(1, 2)

    def test_transitions_blocked_directions(self):
        t = MazeGame(MAZE).get_transitions(Position(1, 1))
        assert t["up"] is None
        assert t["left"] is None

    def test_is_terminal_goal(self):
        assert MazeGame(MAZE).is_terminal(Position(3, 3))

    def test_is_terminal_non_goal(self):
        assert not MazeGame(MAZE).is_terminal(Position(1, 1))

    def test_goal_reachable(self):
        game = MazeGame(MAZE)
        assert Position(3, 3) in game.get_all_states()

    def test_fallback_start_when_no_S(self):
        level = Level.from_string("#####\n#...#\n#####")
        game = MazeGame(level)
        assert game.get_initial_state() == Position(1, 1)


# ── PacmanGame ────────────────────────────────────────────────────────────────


class TestPacmanGame:
    def test_initial_state(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        state = game.get_initial_state()
        assert state.position == Position(1, 1)
        assert state.eaten == frozenset()

    def test_max_pellets_cap(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=1)
        assert len(game.pellets) == 1

    def test_moving_onto_pellet_marks_eaten(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        state = game.get_initial_state()
        next_state = game.get_transitions(state)["right"]  # (2,1) has pellet
        assert next_state is not None
        assert Position(2, 1) in next_state.eaten

    def test_revisiting_eaten_pellet_not_double_counted(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        s0 = game.get_initial_state()
        s1 = game.get_transitions(s0)["right"]  # eat pellet at (2,1)
        s2 = game.get_transitions(s1)["left"]  # back to (1,1)
        s3 = game.get_transitions(s2)["right"]  # revisit (2,1)
        assert s3 is not None
        assert s3.eaten == s1.eaten  # still just one pellet eaten

    def test_moving_onto_floor_does_not_add_eaten(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        state = game.get_initial_state()
        next_state = game.get_transitions(state)["down"]  # (1,2) = floor
        assert next_state is not None
        assert next_state.eaten == frozenset()

    def test_blocked_direction_returns_none(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        state = game.get_initial_state()
        assert game.get_transitions(state)["left"] is None  # wall at (0,1)

    def test_is_terminal_all_eaten(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        full_eaten = PacmanState(Position(1, 1), game.pellets)
        assert game.is_terminal(full_eaten)

    def test_is_not_terminal_partial(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        one_eaten = PacmanState(Position(1, 1), frozenset([list(game.pellets)[0]]))
        assert not game.is_terminal(one_eaten)

    def test_is_not_terminal_empty(self):
        game = PacmanGame(PACMAN_LEVEL, max_pellets=2)
        assert not game.is_terminal(game.get_initial_state())


class TestPacmanState:
    def test_hashable(self):
        s1 = PacmanState(Position(1, 1), frozenset([Position(2, 2)]))
        s2 = PacmanState(Position(1, 1), frozenset([Position(2, 2)]))
        assert s1 == s2
        assert hash(s1) == hash(s2)

    def test_deduplication_in_set(self):
        s1 = PacmanState(Position(1, 1), frozenset())
        s2 = PacmanState(Position(1, 1), frozenset())
        assert len({s1, s2}) == 1

    def test_different_eaten_not_equal(self):
        s1 = PacmanState(Position(1, 1), frozenset([Position(2, 2)]))
        s2 = PacmanState(Position(1, 1), frozenset())
        assert s1 != s2

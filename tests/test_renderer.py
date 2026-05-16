"""Tests for the renderer.

No Google API calls are made here — we just inspect the structure of the
batchUpdate request dicts that the renderer produces.
"""

import pytest

from slide_games.games.maze import MazeGame
from slide_games.games.pacman import PacmanGame, PacmanState
from slide_games.maze_gen import generate_maze
from slide_games.models import Level, Position
from slide_games.renderer import Renderer
from slide_games.themes import DARK, PACMAN

# ── fixtures ──────────────────────────────────────────────────────────────────

MAZE = Level.from_string("""\
#####
#S..#
#.###
#..G#
#####""")
# S=(1,1)  G=(3,3)
# From (1,1): right and down are passable; up and left are walls.


def _game_and_renderer(theme=DARK):
    game = MazeGame(MAZE)
    renderer = Renderer(game, theme)
    return game, renderer


def _state_to_slide(game):
    return {s: f"slide_{i}" for i, s in enumerate(game.get_all_states())}


def _req_key(req):
    return next(iter(req))


def _all_keys(reqs):
    return [_req_key(r) for r in reqs]


def _link_targets(reqs):
    """Collect pageObjectId values from text-level link requests."""
    return [
        r["updateTextStyle"]["style"]["link"]["pageObjectId"]
        for r in reqs
        if _req_key(r) == "updateTextStyle"
        and "link" in r["updateTextStyle"].get("style", {})
        and "pageObjectId" in r["updateTextStyle"]["style"]["link"]
    ]


# ── title slide ───────────────────────────────────────────────────────────────


class TestRenderTitle:
    def test_returns_nonempty_list(self):
        game, r = _game_and_renderer()
        reqs = r.render_title("t_slide", "init_slide", "My Game")
        assert isinstance(reqs, list)
        assert len(reqs) > 0

    def test_has_page_background(self):
        game, r = _game_and_renderer()
        reqs = r.render_title("t_slide", "init_slide", "My Game")
        assert "updatePageProperties" in _all_keys(reqs)

    def test_has_exactly_one_link_to_initial_slide(self):
        game, r = _game_and_renderer()
        reqs = r.render_title("t_slide", "init_slide", "My Game")
        targets = _link_targets(reqs)
        assert targets == ["init_slide"]

    def test_title_text_in_insert_text(self):
        game, r = _game_and_renderer()
        reqs = r.render_title("t_slide", "init_slide", "My Game")
        texts = [req["insertText"]["text"] for req in reqs if "insertText" in req]
        assert "My Game" in texts

    def test_start_button_text(self):
        game, r = _game_and_renderer()
        reqs = r.render_title("t_slide", "init_slide", "My Game")
        texts = [req["insertText"]["text"] for req in reqs if "insertText" in req]
        assert any(t.upper() in ("PLAY", "START") for t in texts)


# ── game state slide ──────────────────────────────────────────────────────────


class TestRenderState:
    def test_returns_nonempty_list(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        assert isinstance(reqs, list)
        assert len(reqs) > 0

    def test_has_page_background(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        assert "updatePageProperties" in _all_keys(reqs)

    def test_links_match_passable_direction_count(self):
        """Exactly one shape link per passable direction."""
        game, r = _game_and_renderer()
        state = game.get_initial_state()  # (1,1): right + down passable
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        passable = sum(1 for ns in game.get_transitions(state).values() if ns is not None)
        assert len(_link_targets(reqs)) == passable

    def test_link_targets_exist_in_state_map(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        valid_slide_ids = set(s2s.values())
        for target in _link_targets(reqs):
            assert target in valid_slide_ids

    def test_fully_blocked_state_has_no_links(self):
        """A state surrounded by walls on all sides should produce zero links."""
        # Build a level where start is completely walled in
        level = Level.from_string("#####\n##S##\n#####")
        game = MazeGame(level)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = {state: "only_slide"}
        reqs = r.render_state("only_slide", state, s2s)
        assert _link_targets(reqs) == []

    def test_terminal_state_has_win_text(self):
        game, r = _game_and_renderer()
        goal = Position(3, 3)
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[goal], goal, s2s)
        texts = [req["insertText"]["text"] for req in reqs if "insertText" in req]
        assert any("WIN" in t.upper() for t in texts)

    def test_non_terminal_state_no_win_text(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        texts = [req["insertText"]["text"] for req in reqs if "insertText" in req]
        assert not any("WIN" in t.upper() for t in texts)

    def test_terminal_with_next_level_has_button(self):
        """Win slide with next_level_slide_id includes a link to that slide."""
        game, r = _game_and_renderer()
        goal = Position(3, 3)
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[goal], goal, s2s, next_level_slide_id="next_lvl")
        targets = _link_targets(reqs)
        assert "next_lvl" in targets

    def test_terminal_without_next_level_no_extra_link(self):
        """Win slide without next_level_slide_id has no next-level link."""
        game, r = _game_and_renderer()
        goal = Position(3, 3)
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[goal], goal, s2s)
        # No links at all on a fully blocked goal (all transitions hit walls)
        targets = _link_targets(reqs)
        assert "next_lvl" not in targets

    def test_non_terminal_next_level_id_ignored(self):
        """next_level_slide_id is silently ignored for non-terminal states."""
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s, next_level_slide_id="next_lvl")
        targets = _link_targets(reqs)
        assert "next_lvl" not in targets

    def test_next_level_button_text(self):
        """The next-level button contains 'NEXT' or 'LEVEL' in its label."""
        game, r = _game_and_renderer()
        goal = Position(3, 3)
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[goal], goal, s2s, next_level_slide_id="next_lvl")
        texts = [req["insertText"]["text"] for req in reqs if "insertText" in req]
        assert any("NEXT" in t.upper() or "LEVEL" in t.upper() for t in texts)

    def test_grid_cells_created_for_every_cell(self):
        """Grid background + one rect per wall/goal/player cell (floor cells skipped)."""
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        rect_creates = [
            req
            for req in reqs
            if _req_key(req) == "createShape" and req["createShape"]["shapeType"] == "RECTANGLE"
        ]
        # grid background (1) + walls + goal + player position
        wall_count = sum(1 for row in MAZE.grid for ch in row if ch == "#")
        assert len(rect_creates) >= 1 + wall_count + 1 + 1  # bg + walls + goal + player

    def test_four_nav_buttons_created(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        round_rects = [
            req
            for req in reqs
            if _req_key(req) == "createShape"
            and req["createShape"]["shapeType"] == "ROUND_RECTANGLE"
        ]
        assert len(round_rects) == 4

    def test_slide_id_used_in_page_background(self):
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        slide_id = s2s[state]
        reqs = r.render_state(slide_id, state, s2s)
        bg_reqs = [req for req in reqs if _req_key(req) == "updatePageProperties"]
        assert all(req["updatePageProperties"]["objectId"] == slide_id for req in bg_reqs)


# ── pacman-specific rendering ─────────────────────────────────────────────────


class TestPacmanRenderer:
    LEVEL = Level.from_string("""\
#####
#Sp.#
#..p#
#####""")

    def test_uneaten_pellet_creates_ellipse(self):
        game = PacmanGame(self.LEVEL, max_pellets=2)
        r = Renderer(game, PACMAN)
        state = game.get_initial_state()
        s2s = {s: f"s{i}" for i, s in enumerate(game.get_all_states())}
        reqs = r.render_state(s2s[state], state, s2s)
        ellipses = [
            req
            for req in reqs
            if _req_key(req) == "createShape" and req["createShape"]["shapeType"] == "ELLIPSE"
        ]
        assert len(ellipses) == len(game.pellets)

    def test_eaten_pellet_no_ellipse(self):
        game = PacmanGame(self.LEVEL, max_pellets=2)
        r = Renderer(game, PACMAN)
        all_eaten = PacmanState(
            game.get_initial_state().position,
            game.pellets,
        )
        s2s = {s: f"s{i}" for i, s in enumerate(game.get_all_states())}
        # eaten state might not be in the BFS (depends on map), so add it manually
        s2s[all_eaten] = "eaten_slide"
        reqs = r.render_state("eaten_slide", all_eaten, s2s)
        ellipses = [
            req
            for req in reqs
            if _req_key(req) == "createShape" and req["createShape"]["shapeType"] == "ELLIPSE"
        ]
        assert len(ellipses) == 0


# ── sprite / image overlay ────────────────────────────────────────────────────


class TestCellImageUrl:
    def test_no_image_url_no_create_image(self):
        """Default game (no override) produces zero createImage requests."""
        game, r = _game_and_renderer()
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        assert not any(_req_key(req) == "createImage" for req in reqs)

    def test_image_url_for_player_creates_image(self):
        """Overriding get_cell_image_url for the player cell yields createImage."""
        PLAYER_URL = "https://example.com/player.png"

        class SpriteGame(MazeGame):
            def get_cell_image_url(self, state, ch, is_player):
                return PLAYER_URL if is_player else None

        game = SpriteGame(MAZE)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        image_reqs = [req for req in reqs if _req_key(req) == "createImage"]
        assert len(image_reqs) == 1
        assert image_reqs[0]["createImage"]["url"] == PLAYER_URL

    def test_image_url_for_all_walls(self):
        """One createImage per wall cell when every wall gets a sprite."""
        WALL_URL = "https://example.com/wall.png"

        class WallSpriteGame(MazeGame):
            def get_cell_image_url(self, state, ch, is_player):
                return WALL_URL if ch == "#" else None

        game = WallSpriteGame(MAZE)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        image_reqs = [req for req in reqs if _req_key(req) == "createImage"]
        wall_count = sum(1 for row in MAZE.grid for ch in row if ch == "#")
        assert len(image_reqs) == wall_count

    def test_create_image_url_matches(self):
        """The URL in the createImage request matches what get_cell_image_url returns."""
        GOAL_URL = "https://example.com/goal.png"

        class GoalSpriteGame(MazeGame):
            def get_cell_image_url(self, state, ch, is_player):
                return GOAL_URL if ch == "G" else None

        game = GoalSpriteGame(MAZE)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        image_reqs = [req for req in reqs if _req_key(req) == "createImage"]
        assert len(image_reqs) == 1
        assert image_reqs[0]["createImage"]["url"] == GOAL_URL


# ── generated maze rendering ──────────────────────────────────────────────────


class TestGeneratedMazeRenderer:
    @pytest.mark.parametrize("algo", ["backtracker", "prim", "kruskal"])
    def test_generated_maze_renders_without_error(self, algo):
        level = generate_maze(4, 4, algorithm=algo, seed=0)
        game = MazeGame(level)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        assert len(reqs) > 0

    def test_generated_maze_has_correct_cell_count(self):
        level = generate_maze(3, 3, seed=0)
        game = MazeGame(level)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = _state_to_slide(game)
        reqs = r.render_state(s2s[state], state, s2s)
        rect_creates = [
            req
            for req in reqs
            if _req_key(req) == "createShape" and req["createShape"]["shapeType"] == "RECTANGLE"
        ]
        # grid background (1) + all wall cells + goal + player
        wall_count = sum(1 for row in level.grid for ch in row if ch == "#")
        assert len(rect_creates) >= 1 + wall_count + 1

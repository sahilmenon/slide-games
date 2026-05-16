"""Tests for the builder.

SlidesClient is mocked so no Google API credentials are needed.
"""

from unittest.mock import MagicMock, patch

import pytest

from slide_games.builder import build_campaign, build_presentation
from slide_games.games.maze import MazeGame
from slide_games.models import Level

# ── levels ────────────────────────────────────────────────────────────────────

# 2 reachable states: S and G
TINY = Level.from_string("""\
###
#S#
#G#
###""")

# ~56 reachable cells — useful for max_states tests
LARGE = Level.from_string("""\
##########
#S.......#
#........#
#........#
#........#
#........#
#........#
#........#
#.......G#
##########""")


# ── helpers ───────────────────────────────────────────────────────────────────


def _mock_client():
    c = MagicMock()
    c.create_presentation.return_value = {
        "presentationId": "fake_prs_id",
        "slides": [{"objectId": "default_slide_id"}],
    }
    c.batch_update.return_value = {}
    c.url.return_value = "https://docs.google.com/presentation/d/fake_prs_id/edit"
    return c


def _run(game, **kwargs):
    with patch("slide_games.builder.SlidesClient") as MockClient:
        mock = _mock_client()
        MockClient.return_value = mock
        url = build_presentation(
            game,
            credentials_file="fake.json",
            verbose=False,
            **kwargs,
        )
    return url, mock


# ── max_states guard ──────────────────────────────────────────────────────────


class TestMaxStates:
    def test_exceeding_limit_raises_before_api(self):
        game = MazeGame(LARGE)
        with patch("slide_games.builder.SlidesClient") as MockClient:
            with pytest.raises(ValueError, match="max_states"):
                build_presentation(game, max_states=5, credentials_file="fake.json")
            MockClient.assert_not_called()

    def test_error_message_contains_actual_count(self):
        game = MazeGame(LARGE)
        state_count = len(game.get_all_states())
        with pytest.raises(ValueError, match=str(state_count)):
            _run(game, max_states=5)

    def test_within_limit_does_not_raise(self):
        game = MazeGame(TINY)
        url, _ = _run(game, max_states=10)
        assert url  # returned without error

    def test_exact_limit_does_not_raise(self):
        game = MazeGame(TINY)
        count = len(game.get_all_states())
        url, _ = _run(game, max_states=count)
        assert url

    def test_one_over_limit_raises(self):
        game = MazeGame(TINY)
        count = len(game.get_all_states())
        with pytest.raises(ValueError):
            _run(game, max_states=count - 1)


# ── API call structure ────────────────────────────────────────────────────────


class TestBuildCallsApi:
    def test_creates_presentation(self):
        game = MazeGame(TINY)
        _, mock = _run(game)
        mock.create_presentation.assert_called_once()

    def test_batch_update_called_at_least_twice(self):
        """Once for inserting/deleting slides, at least once for content."""
        game = MazeGame(TINY)
        _, mock = _run(game)
        assert mock.batch_update.call_count >= 2

    def test_delete_default_slide_in_first_batch(self):
        game = MazeGame(TINY)
        _, mock = _run(game)
        first_batch_requests = mock.batch_update.call_args_list[0][0][1]
        delete_reqs = [r for r in first_batch_requests if "deleteObject" in r]
        assert len(delete_reqs) == 1
        assert delete_reqs[0]["deleteObject"]["objectId"] == "default_slide_id"

    def test_insert_slides_count(self):
        """Phase 1a creates 1 title + 2 template slides per game (nav + error).
        State and error slides are created via duplicateObject in Phase 2."""
        _, mock = _run(MazeGame(TINY))
        first_batch = mock.batch_update.call_args_list[0][0][1]
        insert_reqs = [r for r in first_batch if "createSlide" in r]
        assert len(insert_reqs) == 3  # title + nav-template + error-template

    def test_duplicate_slides_for_states(self):
        """Phase 2 creates state+error slides via duplicateObject, one pair per state."""
        game = MazeGame(TINY)
        state_count = len(game.get_all_states())
        _, mock = _run(game)
        all_reqs = [req for c in mock.batch_update.call_args_list for req in c[0][1]]
        dup_reqs = [r for r in all_reqs if "duplicateObject" in r]
        assert len(dup_reqs) == state_count * 2  # nav + error per state

    def test_all_inserted_slides_are_blank(self):
        game = MazeGame(TINY)
        _, mock = _run(game)
        first_batch = mock.batch_update.call_args_list[0][0][1]
        insert_reqs = [r for r in first_batch if "createSlide" in r]
        for req in insert_reqs:
            layout = req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            assert layout == "BLANK"

    def test_returns_url_string(self):
        game = MazeGame(TINY)
        url, _ = _run(game)
        assert isinstance(url, str)
        assert url.startswith("https://")

    def test_url_contains_presentation_id(self):
        game = MazeGame(TINY)
        url, _ = _run(game)
        assert "fake_prs_id" in url


# ── campaign ──────────────────────────────────────────────────────────────────


def _run_campaign(games, **kwargs):
    with patch("slide_games.builder.SlidesClient") as MockClient:
        mock = _mock_client()
        MockClient.return_value = mock
        url = build_campaign(
            games,
            credentials_file="fake.json",
            verbose=False,
            **kwargs,
        )
    return url, mock


class TestBuildCampaign:
    def test_empty_games_raises(self):
        with pytest.raises(ValueError):
            _run_campaign([])

    def test_single_game_identical_to_build_presentation(self):
        game = MazeGame(TINY)
        url_single, mock_single = _run(game)
        url_camp, mock_camp = _run_campaign([game])
        # Both should produce a URL and call create_presentation once
        assert isinstance(url_camp, str)
        assert mock_camp.create_presentation.call_count == 1

    def test_two_games_slide_count(self):
        """Phase 1a creates 1 title + 2 template slides per level."""
        _, mock = _run_campaign([MazeGame(TINY), MazeGame(TINY)])
        first_batch = mock.batch_update.call_args_list[0][0][1]
        insert_reqs = [r for r in first_batch if "createSlide" in r]
        # title + (nav-template + error-template) × 2 games
        assert len(insert_reqs) == 5  # 1 title + 4 templates

    def test_per_level_max_states_checked(self):
        game = MazeGame(LARGE)
        with pytest.raises(ValueError, match="max_states"):
            _run_campaign([game], max_states=5)

    def test_returns_url(self):
        url, _ = _run_campaign([MazeGame(TINY), MazeGame(TINY)])
        assert url.startswith("https://")

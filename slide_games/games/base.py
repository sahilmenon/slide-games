from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

ARROWS: dict[str, str] = {
    "up": "▲",
    "down": "▼",
    "left": "◄",
    "right": "►",
}


class BaseGame(ABC):
    """Base class for all slide games.

    To create a custom game, subclass this and implement the three abstract
    methods.  The ``build_presentation`` function handles everything else —
    state discovery, slide creation, rendering, and linking.

    Example — a bare-bones "move around a grid" game::

        class MyGame(BaseGame):
            def get_initial_state(self):
                return Position(1, 1)

            def get_transitions(self, state):
                # return {direction: next_state_or_None}
                return {
                    "up":    Position(state.x, state.y - 1) if can_move_up(state) else None,
                    "down":  ...,
                    "left":  ...,
                    "right": ...,
                }

            def is_terminal(self, state):
                return state == Position(5, 5)  # reached the goal

    The default renderer expects ``self.level`` (a :class:`~slide_games.models.Level`)
    and states that are either a :class:`~slide_games.models.Position` or an object
    with a ``.position`` attribute and an optional ``.eaten`` frozenset.

    Override :meth:`get_cell_color` and :meth:`get_extra_shapes` for custom rendering
    without touching the renderer at all.
    """

    @abstractmethod
    def get_initial_state(self) -> Any:
        """Return the starting game state."""
        ...

    @abstractmethod
    def get_transitions(self, state: Any) -> dict[str, Any | None]:
        """Return a dict mapping each of the four directions to the next state.

        Use ``None`` for blocked directions (the button will be grayed out).
        All four direction keys must be present.
        """
        ...

    @abstractmethod
    def is_terminal(self, state: Any) -> bool:
        """Return True if this state is a win/loss end state."""
        ...

    # ------------------------------------------------------------------
    # Optional hooks for custom rendering (no need to touch the renderer)
    # ------------------------------------------------------------------

    def get_cell_color(self, state: Any, ch: str, is_player: bool) -> dict | None:
        """Return an RGB dict to override the default cell color, or None to use the theme default.

        Called once per grid cell per state when building slide content.
        """
        return None

    def get_cell_image_url(self, state: Any, ch: str, is_player: bool) -> str | None:
        """Return a publicly accessible image URL to overlay on a cell, or None.

        When a URL is returned the renderer draws the image on top of the
        cell's background rectangle.  Use PNG with transparency for best
        results.  The image is scaled to fit the cell's inner area.

        Example — use a custom sprite for the player::

            def get_cell_image_url(self, state, ch, is_player):
                if is_player:
                    return "https://example.com/hero.png"
                return None
        """
        return None

    def get_extra_shapes(self, state: Any) -> list[dict]:
        """Return extra shape descriptors to add on top of the default grid.

        Each descriptor is a dict with keys:
            type        "rect" | "ellipse" | "text"
            x, y        position in grid-cell units (floats allowed)
            w, h        size in grid-cell units
            color       RGB dict
            text        (for type "text") string to render
            font_size   (for type "text") point size

        The renderer converts grid-cell units to EMUs automatically.
        """
        return []

    def show_win_banner(self, state: Any) -> bool:
        """Return True to show the 'YOU WIN!' banner for this terminal state.

        Override to return False for loss states (e.g. caught by a ghost) so
        the banner is suppressed and the game's ``render()`` output is shown
        instead.  D-pad buttons on loss slides all link back to the initial
        state so the player can immediately restart.

        Default: same as :meth:`is_terminal`.
        """
        return self.is_terminal(state)

    def render(self, surface: Any, state: Any) -> None:
        """Override to draw custom slide visuals using the pygame-like drawing API.

        When overridden, this method replaces the default grid renderer for
        game-state slides.  The D-pad navigation buttons and win banner are
        still added automatically — keep content above y = 820 virtual pixels
        to avoid overlapping them.

        ``surface`` is a :class:`~slide_games.gfx.Surface` with a 1920 × 1080
        virtual coordinate space.  Use :mod:`~slide_games.gfx.draw` functions
        to draw shapes, circles, lines, and text.

        Example::

            from slide_games.gfx import draw, Color, Rect

            def render(self, surface, state):
                surface.fill(Color(20, 20, 60))
                draw.circle(surface, Color(255, 215, 0),
                            (state.x * 120 + 100, state.y * 120 + 100), 50)
                draw.text(surface, f"Score: {state.score}",
                          Rect(10, 10, 400, 60), color=Color(255, 255, 255))
        """

    # ------------------------------------------------------------------
    # State discovery — override only if BFS is not appropriate
    # ------------------------------------------------------------------

    def get_all_states(self) -> list[Any]:
        """BFS from the initial state to enumerate every reachable state."""
        start = self.get_initial_state()
        visited: set = {start}
        queue = [start]
        order = [start]
        while queue:
            s = queue.pop(0)
            for ns in self.get_transitions(s).values():
                if ns is not None and ns not in visited:
                    visited.add(ns)
                    queue.append(ns)
                    order.append(ns)
        return order

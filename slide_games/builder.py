"""Orchestrates state discovery → slide creation → rendering → linking."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .client import SlidesClient
from .games.base import BaseGame
from .renderer import SLIDE_H, SLIDE_W, Renderer
from .themes import DARK, Theme

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
SEND_WORKERS = 5  # workers per build_campaign call
STATE_WARN = 500


class _RateLimiter:
    """Token-bucket rate limiter.  `acquire()` blocks until a call token is available.

    Caps total batchUpdate throughput to `calls_per_minute` across all concurrent
    build_campaign invocations, preventing HTTP 429 quota errors.  Starts with a
    small burst allowance so the first few calls don't all stall at once.
    """

    def __init__(self, calls_per_minute: int) -> None:
        self._rate = calls_per_minute / 60.0  # tokens / second
        self._tokens = min(5.0, self._rate * 5)  # initial burst: up to 5s worth
        self._max = float(calls_per_minute)
        self._lock = threading.Lock()
        self._last = time.monotonic()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._max,
                    self._tokens + self._rate * (now - self._last),
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            time.sleep(0.05)


# Global rate limiter: ≤50 batchUpdate calls/minute across ALL concurrent demos.
# Google Slides quota is 60 writes/min/user; 50 leaves headroom for retries.
_API_RATE = _RateLimiter(calls_per_minute=50)
# Concurrency cap: limits simultaneous in-flight HTTP connections.
_API_SEM = threading.Semaphore(4)


def _sid() -> str:
    return f"s{uuid.uuid4().hex[:15]}"


def _spatial_key(state: Any, initial: Any) -> tuple[int, int]:
    """Column-major sort key so keyboard ↓ in Presentation mode ≈ game ↓.

    Without sorting, BFS wavefront order causes pressing keyboard ↓ to jump to
    a position that is the mirror image of the current one across the main
    diagonal (x=y).  Sorting column-major (x first, then y) places states in
    the same column consecutively, so the next slide in the deck is the state
    directly below the current one for most positions.

    The initial state always sorts first (before slide 2) so that keyboard ↓
    from the title slide lands on the starting position.
    """
    if state == initial:
        return (-1, -1)
    pos = state if hasattr(state, "x") else getattr(state, "position", None)
    if pos is None:
        return (0, 0)
    return (pos.x, pos.y)


def build_presentation(
    game: BaseGame,
    title: str = "Slide Game",
    theme: Theme = DARK,
    credentials_file: str = "credentials.json",
    verbose: bool = True,
    max_states: int = 1_000,
    progress_callback=None,
    retry_callback=None,
    thread_initializer=None,
) -> str:
    """Generate a Google Slides presentation for a single game.

    Thin wrapper around :func:`build_campaign` for the common single-level case.
    See :func:`build_campaign` for full parameter documentation.
    """
    return build_campaign(
        [game],
        title=title,
        theme=theme,
        credentials_file=credentials_file,
        verbose=verbose,
        max_states=max_states,
        progress_callback=progress_callback,
        retry_callback=retry_callback,
        thread_initializer=thread_initializer,
    )


def build_campaign(
    games: list[BaseGame],
    title: str = "Slide Game",
    theme: Theme = DARK,
    credentials_file: str = "credentials.json",
    verbose: bool = True,
    max_states: int = 1_000,
    progress_callback=None,
    retry_callback=None,
    thread_initializer=None,
) -> str:
    """Generate a multi-level Google Slides presentation and return its URL.

    Each game in ``games`` becomes one level.  Win slides include a
    **Next Level ►** button that jumps to the next game's starting position.
    The final level's win slide shows only "YOU WIN!" with no next-level button.

    Args:
        games: Ordered list of :class:`~slide_games.games.BaseGame` instances,
            one per level.  A single-element list is equivalent to
            :func:`build_presentation`.
        title: Title shown on the opening slide.
        theme: Visual theme for all levels.
        credentials_file: Path to your OAuth client secrets JSON.
        verbose: Print progress to stdout.
        max_states: Per-level hard cap on reachable states.

    Returns:
        URL of the created presentation.

    Raises:
        ValueError: If any game exceeds ``max_states``, or ``games`` is empty.

    Example::

        from slide_games import build_campaign, MazeGame
        from slide_games.maze_gen import generate_maze

        levels = [
            MazeGame(generate_maze(4, 3, seed=1)),
            MazeGame(generate_maze(6, 5, seed=2)),
            MazeGame(generate_maze(8, 6, seed=3)),
        ]
        url = build_campaign(levels, title="Maze Campaign")
    """
    if not games:
        raise ValueError("games must not be empty")

    # 1 — discover and sort states for every level
    all_states: list[list] = []
    for i, game in enumerate(games):
        states = game.get_all_states()
        initial = game.get_initial_state()
        states.sort(key=lambda s: _spatial_key(s, initial))
        if len(states) > max_states:
            raise ValueError(
                f"Level {i + 1} has {len(states)} reachable states, which exceeds "
                f"max_states={max_states}.  Reduce the state space or raise max_states."
            )
        all_states.append(states)

    total_states = sum(len(s) for s in all_states)
    if verbose:
        lvl = len(games)
        print(f"Discovered {total_states} state(s) across {lvl} level{'s' if lvl > 1 else ''}")
    if verbose and total_states > STATE_WARN:
        print(
            f"  Warning: {total_states} states -> {total_states * 2 + 1} slides. "
            "This may take a few minutes."
        )

    client = SlidesClient(credentials_file)

    # 2 — pre-assign all IDs up front (needed for cross-level hyperlink wiring)
    title_slide_id = _sid()

    # One nav-template slide + one error-template slide per level.
    # These are created via createSlide, populated, then used as duplicateObject
    # sources so that per-state slides need far fewer API requests.
    tmpl_state_slide_ids: list[str] = [_sid() for _ in games]
    tmpl_state_btn_ids: list[dict[str, str]] = [
        {d: _sid() for d in ("up", "down", "left", "right")} for _ in games
    ]
    tmpl_error_slide_ids: list[str] = [_sid() for _ in games]
    tmpl_error_btn_ids: list[str] = [_sid() for _ in games]

    per_level_state_slides: list[dict] = [{s: _sid() for s in states} for states in all_states]
    per_level_error_slides: list[dict] = [{s: _sid() for s in states} for states in all_states]
    # Pre-assign per-state button IDs so we know them before duplication
    _DIRS = ("up", "down", "left", "right")
    per_level_state_btn_ids: list[dict] = [
        {s: {d: _sid() for d in _DIRS} for s in states} for states in all_states
    ]
    per_level_error_btn_ids: list[dict] = [{s: _sid() for s in states} for states in all_states]

    initial_slide_id = per_level_state_slides[0][games[0].get_initial_state()]

    # 3 — create presentation (comes with one default slide we'll delete)
    prs = client.create_presentation(title, SLIDE_W, SLIDE_H)
    prs_id = prs["presentationId"]
    default_slide_id = prs["slides"][0]["objectId"]
    if verbose:
        print(f"Created presentation {prs_id}")

    # Phase 1a — create title + template slides only (NOT state/error slides;
    #            those are created via duplicateObject in Phase 2)
    tmpl_ids_to_create: list[str] = []
    for i in range(len(games)):
        tmpl_ids_to_create.append(tmpl_state_slide_ids[i])
        tmpl_ids_to_create.append(tmpl_error_slide_ids[i])

    p1a_reqs = [
        {
            "createSlide": {
                "insertionIndex": j + 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
                "objectId": sid,
            }
        }
        for j, sid in enumerate([title_slide_id] + tmpl_ids_to_create)
    ] + [{"deleteObject": {"objectId": default_slide_id}}]

    for i in range(0, len(p1a_reqs), BATCH_SIZE):
        _API_RATE.acquire()
        client.batch_update(prs_id, p1a_reqs[i : i + BATCH_SIZE], on_retry=retry_callback)

    # Phase 1b — populate title + templates
    rdr0 = Renderer(games[0], theme)
    p1b_reqs: list[dict] = rdr0.render_title(title_slide_id, initial_slide_id, title)

    for lvl_idx, game in enumerate(games):
        rdr = Renderer(game, theme)
        p1b_reqs += rdr.render_nav_template(
            tmpl_state_slide_ids[lvl_idx], tmpl_state_btn_ids[lvl_idx]
        )
        p1b_reqs += rdr.render_error_template(
            tmpl_error_slide_ids[lvl_idx], tmpl_error_btn_ids[lvl_idx]
        )

    for i in range(0, len(p1b_reqs), BATCH_SIZE):
        _API_RATE.acquire()
        client.batch_update(prs_id, p1b_reqs[i : i + BATCH_SIZE], on_retry=retry_callback)

    if verbose:
        print(f"Created {1 + len(tmpl_ids_to_create)} template slides")

    # Phase 2 — duplicateObject for all state + error slides.
    # Duplicating in REVERSE spatial order so the resulting deck order is the
    # original spatial sort order (each dup is inserted after its source template).
    p2_reqs: list[dict] = []
    for lvl_idx, states in enumerate(all_states):
        tmpl_s = tmpl_state_slide_ids[lvl_idx]
        tmpl_b = tmpl_state_btn_ids[lvl_idx]
        for state in reversed(states):
            s_sid = per_level_state_slides[lvl_idx][state]
            s_btns = per_level_state_btn_ids[lvl_idx][state]
            p2_reqs.append(
                {
                    "duplicateObject": {
                        "objectId": tmpl_s,
                        "objectIds": {
                            tmpl_s: s_sid,
                            **{tmpl_b[d]: s_btns[d] for d in _DIRS},
                        },
                    }
                }
            )
    for lvl_idx, states in enumerate(all_states):
        tmpl_e = tmpl_error_slide_ids[lvl_idx]
        tmpl_e_btn = tmpl_error_btn_ids[lvl_idx]
        for state in reversed(states):
            e_sid = per_level_error_slides[lvl_idx][state]
            e_btn = per_level_error_btn_ids[lvl_idx][state]
            p2_reqs.append(
                {
                    "duplicateObject": {
                        "objectId": tmpl_e,
                        "objectIds": {tmpl_e: e_sid, tmpl_e_btn: e_btn},
                    }
                }
            )

    for i in range(0, len(p2_reqs), BATCH_SIZE):
        _API_RATE.acquire()
        client.batch_update(prs_id, p2_reqs[i : i + BATCH_SIZE], on_retry=retry_callback)

    if verbose:
        n_slides = total_states * 2
        print(f"Duplicated {n_slides} slides from templates")

    # Phase 3 — build and send delta content (game render + button updates +
    #           error links).  Template slides are deleted at the end.
    if verbose:
        print("Building slide content…")

    total_states_all = sum(len(s) for s in all_states)
    done_states = 0
    slide_groups: list[list[dict]] = []

    for lvl_idx, (game, states, s2s, e2s) in enumerate(
        zip(games, all_states, per_level_state_slides, per_level_error_slides)
    ):
        rdr = Renderer(game, theme)
        if lvl_idx + 1 < len(games):
            next_initial = games[lvl_idx + 1].get_initial_state()
            next_level_id: str | None = per_level_state_slides[lvl_idx + 1][next_initial]
        else:
            next_level_id = None

        initial_state = game.get_initial_state()
        initial_sid = s2s[initial_state]

        for state in states:
            slide_id = s2s[state]
            error_sid = e2s[state]
            s_btns = per_level_state_btn_ids[lvl_idx][state]
            e_btn = per_level_error_btn_ids[lvl_idx][state]
            nxt = next_level_id if game.is_terminal(state) else None

            group = rdr.render_state_delta(
                slide_id, state, s_btns, s2s, error_sid, nxt, initial_sid
            )
            group += rdr.render_error_delta(e_btn, slide_id)
            slide_groups.append(group)
            done_states += 1
            if progress_callback is not None:
                progress_callback(done_states, total_states_all, "building")

    # Delete template slides as the final group (safe: all dups already done)
    slide_groups.append(
        [{"deleteObject": {"objectId": t}} for t in tmpl_state_slide_ids + tmpl_error_slide_ids]
    )

    # Pack groups into batches without splitting any group across a boundary
    batches: list[list[dict]] = []
    current: list[dict] = []
    for group in slide_groups:
        if len(current) + len(group) > BATCH_SIZE and current:
            batches.append(current)
            current = []
        current.extend(group)
    if current:
        batches.append(current)

    total = sum(len(b) for b in batches)
    if verbose:
        print(f"Sending {total} API requests in {len(batches)} batches…")
    if progress_callback is not None:
        progress_callback(0, total, "sending")

    # Send batches concurrently (SEND_WORKERS workers, each with its own
    # SlidesClient so httplib2.Http is never shared across threads)
    sent = 0
    s_lock = threading.Lock()
    _tls = threading.local()

    def _send(batch: list[dict]) -> None:
        nonlocal sent
        if not hasattr(_tls, "client"):
            _tls.client = SlidesClient(credentials_file)
            logger.debug("Thread-local SlidesClient created in %s", threading.current_thread().name)
        logger.debug("waiting for rate-limit token (batch size %d)", len(batch))
        _API_RATE.acquire()
        logger.debug("rate-limit token acquired, sending batch (size %d)", len(batch))
        with _API_SEM:
            try:
                _tls.client.batch_update(prs_id, batch, on_retry=retry_callback)
            except Exception as exc:
                logger.error("batch_update failed: %s", exc, exc_info=True)
                raise
        with s_lock:
            sent = min(sent + len(batch), total)
            now = sent
        logger.debug("send progress: %d/%d requests (batch size %d)", now, total, len(batch))
        if progress_callback is not None:
            try:
                progress_callback(now, total, "sending")
            except Exception as exc:
                logger.warning("progress_callback raised: %s", exc)
        if verbose:
            print(f"  {now}/{total}")

    with ThreadPoolExecutor(max_workers=SEND_WORKERS, initializer=thread_initializer) as pool:
        for fut in as_completed(pool.submit(_send, b) for b in batches):
            fut.result()

    url = client.url(prs_id)
    if verbose:
        print(f"\nDone!  Open in Presentation mode to play:\n{url}")
    return url

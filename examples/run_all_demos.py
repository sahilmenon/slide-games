"""Run all four demos in parallel with a live progress table.

Usage::

    python examples/run_all_demos.py

Builds Maze Quest, Snake, Pac-Man, and Sokoban as Google Slides presentations
simultaneously.  A live table shows building/sending progress for all four at
once.  Each demo's URL appears in the table the moment it finishes.

Approximate state counts: Maze ~511, Snake ~517, Pac-Man ~491, Sokoban ~600.
"""
from __future__ import annotations
import logging
import os
import shutil
import sys
import threading
import time
import traceback as _tb
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

from slide_games import build_campaign, generate_maze
from maze_demo    import CustomMazeGame,   MAZE_THEME
from snake_demo   import SnakeGame,        SNAKE_THEME
from pacman_demo  import GhostPacmanGame,  PAC_THEME
from sokoban_demo import SokobanGame,      SOKOBAN_THEME, LEVEL_STR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── per-thread demo-name injection into all log records ───────────────────────
_log_ctx = threading.local()

class _DemoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.demo = getattr(_log_ctx, "demo", "-")
        return True

logging.basicConfig(
    filename="slide_games_debug.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s [%(demo)-10s] %(name)s: %(message)s",
)
for _h in logging.root.handlers:
    _h.addFilter(_DemoFilter())

# Suppress high-volume library loggers that add noise without diagnostic value.
# urllib3 and googleapiclient log every HTTP request at DEBUG; we only want
# WARNING+ from them so 429 retries remain visible but routine calls don't fill the log.
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

# ── table layout (80 chars exactly) ──────────────────────────────────────────
# Column content widths: Demo=14, States=7, Progress=34, Time=12
# 5 borders + 4×2 padding + (14+7+34+12) = 5+8+67 = 80 ✓
# URL line interior: 80 - 2 borders = 78; "  → " = 4; URL width = 74

_BAR_W = 12   # 4 chars reserved for "BLD "/"SND " phase label
_C1, _C2, _C3, _C4 = 16, 9, 36, 14   # dash counts per column (content+2)
_URL_W = _C1 + _C2 + _C3 + _C4 + 3 - 4   # 74: full interior minus "  → "

_TOP = "┌" + "─"*_C1 + "┬" + "─"*_C2 + "┬" + "─"*_C3 + "┬" + "─"*_C4 + "┐"
_HDR = f"│ {'Demo':<14} │ {'States':>7} │ {'Progress':<34} │ {'Time':<12} │"
_SEP = "├" + "─"*_C1 + "┼" + "─"*_C2 + "┼" + "─"*_C3 + "┼" + "─"*_C4 + "┤"
_BOT = "└" + "─"*_C1 + "┴" + "─"*_C2 + "┴" + "─"*_C3 + "┴" + "─"*_C4 + "┘"


def _bar(done: int, total: int) -> str:
    if total == 0:
        return "░" * _BAR_W
    filled = round(_BAR_W * done / total)
    return "█" * filled + "░" * (_BAR_W - filled)


def _fmt(secs: float) -> str:
    s = max(0, int(secs))
    return f"{s // 60}:{s % 60:02d}"


# ── per-demo row state ────────────────────────────────────────────────────────

class _Row:
    def __init__(self, name: str, states: int) -> None:
        self.name        = name
        self.states      = states
        self._phase      = "pending"
        self._done       = 0
        self._total      = 0
        self._start: float | None = None
        self._retry_wait = 0
        self._total_reqs = 0   # total API requests; set when sending phase begins
        self.url         = ""

    def set(self, phase: str, done: int = 0, total: int = 0,
            start: float | None = None, url: str = "") -> None:
        self._phase = phase
        self._done  = done
        self._total = total
        if start is not None:
            self._start = start
        if url:
            self.url = url
        if phase == "sending" and done == 0 and total > 0:
            self._total_reqs = total

    def set_retry(self, remaining: int) -> None:
        self._retry_wait = remaining

    def render_lines(self) -> list[str]:
        elapsed = time.time() - self._start if self._start else 0.0

        if self._phase == "done":
            bar_str  = f"    {'█' * _BAR_W} 100% {self.states:,}/{self.states:,}"
            time_str = f"{_fmt(elapsed)} total"

        elif self._phase == "sending":
            pct     = self._done * 100 // self._total if self._total else 0
            est_st  = round(self._done * self.states / self._total) if self._total else 0
            bar_str = f"SND {_bar(self._done, self._total)} {pct:3d}% {est_st:,}/{self.states:,}"
            if self._retry_wait > 0:
                time_str = f"retry {self._retry_wait}s"
            elif self._done:
                eta      = elapsed * (self._total - self._done) / self._done
                time_str = f"{_fmt(elapsed)} ~{_fmt(eta)}"
            else:
                time_str = f"{_fmt(elapsed)}"

        elif self._phase == "building":
            pct     = self._done * 100 // self._total if self._total else 0
            bar_str = f"BLD {_bar(self._done, self._total)} {pct:3d}% {self._done:,}/{self._total:,}"
            time_str = (f"retry {self._retry_wait}s"
                        if self._retry_wait > 0 else f"{_fmt(elapsed)}")

        else:  # pending
            bar_str  = ""
            time_str = ""

        lines = [
            f"│ {self.name:<14} │ {self.states:>7,} │"
            f" {bar_str:<34} │ {time_str:<12} │"
        ]
        if self._phase == "sending" and self._total_reqs:
            lines.append(f"│  ↑ {self._done:,} / {self._total_reqs:,} API requests")
        if self._phase == "done" and self._total_reqs:
            lines.append(f"│  ✓ {self._total_reqs:,} API requests sent")
        if self.url:
            lines.append(f"│  → {self.url}")
        return lines


# ── live table ────────────────────────────────────────────────────────────────

class _LiveTable:
    def __init__(self, rows: list[_Row]) -> None:
        self._rows    = rows
        self._n_drawn = 0
        self._last_t  = 0.0
        self._lock    = threading.Lock()

    def print_header(self) -> None:
        sys.stdout.write(f"{_TOP}\n{_HDR}\n{_SEP}\n")
        sys.stdout.flush()

    def redraw(self, force: bool = False) -> None:
        with self._lock:
            now = time.time()
            if not force and now - self._last_t < 0.15:
                return
            self._last_t = now
            lines = []
            for r in self._rows:
                lines.extend(r.render_lines())
            lines.append(_BOT)
            cols   = shutil.get_terminal_size((80, 24)).columns
            visual = sum(max(1, -(-len(l) // cols)) for l in lines)
            if self._n_drawn:
                sys.stdout.write(f"\033[{self._n_drawn}A")
            for line in lines:
                sys.stdout.write(f"\r{line}\033[K\n")
            sys.stdout.flush()
            self._n_drawn = visual


# ── demos ─────────────────────────────────────────────────────────────────────

def _make_demos() -> list[dict]:
    return [
        {
            "name":  "Maze Quest",
            "title": "Maze Quest",
            "games": [
                CustomMazeGame(generate_maze(16, 16, algorithm="backtracker", seed=7))
            ],
            "theme": MAZE_THEME,
        },
        {
            "name":  "Snake",
            "title": "Snake",
            "games": [SnakeGame()],
            "theme": SNAKE_THEME,
        },
        {
            "name":  "Pac-Man",
            "title": "Pac-Man",
            "games": [GhostPacmanGame()],
            "theme": PAC_THEME,
        },
        {
            "name":  "Sokoban",
            "title": "Sokoban",
            "games": [SokobanGame(LEVEL_STR)],
            "theme": SOKOBAN_THEME,
        },
    ]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Computing state counts…")
    demos = _make_demos()
    rows: list[_Row] = []
    for demo in demos:
        n = sum(len(g.get_all_states()) for g in demo["games"])
        demo["states"] = n
        rows.append(_Row(demo["name"], n))
        print(f"  {demo['name']:<14}  {n:,} states")

    table = _LiveTable(rows)
    table.print_header()
    table.redraw(force=True)

    def _run(idx: int, demo: dict) -> None:
        _log_ctx.demo = demo["name"]
        row = rows[idx]
        row.set("building", start=time.time())
        table.redraw(force=True)

        def _cb(done: int, total: int, phase: str,
                _row: _Row = row, _table: _LiveTable = table) -> None:
            _row.set_retry(0)
            _row.set(phase, done=done, total=total)
            try:
                _table.redraw()
            except Exception as exc:
                logging.getLogger(__name__).warning("redraw error in _cb: %s", exc)

        def _retry(remaining: int,
                   _row: _Row = row, _table: _LiveTable = table) -> None:
            _row.set_retry(remaining)
            try:
                _table.redraw(force=True)
            except Exception as exc:
                logging.getLogger(__name__).warning("redraw error in _retry: %s", exc)

        demo_name = demo["name"]

        def _init_thread(_name: str = demo_name) -> None:
            _log_ctx.demo = _name

        try:
            url = build_campaign(
                demo["games"],
                title=demo["title"],
                theme=demo["theme"],
                verbose=False,
                max_states=demo["states"] + 1,
                progress_callback=_cb,
                retry_callback=_retry,
                thread_initializer=_init_thread,
            )
            row.set("done", done=demo["states"], total=demo["states"], url=url)
        except Exception as exc:
            logging.getLogger(__name__).error("demo %s failed: %s", demo["name"], exc,
                                              exc_info=True)
            row.set("error", url=f"FAILED: {exc}")
        table.redraw(force=True)

    with ThreadPoolExecutor(max_workers=len(demos)) as pool:
        for fut in as_completed(pool.submit(_run, i, d) for i, d in enumerate(demos)):
            fut.result()   # _run catches its own errors; this only raises on unexpected bugs

    failed = [demo["name"] for i, demo in enumerate(demos) if not rows[i].url or rows[i].url.startswith("FAILED")]
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        print("See slide_games_debug.log for details.", file=sys.stderr)

    print("\nPresentation URLs")
    print("─" * 60)
    for i, demo in enumerate(demos):
        if rows[i].url and not rows[i].url.startswith("FAILED"):
            print(f"  {demo['name']:<14}  {rows[i].url}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        print("Interrupted.", file=sys.stderr)
    except Exception:
        sys.stdout.write("\n")
        sys.stdout.flush()
        print("─" * 60, file=sys.stderr)
        _tb.print_exc()
        print("─" * 60, file=sys.stderr)
        print("Full log: slide_games_debug.log", file=sys.stderr)
        sys.exit(1)

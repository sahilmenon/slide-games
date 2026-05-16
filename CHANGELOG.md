# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-16

### Added
- `BaseGame` abstract base class with `get_initial_state()`, `get_transitions()`, `is_terminal()`, and optional `render()` hook
- `build_presentation()` — generate a Google Slides presentation for a single game
- `build_campaign()` — multi-level presentations where win slides link to the next level
- `Renderer` — converts game states to Google Slides API requests; supports custom themes via `Theme`
- `SlidesClient` — thin wrapper around the Google Slides batchUpdate API with OAuth flow and exponential-backoff retry
- Built-in games: `MazeGame`, `SnakeGame`, `GhostPacmanGame`, `SokobanGame`
- `generate_maze()` utility supporting recursive backtracker and Prim's algorithms
- `gfx` module: `Surface`, `Color`, `Rect`, `Vector2`, `draw` helpers (`rect`, `circle`, `text`, `shape`, `lines`, `progress_bar`)
- `Position` named tuple and movement helpers
- Template-based `duplicateObject` optimization: reduces API request count by ~40% vs. per-slide creation
- Column-major spatial sort for natural keyboard-navigation order in Presentation mode
- Global token-bucket rate limiter (50 batchUpdate calls/min) and concurrency semaphore
- `py.typed` marker for PEP 561 compliance
- Four example scripts: `maze_demo.py`, `snake_demo.py`, `pacman_demo.py`, `sokoban_demo.py`, `run_all_demos.py`
- Full test suite (237 tests) with zero Google API calls required

[Unreleased]: https://github.com/sahilmenon/slide-games/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sahilmenon/slide-games/releases/tag/v0.1.0

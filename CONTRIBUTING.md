# Contributing to slide-games

Thank you for your interest in contributing!

## Dev setup

```bash
git clone https://github.com/sahilmenon/slide-games.git
cd slide-games
pip install -e ".[dev]"
```

Requires Python 3.11+. No Google API credentials are needed to run the test suite — all API calls are mocked.

## Running tests

```bash
pytest                          # run all 237 tests
pytest --tb=short               # compact traceback on failure
pytest --cov=slide_games        # with coverage report
```

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check slide_games tests    # lint
ruff format slide_games tests   # auto-format
```

Type annotations are checked with mypy:

```bash
mypy slide_games --ignore-missing-imports
```

Pre-commit hooks run all of the above automatically on every commit if you install them:

```bash
pip install pre-commit
pre-commit install
```

## Making a change

1. Fork the repo and create a branch off `main`.
2. Make your change. Add or update tests as appropriate.
3. Ensure `pytest`, `ruff check`, `ruff format --check`, and `mypy` all pass.
4. Open a pull request with a clear description of what changed and why.

## Adding a new game

1. Subclass `BaseGame` in `slide_games/games/`.
2. Implement `get_initial_state()`, `get_transitions()`, and `is_terminal()`.
3. Optionally override `render(surface, state)` using the `gfx` helpers.
4. Add an example script under `examples/` following the existing demos.
5. Confirm `game.get_all_states()` completes in reasonable time and stays under `max_states`.

## Security

Please report security vulnerabilities privately — see [SECURITY.md](SECURITY.md).

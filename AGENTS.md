# Repository Guidelines

## Project Structure & Module Organization
The core Python package lives in `mozilla_bitbar_devicepool/`, with vendor-specific logic in `bitbar/` and `lambdatest/`. Supporting CLI entry points are defined in `pyproject.toml` and mirrored as helper scripts in `bin/`. Shared utils and report generators sit under `util/` and `device_group_report*.py`, while environment and service configuration lives in `config/` and `service/`. Tests reside in `mozilla_bitbar_devicepool/test/`, alongside fixture data in `test_data/`.

## Build, Test, and Development Commands
Run `poetry install --with=dev` to sync dependencies, then `poetry shell` for an interactive environment. Use `pre-commit install` once per clone to enable formatting and lint hooks. Execute unit tests with `pytest` or the coverage variant `pytest --cov --cov-report=term`. CLI entry points run via `poetry run`, e.g., `poetry run mld` for LambdaTest device runs or `poetry run dgr` for Bitbar reports.

## Coding Style & Naming Conventions
Stick to Python 3.9+ with 4-space indentation and descriptive, snake_case names for modules, functions, and variables. Formatting and imports are enforced by `ruff-format` with a 120-character line limit; structural linting runs via `ruff check --select I --fix` and `pylint` in CI/pre-commit. Configuration files use YAML or TOML—mirror existing key naming and comment styles.

## Testing Guidelines
Place new tests in `mozilla_bitbar_devicepool/test/` following the `<module>_test.py` pattern and reuse helpers in `util_test.py`. Prefer `pytest` fixtures over ad-hoc setup; store serialized inputs in `test_data/`. Validate coverage locally with `pytest --cov --cov-report=html` and ensure critical branches that touch vendor APIs are exercised via mocks.

## Commit & Pull Request Guidelines
Commit messages are short (≤72 characters), lowercase, and often scoped (`lt status: refresh cache`). Group related edits per commit and reference Bugzilla or GitHub IDs when applicable. Pull requests should describe vendor impact, outline testing (`pytest`, manual device run), and include screenshots or log snippets when UI or report output changes. Link configuration updates to rollout plans so reviewers can validate credentials and scheduling.

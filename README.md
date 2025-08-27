# mozilla-taskcluster-devicepool

[![CircleCI Status](https://circleci.com/gh/mozilla-platform-ops/mozilla-bitbar-devicepool.svg?style=svg)](https://app.circleci.com/pipelines/github/mozilla-platform-ops/mozilla-bitbar-devicepool)


This project enables the execution of Mozilla's [Taskcluster](https://taskcluster.net/) tests on Android hardware devices via API integrations with various vendors.

Currently supported vendors are [Bitbar](https://bitbar.com/) and [Lambdatest](https://www.lambdatest.com/).

## Installation

```bash
# Clone the repository
git clone https://github.com/bclary/mozilla-bitbar-devicepool.git
cd mozilla-bitbar-devicepool

# if needed, install poetry
#   - see https://python-poetry.org/docs/ for more options and info
curl -sSL https://install.python-poetry.org | python3 -

# install poetry shell plugin
poetry self add poetry-plugin-shell

# ensure poetry and plugins are up to date
poetry self update

# activate the virtual environment
poetry shell

# install dependencies (with dev deps)
poetry install --with=dev

```

## Updates

```bash
# Update the repository
cd mozilla-bitbar-devicepool
git pull --rebase

# ensure poetry and plugins are up to date
poetry self update

# activate the virtual environment
poetry shell

# install any updated dependencies
poetry install

# Restart the service
```

## Development

```bash
poetry shell  # activate venv
pre-commit install  # install the pre-commit hook
# make changes
# commit
# test
# make a PR
```

## Testing (Unit Tests)

You must install the development requirements first.  See the "Development" section above.

```bash
# activate venv
poetry shell

pytest  # runs once
# or
pytest-watch  # monitors files for changes and reruns

# pytest-watch with coverage and double verbose
pytest-watch -- -vv --cov
```

## Running and More Documentation

For Bitbar, see `README.bb.md`.

For Lamdatest, see `README.lt.md`.

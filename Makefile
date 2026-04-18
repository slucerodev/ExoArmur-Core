# ExoArmur Makefile
#
# All targets honour a PYTHON= override so the same Makefile works in a
# cloned .venv, a CI runner, or a developer's system Python. By default we
# use `python3` on PATH, which picks up whichever interpreter you have
# activated.
#
# Every target that needs the ExoArmur test/lint toolchain assumes the
# project has been installed via the README's two-step pattern:
#
#     pip install -r requirements.lock
#     pip install --no-deps -e '.[dev]'
#
# See `make install` below for the exact sequence.

PYTHON ?= python3
PIP    := $(PYTHON) -m pip

# Source roots that all tools operate on. Keeping this in one place means
# lint/format/type-check stay in lockstep as directories move.
SRC_PATHS := src tests demos examples scripts

.PHONY: help install install-dev test verify stability lint format format-check typecheck clean

help:
	@echo "ExoArmur Build System"
	@echo ""
	@echo "Everyday targets (safe, currently pass on main):"
	@echo "  install       - Install locked runtime deps + editable package (no dev tools)"
	@echo "  install-dev   - Install locked runtime deps + editable package + dev extras"
	@echo "  test          - Run the full pytest suite"
	@echo "  verify        - Run 'exoarmur verify-all' (full verification pipeline)"
	@echo "  stability     - Run the three-run stability gate used by CI"
	@echo "  lint          - Compile-check every Python file under src/ and tests/"
	@echo "  clean         - Remove build artifacts, caches, and generated files"
	@echo ""
	@echo "Opt-in targets (surface pre-existing style/type debt; may fail on main):"
	@echo "  format        - Apply black + isort to source tree (mutates files)"
	@echo "  format-check  - Non-mutating black + isort verification"
	@echo "  typecheck     - Run mypy against src/exoarmur (requires dev extras)"
	@echo ""
	@echo "Overrides: PYTHON=/path/to/python make test"

install:
	$(PIP) install --upgrade 'pip>=26.0'
	$(PIP) install -r requirements.lock
	$(PIP) install --no-deps -e .

install-dev:
	$(PIP) install --upgrade 'pip>=26.0'
	$(PIP) install -r requirements.lock
	$(PIP) install --no-deps -e '.[dev]'

test:
	$(PYTHON) -m pytest -q

verify:
	$(PYTHON) -m exoarmur.cli verify-all

stability:
	$(PYTHON) scripts/infra/stability_ci.py

# `lint` is deliberately scoped to checks that are guaranteed to pass on a
# clean `main` today: a compile + import check of every tracked Python file
# under src/ and tests/. Stricter style/type checks live under format-check
# and typecheck so a developer opts into them explicitly.
lint:
	$(PYTHON) -m compileall -q src tests

format:
	$(PYTHON) -m isort $(SRC_PATHS)
	$(PYTHON) -m black $(SRC_PATHS)

format-check:
	$(PYTHON) -m isort --check-only $(SRC_PATHS)
	$(PYTHON) -m black --check $(SRC_PATHS)

typecheck:
	$(PYTHON) -m mypy src/exoarmur

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .stability-runs
	rm -rf build dist
	rm -rf src/*.egg-info
	rm -f .coverage stability_report.json
	@echo "Cleaned build artifacts"

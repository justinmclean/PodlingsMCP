PYTHON ?= python3

.PHONY: test coverage lint format check-format typecheck check

test:
	$(PYTHON) -m unittest discover -s tests -v

coverage:
	$(PYTHON) -m coverage run --branch -m unittest discover -s tests
	$(PYTHON) -m coverage report -m

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

check-format:
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy podlings tests

check: lint typecheck test

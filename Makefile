VENV    = .venv
PYTHON  = $(VENV)/bin/python
PIP     = $(VENV)/bin/pip
MAP    ?= maps/easy/01_linear_path.txt


install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	find . -type d -name "__pycache__" -not -path "./$(VENV)/*" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(VENV)/bin/flake8 . --exclude=$(VENV),.git,__pycache__,.mypy_cache,.pytest_cache
	$(VENV)/bin/mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(VENV)/bin/flake8 . --exclude=$(VENV),.git,__pycache__,.mypy_cache,.pytest_cache
	$(VENV)/bin/mypy . --strict


.PHONY: install run debug clean lint lint-strict
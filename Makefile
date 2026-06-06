# Makefile — single entry point for routine project actions.
# `make` or `make help` lists available targets.

VENV   ?= .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
DEPS_SENTINEL := $(VENV)/.deps-installed

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(VENV)/bin/python:
	python3 -m venv $(VENV)

$(DEPS_SENTINEL): requirements-dev.txt requirements.txt | $(VENV)/bin/python
	$(PIP) install -r requirements-dev.txt
	@touch $(DEPS_SENTINEL)

.PHONY: install
install: $(DEPS_SENTINEL) ## Create venv and install dev/test dependencies

.PHONY: env
env: ## Create .env from .env.example if missing
	@test -f .env || cp .env.example .env

.PHONY: test
test: install ## Run tests
	$(PYTEST)

.PHONY: run
run: install ## Run the application
	$(PY) main.py

.PHONY: clean
clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .mypy_cache

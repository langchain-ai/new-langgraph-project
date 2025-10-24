.PHONY: all install lint test help

# Default target executed when no arguments are given to make.
all: help

######################
# DEPENDENCIES
######################

install:
	pip install -e .[dev]

######################
# LINTING & FORMATTING
######################

lint:
	ruff check src/ tests/
	ruff format src/ tests/

######################
# TESTING
######################

test:
	python -m pytest tests/unit_tests

integration_tests:
	python -m pytest tests/integration_tests

######################
# HELP
######################

help:
	@echo 'Makefile Targets:'
	@echo '  install            - Install dependencies'
	@echo '  lint               - Run linters and formatters'
	@echo '  test               - Run unit tests'
	@echo '  integration_tests  - Run integration tests'
	@echo '  help               - Show this help message'
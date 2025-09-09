.PHONY: all format lint test tests test_watch integration_tests docker_tests help extended_tests dev-up dev-down dev-logs docker-build docker-up docker-down clean setup test-api

# Default target executed when no arguments are given to make.
all: help

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	python -m pytest $(TEST_FILE)

integration_tests:
	python -m pytest tests/integration_tests 

test_watch:
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	python -m pytest --only-extended $(TEST_FILE)


######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=src/
MYPY_CACHE=.mypy_cache
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: PYTHON_FILES=src
lint_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_package lint_tests:
	python -m ruff check .
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
	ruff format $(PYTHON_FILES)
	ruff check --select I --fix $(PYTHON_FILES)

spell_check:
	codespell --toml pyproject.toml

spell_fix:
	codespell --toml pyproject.toml -w

######################
# DOCKER & DEPLOYMENT
######################

dev-up:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@echo "LocalStack is running at http://localhost:4566"

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

docker-build:
	docker build -t ai-agents:latest .

docker-up:
	./scripts/deploy.sh up

docker-down:
	./scripts/deploy.sh down

docker-logs:
	docker-compose logs -f

test-api:
	@echo "Testing API endpoints..."
	curl -X GET http://localhost:8000/health | python -m json.tool
	@echo ""
	curl -X POST http://localhost:8000/api/v1/process \
		-H "Content-Type: application/json" \
		-d '{"s3_key": "test/sample.pdf", "process_type": "classify"}' | python -m json.tool

clean:
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.example .env; \
		echo "Please update .env with your configuration"; \
	fi
	pip install -r requirements.txt
	@echo "Setup complete!"

######################
# HELP
######################

help:
	@echo '----'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo '----'
	@echo 'Docker Commands:'
	@echo 'dev-up                       - Start LocalStack for development'
	@echo 'dev-down                     - Stop LocalStack'
	@echo 'dev-logs                     - View LocalStack logs'
	@echo 'docker-build                 - Build Docker image'
	@echo 'docker-up                    - Start all services with Docker'
	@echo 'docker-down                  - Stop all Docker services'
	@echo 'test-api                     - Test API endpoints'
	@echo 'clean                        - Clean up everything'
	@echo 'setup                        - Setup development environment'


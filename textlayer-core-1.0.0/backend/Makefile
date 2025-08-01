.PHONY: help lint format test clean install dev run env-setup doppler-setup update-models

# Display help information by default
help:
	@echo "Available commands:"
	@echo "  make help          - Show this help message"
	@echo "  make lint          - Run linting checks"
	@echo "  make format        - Run code formatters"
	@echo "  make test          - Run unit tests"
	@echo "  make coverage      - Run tests with coverage"
	@echo "  make clean         - Clean up build artifacts"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev           - Install development dependencies"
	@echo "  make run           - Run the Flask application in development mode"
	@echo "  make env-setup     - Create a .env file from .env.example if it doesn't exist"
	@echo "  make doppler-setup - Initialize Doppler CLI for secrets management"
	@echo "  make update-models - Update the LLM model registry from LiteLLM"

# Run linting checks with Ruff
lint:
	@echo "Running Ruff linter..."
	ruff format --check .
	ruff check .

# Run code formatting with Ruff
format:
	@echo "Running Ruff linter with auto-fix..."
	ruff format .
	ruff check --fix .

# Run all tests
test:
	@echo "Running tests..."
	FLASK_CONFIG=TEST flask test

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	FLASK_CONFIG=TEST flask test --coverage

# Clean up build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf app/cli/tmp/coverage
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install production dependencies
install:
	@echo "Installing production dependencies..."
	pip install -e .

# Install development dependencies
dev:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"

# Run the Flask application in development mode
run:
	@echo "Starting Flask application in development mode..."
	uv run flask run

# Create .env file from .env.example if it doesn't exist
env-setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "Please update the .env file with your configuration values."; \
	else \
		echo ".env file already exists."; \
	fi

# Setup Doppler CLI for secrets management
doppler-setup:
	@echo "Setting up Doppler CLI for secrets management..."
	@if command -v doppler >/dev/null 2>&1; then \
		echo "Doppler CLI is already installed."; \
		doppler login; \
		echo "Run 'doppler setup' to configure your project."; \
	else \
		echo "Doppler CLI is not installed."; \
		echo "Please install Doppler CLI by following the instructions at:"; \
		echo "https://docs.doppler.com/docs/install-cli"; \
	fi  

# Update LLM model registry from LiteLLM
update-models:
	@echo "Updating LLM model registry from LiteLLM..."
	flask update_models --force
	@echo "Model registry updated successfully."  

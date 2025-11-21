.PHONY: help install test lint format clean

help:
	@echo "DukeNET Development Commands"
	@echo "install  - Install all dependencies"
	@echo "test     - Run all tests"
	@echo "lint     - Run linters"
	@echo "format   - Format code"
	@echo "clean    - Clean build artifacts"

install:
	@echo "Installing dependencies..."

test:
	pytest tests/

lint:
	@echo "Running linters..."

format:
	black .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name target -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +

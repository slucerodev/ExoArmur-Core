# ExoArmur Makefile

.PHONY: help test verify clean lint format

help:
	@echo "ExoArmur Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  test     - Run all tests"
	@echo "  verify   - Run comprehensive verification pipeline"
	@echo "  lint     - Run linting checks"
	@echo "  format   - Format code"
	@echo "  clean    - Clean build artifacts"

test:
	python3 -m pytest tests/ -v

verify:
	python3 scripts/verify_all.py

lint:
	@echo "Running basic Python syntax checks..."
	python3 -m py_compile src/federation/*.py
	@echo "✅ Syntax checks passed"

format:
	@echo "No formatter configured - skipping"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "✅ Cleaned build artifacts"

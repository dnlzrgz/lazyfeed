clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

lint:
	pre-commit run --all-files

update:
	uv lock --upgrade
	uv sync

console:
	textual console

dev:
	uv run textual run --dev src/lazyfeed/main.py

test:
	pytest -v

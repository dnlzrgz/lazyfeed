clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

lint:
	uv run ruff format .
	uv run ruff check . --fix

update:
	uv lock --upgrade
	uv sync

console:
	textual console

dev:
	uv run textual run --dev src/lazyfeed/main.py

test:
	pytest -v

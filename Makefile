clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

lint:
	uv run ruff check . --fix

update:
	uv lock --upgrade
	uv sync

test:
	pytest -v

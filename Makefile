.PHONY: install test review clean

install:
	@echo "🔍 Installing codereview..."
	pip install -e .
	@echo ""
	@echo "✅ Done! Run 'codereview --setup' to get started."

test:
	pytest -v

review:
	codereview codereview/cli.py codereview/reviewer.py codereview/formatter.py codereview/git_utils.py codereview/config.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
	find . -name "__pycache__" -delete

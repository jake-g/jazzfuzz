.PHONY: help server clean format match-albums test-links benchmark export-tsv test

# Default target displays help
help:
	@echo "========================================================="
	@echo "🌐 Jazz Fuzz Maintenance Console"
	@echo "========================================================="
	@echo "Available commands:"
	@echo "  make server        - Launch local development server at http://localhost:3001"
	@echo "  make match-albums  - Run the album matching tool (requires oauth.json)"
	@echo "  make test-links    - Validate all YouTube playlist & video links in index.html"
	@echo "  make benchmark     - Benchmark loading times for poster image resolutions"
	@echo "  make export-tsv    - Create a TSV glossary (index) of all albums"
	@echo "  make test          - Run all Python unit tests"
	@echo "  make format        - Clean up code styling and trim trailing whitespace"
	@echo "  make clean         - Remove Python cache files"
	@echo "========================================================="

server:
	@echo "Starting local dev server with CORS enabled at http://localhost:3001 ..."
	@python3 -c "$$CORS_SERVER"

match-albums:
	python3 maintenance.py match --html index.html

test-links:
	python3 maintenance.py test-links --html index.html

benchmark:
	python3 maintenance.py benchmark --html index.html

export-tsv:
	python3 maintenance.py export-tsv --html index.html --tsv albums_glossary.tsv

test:
	python3 -m unittest discover -p "*_test.py"

format:
	@echo "Formatting Python files with black..."
	@if command -v black >/dev/null 2>&1; then \
		black maintenance.py maintenance_test.py; \
	else \
		echo "black is not installed. Skipping auto-formatting."; \
	fi
	@echo "Trimming trailing whitespace on HTML, JS, CSS..."
	find . -type f \( -name "*.html" -o -name "*.js" -o -name "*.css" \) -not -path "*/old/*" -exec sed -i '' -e 's/[[:space:]]*$$//' {} +

clean:
	@echo "🧹 Cleaning up pycache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean completed."

define CORS_SERVER
import http.server

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

http.server.test(HandlerClass=CORSRequestHandler, port=3001)
endef
export CORS_SERVER

.PHONY: help server clean format match-albums test-links benchmark export-tsv test research-todos todo-wizard import-album sort-tsv validate-years check verify sort-todo

# Detect OS for cross-platform in-place sed
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	SED_INPLACE := sed -i ''
else
	SED_INPLACE := sed -i
endif

# Default target displays help
help:
	@echo "========================================================="
	@echo "🌐 Jazz Fuzz Maintenance Console"
	@echo "========================================================="
	@echo "Available commands:"
	@echo "  make server         - Launch local development server at http://localhost:3001"
	@echo "  make match-albums   - Run the album matching tool (requires oauth.json)"
	@echo "  make research-todos - Update todo albums TSV with MusicBee ratings and popularity"
	@echo "  make todo-wizard    - Step through the todo list to skip, delete, or promote"
	@echo "  make import-album   - Direct import of an album (ARTIST=\"...\" ALBUM=\"...\" [POPULARITY=50])"
	@echo "  make sort-tsv       - Sort a TSV file (FILE=\"filename.tsv\" BY=\"newest|oldest|popular|default\")"
	@echo "  make sort-todo      - Ensure albums_todo.tsv is sorted by default rules"
	@echo "  make test-links     - Validate all YouTube playlist & video links in index.html"
	@echo "  make validate-years - Check catalog for classic albums with reissue year anomalies"
	@echo "  make check/verify   - Run all format, test, link verification, and year audits"
	@echo "  make benchmark      - Benchmark loading times for poster image resolutions"
	@echo "  make export-tsv     - Create a TSV glossary (index) of all albums"
	@echo "  make test           - Run all Python unit tests"
	@echo "  make format         - Clean up code styling and trim trailing whitespace"
	@echo "  make clean          - Remove Python cache files"
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

research-todos:
	python3 maintenance.py research-todos --todo albums_todo.tsv

todo-wizard:
	python3 maintenance.py todo-wizard --todo albums_todo.tsv

import-album:
	@if [ -z "$(ARTIST)" ] || [ -z "$(ALBUM)" ]; then \
		echo "Usage: make import-album ARTIST=\"Artist Name\" ALBUM=\"Album Title\" [POPULARITY=50]"; \
		exit 1; \
	fi
	python3 maintenance.py import-album --artist "$(ARTIST)" --album "$(ALBUM)" --popularity "$(or $(POPULARITY),50)"

sort-tsv:
	@if [ -z "$(FILE)" ] || [ -z "$(BY)" ]; then \
		echo "Usage: make sort-tsv FILE=\"filename.tsv\" BY=\"newest|oldest|popular|default\""; \
		exit 1; \
	fi
	python3 maintenance.py sort-tsv --file "$(FILE)" --by "$(BY)"

validate-years:
	python3 maintenance.py validate-years --html index.html

sort-todo:
	python3 maintenance.py sort-tsv --file albums_todo.tsv --by default

validate-placeholders:
	@echo "Checking for unresolved (Add ... manually) placeholders in index.html..."
	@if grep -q "(Add " index.html; then \
		echo "❌ Error: Found unresolved placeholder texts in index.html!"; \
		grep -n "(Add " index.html; \
		exit 1; \
	fi
	@echo "✅ No placeholders found."

validate-playlists:
	python3 maintenance.py validate-playlists --html index.html

check: format sort-todo test test-links validate-years validate-placeholders validate-playlists
	@echo "✅ ALL MAINTENANCE CHECKS PASSED SUCCESSFULLY!"

verify: check

test:
	python3 -m unittest discover -p "*_test.py"

format:
	@echo "Formatting Python files with black..."
	@if command -v black >/dev/null 2>&1; then \
		black maintenance.py maintenance_test.py; \
	else \
		echo "black is not installed. Skipping auto-formatting."; \
	fi
	@echo "Trimming trailing whitespace on HTML, JS, CSS, PY, TSV, MD..."
	find . -type f \( -name "*.html" -o -name "*.js" -o -name "*.css" -o -name "*.py" -o -name "*.tsv" -o -name "*.md" \) -not -path "*/old/*" -exec $(SED_INPLACE) -e 's/[[:space:]]*$$//' {} +

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

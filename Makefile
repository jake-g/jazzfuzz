.PHONY: help setup venv pre-commit server clean format match-albums test-links benchmark export-tsv export-playlist refresh-auth test research-queue queue-wizard import-album sort-tsv validate-years check verify sort-queue

# Define virtual environment path
VENV := venv
ifeq ($(wildcard $(VENV)/bin/python),)
	PYTHON := python3
else
	PYTHON := $(VENV)/bin/python
endif

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
	@echo "  make server          - Launch local development server at http://localhost:3001"
	@echo "  make match-albums    - Run the album matching tool (requires oauth.json)"
	@echo "  make research-queue  - Update queue albums TSV with MusicBee ratings and popularity"
	@echo "  make queue-wizard    - Step through the queue list to skip, delete, or promote"
	@echo "  make import-album    - Direct import of an album (ARTIST=\"...\" ALBUM=\"...\" [POPULARITY=50])"
	@echo "  make sort-tsv        - Sort a TSV file (FILE=\"filename.tsv\" BY=\"newest|oldest|popular|default\")"
	@echo "  make sort-queue      - Ensure albums_queue.tsv is sorted by default rules"
	@echo "  make test-links      - Validate all YouTube playlist & video links in index.html"
	@echo "  make validate-years  - Check catalog for classic albums with reissue year anomalies"
	@echo "  make check/verify    - Run all format, test, link verification, and year audits"
	@echo "  make benchmark       - Benchmark loading times for poster image resolutions"
	@echo "  make export-tsv      - Create a TSV glossary (index) of all albums"
	@echo "  make export-playlist - Sync catalog albums to your YouTube Music public playlist"
	@echo "  make refresh-auth    - Paste a browser cURL command to refresh session cookies"
	@echo "  make test            - Run all Python unit tests"
	@echo "  make format          - Clean up code styling and trim trailing whitespace"
	@echo "  make clean           - Remove Python cache files"
	@echo "========================================================="

server:
	@echo "Starting local dev server with CORS enabled at http://localhost:3001 ..."
	@$(PYTHON) -c "$$CORS_SERVER"

match-albums:
	$(PYTHON) maintenance.py match --html index.html

test-links:
	$(PYTHON) maintenance.py test-links --html index.html

benchmark:
	$(PYTHON) maintenance.py benchmark --html index.html

export-tsv:
	$(PYTHON) maintenance.py export-tsv --html index.html --tsv albums_glossary.tsv

export-playlist:
	$(PYTHON) maintenance.py export-playlist --html index.html

refresh-auth:
	$(PYTHON) maintenance.py refresh-auth

research-queue:
	$(PYTHON) maintenance.py research-todos --todo albums_queue.tsv

queue-wizard:
	$(PYTHON) maintenance.py todo-wizard --todo albums_queue.tsv

import-album:
	@if [ -z "$(ARTIST)" ] || [ -z "$(ALBUM)" ]; then \
		echo "Usage: make import-album ARTIST=\"Artist Name\" ALBUM=\"Album Title\" [POPULARITY=50]"; \
		exit 1; \
	fi
	$(PYTHON) maintenance.py import-album --artist "$(ARTIST)" --album "$(ALBUM)" --popularity "$(or $(POPULARITY),50)"

sort-tsv:
	@if [ -z "$(FILE)" ] || [ -z "$(BY)" ]; then \
		echo "Usage: make sort-tsv FILE=\"filename.tsv\" BY=\"newest|oldest|popular|default\""; \
		exit 1; \
	fi
	$(PYTHON) maintenance.py sort-tsv --file "$(FILE)" --by "$(BY)"

validate-years:
	$(PYTHON) maintenance.py validate-years --html index.html

sort-queue:
	$(PYTHON) maintenance.py sort-tsv --file albums_queue.tsv --by default

validate-placeholders:
	@echo "Checking for unresolved (Add ... manually) placeholders in index.html..."
	@if grep -q "(Add " index.html; then \
		echo "❌ Error: Found unresolved placeholder texts in index.html!"; \
		grep -n "(Add " index.html; \
		exit 1; \
	fi
	@echo "✅ No placeholders found."

validate-playlists:
	$(PYTHON) maintenance.py validate-playlists --html index.html

check: format sort-queue pre-commit test test-links validate-years validate-placeholders validate-playlists
	@echo "✅ Checks Passed!"

verify: check

pre-commit:
	@echo "Running pre-commit hooks..."
	@if $(PYTHON) -c "import pre_commit" >/dev/null 2>&1; then \
		$(VENV)/bin/pre-commit run --all-files; \
	else \
		echo "pre-commit is not installed in virtual environment. Skipping hooks."; \
	fi

test:
	$(PYTHON) -m unittest discover -p "*_test.py"

format:
	@echo "Formatting Python files with black..."
	@if $(PYTHON) -c "import black" >/dev/null 2>&1; then \
		$(PYTHON) -m black maintenance.py maintenance_test.py; \
	else \
		echo "black is not installed. Skipping auto-formatting."; \
	fi
	@echo "Trimming trailing whitespace on HTML, JS, CSS, PY, MD..."
	find . -type f \( -name "*.html" -o -name "*.js" -o -name "*.css" -o -name "*.py" -o -name "*.md" \) -not -path "*/old/*" -exec $(SED_INPLACE) -e 's/[[:space:]]*$$//' {} +

setup: venv

venv:
	@echo "Creating Python virtual environment in $(VENV)..."
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "✅ Virtual environment successfully initialized!"

clean:
	@echo "🧹 Cleaning up pycache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf $(VENV)
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

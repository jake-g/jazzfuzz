# Jazz Fuzz

A sonic portal to a curated selection of cosmic jazz albums. This site features detailed information about each album, including the musicians involved, production credits, track lists, and embedded YouTube Music players.

## Live Site
The site is hosted on GitHub Pages:
[https://jake-g.github.io/jazzfuzz/](https://jake-g.github.io/jazzfuzz/)

## Features
- **Curated Catalog:** A list of favorite jazz albums with cover art, release details, track lists, and personnel details.
- **Dynamic Sorting:** Sort albums dynamically by artist or release year.
- **Collapsible Details:** Expand/collapse album metadata and descriptions.
- **Fast Playback:** Uses the lightweight `<lite-youtube>` component to load YouTube players on-demand.
## Development

### Adding New Albums
When adding new album reviews to [index.html](file:///Users/jakegarrison/Downloads/projects/jazzfuzz/index.html):
1. **Formatting:** Follow the structured layout defined in [template.html](file:///Users/jakegarrison/Downloads/projects/jazzfuzz/template.html).
2. **Chronological Sorting:** Albums must be ordered in **newest-to-oldest (reverse chronological)** order based on their original release date. Please place new reviews in their correct position in `index.html`.
3. **Glossary:** Run `make export-tsv` to update the album index glossary.

### Makefile Maintenance Commands
A `Makefile` is provided in the root directory to automate common development and maintenance tasks:

- **Start Local Server:**
  ```bash
  make server
  ```
  Runs the local development server at `http://localhost:3001` with CORS enabled (defined inline).

- **Match Albums on YouTube Music:**
  ```bash
  make match-albums
  ```
  Runs the matching utility `maintenance.py match` to search for playlist matches. Requires a local `oauth.json` for YouTube Music authentication.

- **Validate YouTube Links:**
  ```bash
  make test-links
  ```
  Scans all YouTube playlist and video IDs in `index.html` and checks their validity using the public YouTube OEmbed API.

- **Benchmark Poster Loading Times:**
  ```bash
  make benchmark
  ```
  Measures and compares the total download size and download speed for high-resolution (`maxresdefault`) vs standard (`hqdefault`) poster images for all album frames.

- **Export Album TSV Glossary:**
  ```bash
  make export-tsv
  ```
  Extracts all albums and metadata from `index.html` and generates a clean TSV glossary at `albums_glossary.tsv`.

- **Run Tests:**
  ```bash
  make test
  ```
  Runs python unit tests located in `maintenance_test.py`.

- **Code Formatting:**
  ```bash
  make format
  ```
  Applies style formatting (`black`) to python utilities, and trims trailing whitespaces from HTML, JS, and CSS files safely.

- **Clean Cache:**
  ```bash
  make clean
  ```
  Removes Python bytecode caches (`__pycache__` and `.pyc` files).

### CI/CD and Quality Tools
- **Pre-commit Hooks:** Set up to automatically check for trailing whitespace, fix end of files, validate YAML files, and block large file commits.
- **GitHub Actions (CI Pipeline):** Automatically runs on pushes and PRs to `main` branch to check Python code formatting using `black`, ensure that scripts compile, and run the unit tests.

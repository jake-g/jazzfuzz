# Jazz Fuzz

[![View on GitHub](https://img.shields.io/badge/View_on-GitHub-181717?logo=github&style=flat)](https://github.com/jake-g/jazzfuzz)
[![CI Status](https://github.com/jake-g/jazzfuzz/actions/workflows/ci.yml/badge.svg)](https://github.com/jake-g/jazzfuzz/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-deployed-success?logo=github&style=flat)](https://jake-g.github.io/jazzfuzz/)
[![Glossary Albums](https://img.shields.io/badge/Glossary-Albums-success?style=flat)](https://jake-g.github.io/jazzfuzz/list.html?view=glossary)
[![Queue](https://img.shields.io/badge/Todo-Queue-success?style=flat)](https://jake-g.github.io/jazzfuzz/list.html?view=queue)

A sonic portal to a curated catalog of cosmic jazz albums with cover art, release details, track lists, and embedded players.

## Live Site
The site is hosted on GitHub Pages:
[https://jake-g.github.io/jazzfuzz/](https://jake-g.github.io/jazzfuzz/)

## Features
*   **Dynamic Sorting & Filtering:** Sort by artist, year, or popularity; filter by decade, genre, or artist.
*   **Collapsible Metadata:** Toggle album reviews globally or individually.
*   **Lite Players:** Uses `<lite-youtube>` to load video players on-demand.
*   **Playback Controls:** Global controls in the header (Prev, Play, Next, Shuffle) to navigate between visible albums, auto-advance on track completion, keep track history, and filter candidates dynamically.
*   **Glossary and Queue Views:** Client-side parsed layouts ([list.html](list.html)) for catalog overview and evaluation tracking.

## Popularity Metric
Albums are ranked 1 to 100 based on RateYourMusic charts, BestEverAlbums scores, and play counts:
*   **95 – 100:** Universal masterpieces (*Kind of Blue*, *A Love Supreme*).
*   **85 – 94:** Essential genre standards (*Head Hunters*, *Saxophone Colossus*).
*   **75 – 84:** Niche classics or highly-acclaimed modern records (*SOURCE*, *Piano Nights*).
*   **50 – 74:** Newly added / evaluation pending (default score is `50`).

## Development
New reviews added to [index.html](index.html) must use the layout in [template.html](template.html) and be sorted **reverse-chronologically** (newest first).

### Makefile Tooling
Run targets using `make <target>`:

| Target | Description |
| :--- | :--- |
| `setup` | Initialize Python virtual environment and install all requirements |
| `server` | Launch local development server at `http://localhost:3001` |
| `verify` | **Catch-all check:** formats files, runs pre-commit hooks, unit tests, audits links and classic years |
| `research-queue` | Match queue list albums against local MusicBee DB rating statistics |
| `queue-wizard` | Interactive wizard to screen, skip, delete, or promote queue albums |
| `import-album` | Import album from YTMusic directly: `make import-album ARTIST="..." ALBUM="..." [POPULARITY=50]` |
| `sort-queue` | Enforce popularity/year descending sort order on `albums_queue.tsv` |
| `sort-tsv` | Sort any TSV file: `make sort-tsv FILE="..." BY="newest\|oldest\|popular\|default"` |
| `test-links` | Validate all YouTube playlist/video links in the index file |
| `validate-years` | Scan index to check if classic albums use modern reissue years |
| `export-tsv` | Export active catalog to `albums_glossary.tsv` |
| `export-playlist` | Sync catalog albums sorted by popularity to your YouTube Music public playlist |
| `refresh-auth` | Prompt to paste browser cURL command and refresh local `browser.json` cookies |
| `test` | Run all Python unit tests |
| `format` | Trim trailing whitespaces and run code formatting |
| `clean` | Remove python bytecode cache |

### Quality Tools
*   **Pre-commit Hooks:** Automatically checks formatting, trailing whitespace, and file endings.
*   **GitHub Actions:** Automated test-runner pipeline (`ci.yml`) runs formatting and unit tests on push/PR.

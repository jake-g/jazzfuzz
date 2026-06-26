# Jazz Fuzz

[![View on GitHub](https://img.shields.io/badge/View_on-GitHub-181717?logo=github&style=flat)](https://github.com/jake-g/jazzfuzz)
[![CI Status](https://github.com/jake-g/jazzfuzz/actions/workflows/ci.yml/badge.svg)](https://github.com/jake-g/jazzfuzz/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-deployed-success?logo=github&style=flat)](https://jake-g.github.io/jazzfuzz/)
[![Album Glossary](https://img.shields.io/badge/Glossary-Album_Index-007acc?style=flat)](https://jake-g.github.io/jazzfuzz/glossary.html)
[![Evaluation Queue](https://img.shields.io/badge/Todo-Evaluation_Queue-orange?style=flat)](https://jake-g.github.io/jazzfuzz/todo.html)

A sonic portal to a curated catalog of cosmic jazz albums with cover art, release details, track lists, and embedded players.

## Core Features
*   **Dynamic Sorting & Filtering:** Sort by artist, year, or popularity; filter by decade, genre, or artist.
*   **Collapsible Metadata:** Toggle album reviews globally or individually.
*   **Lite Players:** Uses `<lite-youtube>` to load video players on-demand.
*   **Glossary & Todo Views:** Client-side parsed layouts ([glossary.html](glossary.html) / [todo.html](todo.html)) for catalog overview and evaluation tracking.

## Popularity Metric (`data-popularity`)
Albums are ranked 1 to 100 based on RateYourMusic charts, BestEverAlbums scores, and play counts:
*   **95 – 100:** Universal masterpieces (*Kind of Blue*, *A Love Supreme*).
*   **85 – 94:** Essential genre standards (*Head Hunters*, *Saxophone Colossus*).
*   **75 – 84:** Niche classics or highly-acclaimed modern records (*SOURCE*, *Piano Nights*).
*   **50 – 74:** Newly added / evaluation pending (default score is `50`).

## Development & Maintenance
New reviews added to [index.html](index.html) must use the layout in [template.html](template.html) and be sorted **reverse-chronologically** (newest first).

### Makefile Tooling
Run targets using `make <target>`:

| Target | Description |
| :--- | :--- |
| `server` | Launch local development server at `http://localhost:3001` |
| `verify` | **Catch-all check:** formats files, runs unit tests, audits links and classic years |
| `research-todos` | Match todo list albums against local MusicBee DB rating statistics |
| `todo-wizard` | Interactive wizard to screen, skip, delete, or promote todo albums |
| `import-album` | Import album from YTMusic directly: `make import-album ARTIST="..." ALBUM="..." [POPULARITY=50]` |
| `sort-todo` | Enforce popularity/year descending sort order on `albums_todo.tsv` |
| `sort-tsv` | Sort any TSV file: `make sort-tsv FILE="..." BY="newest\|oldest\|popular\|default"` |
| `test-links` | Validate all YouTube playlist/video links in the index file |
| `validate-years` | Scan index to check if classic albums use modern reissue years |
| `export-tsv` | Export active catalog to `albums_glossary.tsv` |
| `test` | Run all Python unit tests |
| `format` | Trim trailing whitespaces and run code formatting |
| `clean` | Remove python bytecode cache |

### CI/CD and Quality Tools
*   **Pre-commit Hooks:** Automatically checks formatting, trailing whitespace, and file endings.
*   **GitHub Actions:** Automated test-runner pipeline (`ci.yml`) runs formatting and unit tests on push/PR.

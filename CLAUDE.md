# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI tool that extracts chat history from a Beeper/Matrix SQLite database and performs topic analysis using semantic embeddings. Two main commands: `beeper-extract` (interactive chat selection + CSV export) and `beeper-analyze` (K-Means clustering on exported messages).

## Commands

```bash
uv sync                                  # install deps (mise run install)
uv run beeper-extract                    # extract chat history (mise run extract)
uv run beeper-analyze output/chat.csv    # analyze topics (mise run analyze -- output/chat.csv)
uv run beeper-diagnose                   # inspect DB schema (mise run diagnose)
uv run pytest                            # run tests (mise run test)
uv run ruff check . && uv run ruff format --check .  # lint (mise run lint)
uv run ruff format . && uv run ruff check --fix .    # format (mise run format)
```

## Architecture

### Extract (`__main__.py`)

1. Open SQLite database at `DATABASE_PATH`
2. Query `threads` table, parse JSON for chat names
3. Present interactive selection to user
4. Query `mx_room_messages` for the selected thread
5. Parse messages (clean sender IDs, timestamps, JSON bodies)
6. Export to CSV in `output/`

### Analyze (`analyze.py`)

1. Load exported CSV
2. Filter out short messages (< `MIN_MESSAGE_LENGTH` chars)
3. Generate embeddings with `sentence-transformers` (`all-MiniLM-L6-v2`)
4. K-Means clustering into `NUM_TOPICS` groups
5. Extract TF-IDF keywords per cluster
6. Print report + save categorized CSV

### Utilities

- `utils/db.py` - SQLite access (thread listing, message fetching)
- `utils/parser.py` - Message cleanup (sender IDs, timestamps, JSON bodies)

## Conventions & gotchas

- The database file (`index.db`) is git-ignored and user-specific. Set `DATABASE_PATH` in `.env`.
- The `threads` table stores JSON blobs with chat metadata; name can be in `name`, `title`, `display_name`, or `meta.name`/`meta.title`.
- Matrix timestamps are millisecond epoch (divided by 1000 if > 1 trillion).
- WhatsApp bridge users have IDs like `@whatsapp_919876543210:beeper.local` - these are shortened to `User_XXXXXX`.
- Message bodies may be stored as JSON objects with a `body` field - the parser extracts the text.
- Topic analysis uses a local model (no API keys needed) but first run downloads ~90MB.

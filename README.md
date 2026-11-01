# Beeper Chat Organizer

Extract chat history from a Beeper/Matrix SQLite database and analyze conversation topics using semantic embeddings and clustering.

## Features

- Extracts chat threads from Beeper's local SQLite database
- Interactive chat selection for targeted extraction
- Cleans Matrix user IDs and timestamps into readable formats
- Handles JSON-encoded message bodies
- Topic analysis using sentence-transformers + K-Means clustering
- TF-IDF keyword extraction per topic cluster
- Exports to CSV

## Requirements

- Python 3.12+
- `uv` package manager
- A Beeper `index.db` database file

## Installation

1. Sync dependencies:

   ```bash
   uv sync
   ```

2. Copy and configure environment:

   ```bash
   cp .env.example .env
   ```

3. Place your `index.db` in the project root (or set `DATABASE_PATH` in `.env`).

## Project Structure

```text
beeper-chat-organizer/
├── src/beeper_chat_organizer/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Extract CLI entry point
│   ├── analyze.py           # Topic analysis CLI
│   ├── diagnose.py          # Database schema inspector
│   ├── config.py            # Environment variable loading
│   └── utils/
│       ├── __init__.py
│       ├── db.py            # SQLite database access
│       └── parser.py        # Message parsing and cleanup
├── tests/
│   ├── test_parser.py
│   └── test_db.py
├── output/                  # Exported CSVs
├── docs/
├── .github/workflows/ci.yml
├── pyproject.toml
├── mise.toml
├── .env.example
└── README.md
```

## Usage

### 1. Inspect your database

```bash
uv run beeper-diagnose
```

### 2. Extract chat history

```bash
uv run beeper-extract
```

This shows available chats, lets you select one, and exports to `output/<chat_name>_archive.csv`.

### 3. Analyze topics

```bash
uv run beeper-analyze output/My_Chat_archive.csv
```

Options:

```bash
uv run beeper-analyze output/chat.csv --topics 10 --min-length 20
```

### Using mise

```bash
mise run extract
mise run analyze -- output/chat.csv --topics 5
mise run diagnose
```

## Configuration

All settings via `.env` (or CLI arguments where applicable):

| Variable             | Default            | Description                      |
| -------------------- | ------------------ | -------------------------------- |
| `DATABASE_PATH`      | `index.db`         | Path to Beeper SQLite database   |
| `OUTPUT_DIR`         | `output`           | Export directory                 |
| `NUM_TOPICS`         | `8`                | K-Means cluster count            |
| `MIN_MESSAGE_LENGTH` | `15`               | Min chars to include in analysis |
| `EMBEDDING_MODEL`    | `all-MiniLM-L6-v2` | Sentence transformer model       |

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

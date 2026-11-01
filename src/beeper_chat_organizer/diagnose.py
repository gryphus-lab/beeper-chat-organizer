"""Diagnostic utility to inspect the database schema."""

import sqlite3
import sys

from .config import DATABASE_PATH


def main() -> int:
    """Print tables found in the Beeper database."""
    db_path = DATABASE_PATH

    if not db_path.exists():
        print(f"Error: Database not found at '{db_path}'")
        return 1

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()

    print("Tables found in your database:")
    for table in sorted(tables):
        print(f"  - {table}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

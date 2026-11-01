"""Database access layer for Beeper/Matrix SQLite databases."""

import json
import sqlite3
from pathlib import Path

import pandas as pd


def get_threads(db_path: Path) -> pd.DataFrame:
    """Fetch and parse chat threads from the database.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        DataFrame with 'chat_id' and 'chat_name' columns.
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT threadid, thread FROM threads")
    raw_rows = cursor.fetchall()
    conn.close()

    parsed_threads = []
    for row in raw_rows:
        t_id = str(row[0])
        t_json_str = row[1]

        chat_name = _extract_chat_name(t_id, t_json_str)
        if chat_name:
            parsed_threads.append({"chat_id": t_id, "chat_name": chat_name})

    df = pd.DataFrame(parsed_threads)
    if not df.empty:
        df = df.drop_duplicates(subset=["chat_id"]).reset_index(drop=True)

    return df


def get_messages(db_path: Path, thread_id: str) -> list[tuple]:
    """Fetch raw messages for a specific thread.

    Args:
        db_path: Path to the SQLite database.
        thread_id: The thread/room ID to query.

    Returns:
        List of (sendercontactid, timestamp, message) tuples.
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sendercontactid, timestamp, message
        FROM mx_room_messages
        WHERE roomid = ?
        ORDER BY timestamp ASC
        """,
        (thread_id,),
    )
    messages = cursor.fetchall()
    conn.close()
    return messages


def get_all_messages(db_path: Path) -> list[tuple]:
    """Fetch all messages across all threads.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        List of (roomid, sendercontactid, timestamp, message) tuples.
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT roomid, sendercontactid, timestamp, message
        FROM mx_room_messages
        ORDER BY timestamp ASC
        """
    )
    messages = cursor.fetchall()
    conn.close()
    return messages


def _extract_chat_name(thread_id: str, json_str: str) -> str | None:
    """Parse chat name from thread JSON data."""
    try:
        data = json.loads(json_str)
        name = data.get("name") or data.get("title") or data.get("display_name")
        if not name and "meta" in data:
            name = data["meta"].get("name") or data["meta"].get("title")
        return name
    except Exception as e:
        print(f"Error parsing thread data for ID {thread_id}: {e}")
        return None

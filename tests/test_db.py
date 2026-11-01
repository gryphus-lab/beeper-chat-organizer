"""Tests for database access layer."""

import json
import sqlite3
from pathlib import Path

import pytest

from beeper_chat_organizer.utils.db import _extract_chat_name, get_messages, get_threads


@pytest.fixture
def sample_db(tmp_path) -> Path:
    """Create a minimal test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE threads (threadid TEXT, thread TEXT)")
    cursor.execute(
        "INSERT INTO threads VALUES (?, ?)",
        ("!room1:matrix.org", json.dumps({"name": "Test Group"})),
    )
    cursor.execute(
        "INSERT INTO threads VALUES (?, ?)",
        ("!room2:matrix.org", json.dumps({"title": "Another Chat"})),
    )

    cursor.execute(
        "CREATE TABLE mx_room_messages "
        "(roomid TEXT, sendercontactid TEXT, timestamp INTEGER, message TEXT)"
    )
    cursor.execute(
        "INSERT INTO mx_room_messages VALUES (?, ?, ?, ?)",
        ("!room1:matrix.org", "@alice:matrix.org", 1705320000000, "Hello!"),
    )
    cursor.execute(
        "INSERT INTO mx_room_messages VALUES (?, ?, ?, ?)",
        ("!room1:matrix.org", "@bob:matrix.org", 1705320060000, "Hi!"),
    )

    conn.commit()
    conn.close()
    return db_path


class TestGetThreads:
    """Test thread fetching."""

    def test_returns_threads(self, sample_db):
        df = get_threads(sample_db)
        assert len(df) == 2
        assert "Test Group" in df["chat_name"].values
        assert "Another Chat" in df["chat_name"].values

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE threads (threadid TEXT, thread TEXT)")
        conn.commit()
        conn.close()

        df = get_threads(db_path)
        assert df.empty


class TestGetMessages:
    """Test message fetching."""

    def test_returns_messages_for_room(self, sample_db):
        messages = get_messages(sample_db, "!room1:matrix.org")
        assert len(messages) == 2

    def test_empty_for_unknown_room(self, sample_db):
        messages = get_messages(sample_db, "!unknown:matrix.org")
        assert len(messages) == 0


class TestExtractChatName:
    """Test chat name extraction from JSON."""

    def test_name_field(self):
        assert _extract_chat_name("id", '{"name": "My Group"}') == "My Group"

    def test_title_field(self):
        assert _extract_chat_name("id", '{"title": "Chat Title"}') == "Chat Title"

    def test_meta_name(self):
        data = json.dumps({"meta": {"name": "Nested Name"}})
        assert _extract_chat_name("id", data) == "Nested Name"

    def test_invalid_json(self):
        assert _extract_chat_name("id", "not json") is None

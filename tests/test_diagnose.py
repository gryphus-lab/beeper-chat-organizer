"""Tests for the database diagnostic CLI."""

import sqlite3

from beeper_chat_organizer import diagnose


def test_main_missing_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(diagnose, "DATABASE_PATH", tmp_path / "missing.db")

    assert diagnose.main() == 1
    assert "Database not found" in capsys.readouterr().out


def test_main_lists_tables_in_sorted_order(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "beeper.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE z_table (id INTEGER)")
        connection.execute("CREATE TABLE a_table (id INTEGER)")
    monkeypatch.setattr(diagnose, "DATABASE_PATH", db_path)

    assert diagnose.main() == 0
    output = capsys.readouterr().out
    assert output.index("a_table") < output.index("z_table")

"""Tests for the chat extraction CLI."""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from beeper_chat_organizer import __main__ as extractor


def test_parse_args_defaults_and_options(monkeypatch):
    monkeypatch.setattr("sys.argv", ["beeper-extract"])
    args = extractor.parse_args()
    assert args.all is False
    assert args.db == extractor.DATABASE_PATH
    assert args.output_dir == extractor.OUTPUT_DIR

    monkeypatch.setattr(
        "sys.argv",
        [
            "beeper-extract",
            "--all",
            "--db",
            "archive.db",
            "--output-dir",
            "exports",
        ],
    )
    args = extractor.parse_args()
    assert args.all is True
    assert args.db == Path("archive.db")
    assert args.output_dir == Path("exports")


def test_sanitize_filename():
    assert extractor._sanitize_filename("  Work & Friends!  ") == "Work__Friends"
    assert extractor._sanitize_filename("  !!!  ") == ""


def test_export_chat_skips_missing_and_unparseable_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(extractor, "get_messages", lambda *_: [])
    assert extractor._export_chat(Path("db"), "room", "name", tmp_path) is None

    monkeypatch.setattr(extractor, "get_messages", lambda *_: [("sender", 0, "")])
    assert extractor._export_chat(Path("db"), "room", "name", tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_run_export_all_empty_threads(monkeypatch, capsys):
    monkeypatch.setattr(extractor, "get_threads", lambda _: pd.DataFrame())
    assert extractor.run_export_all(Path("db"), Path("output")) == 1
    assert "No chat threads" in capsys.readouterr().out


def test_run_export_all_skips_empty_and_writes_chat_and_combined_csv(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    threads = pd.DataFrame(
        [
            {"chat_id": "valid", "chat_name": "A Good Chat"},
            {"chat_id": "missing", "chat_name": "No Messages"},
            {"chat_id": "empty", "chat_name": "No Parsed Messages"},
        ]
    )
    messages = {
        "valid": [("@alice:matrix.org", 1705320000000, "A useful message")],
        "empty": [("@bob:matrix.org", 1705320000000, "  ")],
    }
    all_messages = [
        ("valid", "@alice:matrix.org", 1705320000000, "A useful message"),
        ("unknown", None, None, "Another useful message"),
    ]
    monkeypatch.setattr(extractor, "get_threads", lambda _: threads)
    monkeypatch.setattr(
        extractor, "get_messages", lambda _, room: messages.get(room, [])
    )
    monkeypatch.setattr(extractor, "get_all_messages", lambda _: all_messages)

    assert extractor.run_export_all(Path("db"), Path("output")) == 0

    output = tmp_path / "output"
    assert (output / "A_Good_Chat_archive.csv").exists()
    assert (output / "complete_history.csv").exists()
    assert "no messages, skipping" in capsys.readouterr().out
    combined = pd.read_csv(output / "complete_history.csv")
    assert combined["Chat"].tolist() == ["A Good Chat", "unknown"]
    assert combined["Sender_ID"].tolist() == ["alice", "Unknown"]


def test_parse_all_with_chat_names_filters_empty_and_maps_unknown_room():
    threads = pd.DataFrame([{"chat_id": "known", "chat_name": "Known Chat"}])
    parsed = extractor._parse_all_with_chat_names(
        [
            ("known", "@alice:matrix.org", 1705320000000, "Hi"),
            ("other", None, None, "Hello"),
            ("known", "@bob:matrix.org", 0, ""),
        ],
        threads,
    )
    assert parsed["Chat"].tolist() == ["Known Chat", "other"]
    assert parsed["Sender_ID"].tolist() == ["alice", "Unknown"]
    assert parsed["Message"].tolist() == ["Hi", "Hello"]

    empty = extractor._parse_all_with_chat_names(
        [("known", "@alice:matrix.org", 0, "")], threads
    )
    assert empty.empty


def test_run_interactive_empty_threads(monkeypatch, capsys):
    monkeypatch.setattr(extractor, "get_threads", lambda _: pd.DataFrame())
    assert extractor.run_interactive(Path("db"), Path("output")) == 1
    assert "No chat threads" in capsys.readouterr().out


@pytest.mark.parametrize("selection", ["not-a-number", "9"])
def test_run_interactive_rejects_invalid_selection(selection, monkeypatch, capsys):
    threads = pd.DataFrame([{"chat_id": "room", "chat_name": "Chat"}])
    monkeypatch.setattr(extractor, "get_threads", lambda _: threads)
    monkeypatch.setattr("builtins.input", lambda _: selection)
    assert extractor.run_interactive(Path("db"), Path("output")) == 1
    assert "Invalid selection" in capsys.readouterr().out


def test_run_interactive_no_messages(monkeypatch, capsys):
    threads = pd.DataFrame([{"chat_id": "room", "chat_name": "Chat"}])
    monkeypatch.setattr(extractor, "get_threads", lambda _: threads)
    monkeypatch.setattr("builtins.input", lambda _: "0")
    monkeypatch.setattr(extractor, "_export_chat", lambda *args: None)
    assert extractor.run_interactive(Path("db"), Path("output")) == 1
    assert "No messages found" in capsys.readouterr().out


def test_run_interactive_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    threads = pd.DataFrame([{"chat_id": "room", "chat_name": "Chat"}])
    monkeypatch.setattr(extractor, "get_threads", lambda _: threads)
    monkeypatch.setattr("builtins.input", lambda _: "0")
    monkeypatch.setattr(
        extractor,
        "get_messages",
        lambda *_: [("@alice:matrix.org", 1705320000000, "A useful message")],
    )
    assert extractor.run_interactive(Path("db"), Path("output")) == 0
    assert (tmp_path / "output" / "Chat_archive.csv").exists()
    assert "Success!" in capsys.readouterr().out


@pytest.mark.parametrize("export_all", [False, True])
def test_main_dispatches_when_database_exists(tmp_path, monkeypatch, export_all):
    db_path = tmp_path / "beeper.db"
    db_path.touch()
    args = SimpleNamespace(db=db_path, output_dir=tmp_path / "output", all=export_all)
    monkeypatch.setattr(extractor, "parse_args", lambda: args)
    calls = []
    monkeypatch.setattr(
        extractor,
        "run_export_all",
        lambda db, output: calls.append(("all", db, output)) or 0,
    )
    monkeypatch.setattr(
        extractor,
        "run_interactive",
        lambda db, output: calls.append(("interactive", db, output)) or 0,
    )
    assert extractor.main() == 0
    expected_mode = "all" if export_all else "interactive"
    assert calls == [(expected_mode, db_path, args.output_dir)]


def test_main_missing_database(tmp_path, monkeypatch, capsys):
    args = SimpleNamespace(db=tmp_path / "missing.db", output_dir=tmp_path, all=False)
    monkeypatch.setattr(extractor, "parse_args", lambda: args)
    assert extractor.main() == 1
    assert "Database not found" in capsys.readouterr().out

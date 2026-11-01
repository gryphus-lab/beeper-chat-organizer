"""Tests for safe output helpers."""

import os
from pathlib import Path

import pandas as pd
import pytest

from beeper_chat_organizer.utils.output import (
    ensure_private_output_dir,
    sanitize_csv_formula,
    sanitize_terminal_text,
    write_private_csv,
)


def test_sanitize_csv_formula_prefixes():
    for prefix in ("=", "+", "-", "@"):
        value = f"{prefix}SUM(A1:A2)"
        assert sanitize_csv_formula(value) == f"'{value}"


def test_sanitize_terminal_text_removes_control_characters():
    assert sanitize_terminal_text("\x1b]52;c;clipboard\x07Hello\nworld") == (
        "]52;c;clipboard Hello world"
    )


def test_output_directory_is_private_and_restricted_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    output_dir = ensure_private_output_dir(Path("output"))
    assert output_dir == tmp_path / "output"
    assert os.stat(output_dir).st_mode & 0o777 == 0o700

    with pytest.raises(ValueError, match="outside the current directory"):
        ensure_private_output_dir(tmp_path.parent / "outside")


def test_csv_is_formula_neutralized_and_owner_only(tmp_path):
    output_path = tmp_path / "private.csv"
    dataframe = pd.DataFrame({"Message": ["=1+1"], "Sender_ID": ["@SUM(A1:A2)"]})

    write_private_csv(dataframe, output_path)

    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "Message,Sender_ID",
        "'=1+1,'@SUM(A1:A2)",
    ]
    assert os.stat(output_path).st_mode & 0o777 == 0o600

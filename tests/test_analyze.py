"""Tests for topic analysis utilities."""

import pandas as pd

from beeper_chat_organizer.utils.output import sanitize_csv_formula


def test_sanitize_csv_formula_prefixes():
    for prefix in ("=", "+", "-", "@"):
        value = f"{prefix}SUM(A1:A2)"
        assert sanitize_csv_formula(value) == f"'{value}"


def test_sanitize_csv_formula_after_whitespace_or_control_prefix():
    for value in ("  =1+1", "\t=1+1", "\r=1+1", "\n=1+1"):
        assert sanitize_csv_formula(value) == f"'{value}"


def test_sanitize_csv_formula_preserves_safe_and_non_text_values():
    assert sanitize_csv_formula("ordinary text") == "ordinary text"
    assert sanitize_csv_formula(123) == 123


def test_sanitize_csv_formula_applies_to_all_exported_text_columns():
    df = pd.DataFrame(
        {"Message": ["=1+1"], "Sender_ID": ["@SUM(A1:A2)"], "Count": [1]}
    )

    sanitized = df.map(sanitize_csv_formula)

    assert sanitized.loc[0, "Message"] == "'=1+1"
    assert sanitized.loc[0, "Sender_ID"] == "'@SUM(A1:A2)"
    assert sanitized.loc[0, "Count"] == 1

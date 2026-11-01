"""Safe output helpers for chat exports."""

import os
import unicodedata
from pathlib import Path


def sanitize_csv_formula(value):
    """Prevent spreadsheet applications from interpreting text as formulas."""
    formula_prefixes = ("=", "+", "-", "@")
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(formula_prefixes)
    ):
        return f"'{value}"
    return value


def sanitize_terminal_text(value) -> str:
    """Replace terminal control characters in untrusted display text."""
    return "".join(
        "" if char == "\x1b" else " " if unicodedata.category(char) == "Cc" else char
        for char in str(value)
    )


def ensure_private_output_dir(path: Path) -> Path:
    """Create a private output directory contained in the current directory."""
    base_dir = Path.cwd().resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(base_dir):
        raise ValueError(f"Output directory is outside the current directory: {path}")

    resolved_path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if resolved_path != base_dir:
        resolved_path.chmod(0o700)
    return resolved_path


def write_private_csv(dataframe, path: Path) -> None:
    """Write a formula-neutralized CSV with owner-only permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(path, flags, 0o600)
    with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as output_file:
        if hasattr(os, "fchmod"):
            os.fchmod(output_file.fileno(), 0o600)
        else:
            os.chmod(path, 0o600)
        dataframe.map(sanitize_csv_formula).to_csv(output_file, index=False)

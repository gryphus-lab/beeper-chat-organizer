"""Main entry point - extract chat history from Beeper database."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import DATABASE_PATH, OUTPUT_DIR
from .utils.db import get_all_messages, get_messages, get_threads
from .utils.output import (
    ensure_private_output_dir,
    sanitize_terminal_text,
    write_private_csv,
)
from .utils.parser import parse_messages


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="beeper-extract",
        description="Extract chat history from a Beeper/Matrix database.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export ALL chats (complete history) without interactive selection",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DATABASE_PATH,
        help=f"Path to SQLite database (default: {DATABASE_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    return parser.parse_args()


def _sanitize_filename(name: str) -> str:
    """Convert a chat name into a safe filename."""
    return (
        "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    )


def _export_chat(
    db_path: Path, thread_id: str, chat_name: str, output_dir: Path
) -> Path | None:
    """Extract and export a single chat to CSV. Returns output path or None."""
    messages_raw = get_messages(db_path, thread_id)
    if not messages_raw:
        return None

    df = parse_messages(messages_raw)
    if df.empty:
        return None

    output_dir = ensure_private_output_dir(output_dir)
    clean_title = _sanitize_filename(chat_name)
    output_csv = output_dir / f"{clean_title}_archive.csv"
    write_private_csv(df, output_csv)
    return output_csv


def run_export_all(db_path: Path, output_dir: Path) -> int:
    """Export complete chat history for ALL threads."""
    print("Reading Beeper 'threads' database...")
    threads_df = get_threads(db_path)

    if threads_df.empty:
        print("No chat threads found in the database.")
        return 1

    print(f"Found {len(threads_df)} chat(s). Exporting all...\n")
    output_dir = ensure_private_output_dir(output_dir)

    total_messages = 0
    exported_count = 0

    for _, row in threads_df.iterrows():
        chat_id = row["chat_id"]
        chat_name = row["chat_name"]
        safe_chat_name = sanitize_terminal_text(chat_name)

        messages_raw = get_messages(db_path, chat_id)
        if not messages_raw:
            print(f"  [{safe_chat_name}] - no messages, skipping")
            continue

        df = parse_messages(messages_raw)
        if df.empty:
            print(f"  [{safe_chat_name}] - no parseable messages, skipping")
            continue

        clean_title = _sanitize_filename(chat_name)
        output_csv = output_dir / f"{clean_title}_archive.csv"
        write_private_csv(df, output_csv)

        total_messages += len(df)
        exported_count += 1
        print(f"  [{safe_chat_name}] -> {len(df)} messages -> {output_csv.name}")

    # Also export a combined file with all messages
    print("\nExporting combined history...")
    all_messages = get_all_messages(db_path)
    if all_messages:
        # Include chat name in combined export
        all_df = _parse_all_with_chat_names(all_messages, threads_df)
        if not all_df.empty:
            combined_path = output_dir / "complete_history.csv"
            write_private_csv(all_df, combined_path)
            print(f"  Combined -> {len(all_df)} messages -> {combined_path.name}")

    print(f"\nDone! Exported {total_messages} messages from {exported_count} chats.")
    return 0


def _parse_all_with_chat_names(
    messages_raw: list[tuple], threads_df: pd.DataFrame
) -> pd.DataFrame:
    """Parse all messages and add chat name column.

    messages_raw tuples: (roomid, sendercontactid, timestamp, message)
    """
    # Build room_id -> chat_name lookup
    chat_lookup = dict(zip(threads_df["chat_id"], threads_df["chat_name"]))

    parsed_rows = []
    for row in messages_raw:
        room_id = str(row[0]) if row[0] is not None else ""
        sender_raw = str(row[1]) if row[1] is not None else "Unknown"
        ts_raw = row[2]
        message_body = str(row[3]) if row[3] is not None else ""

        from .utils.parser import _clean_message, _clean_sender, _parse_timestamp

        sender_clean = _clean_sender(sender_raw)
        readable_ts = _parse_timestamp(ts_raw)
        message_clean = _clean_message(message_body)

        if message_clean:
            parsed_rows.append(
                {
                    "Chat": chat_lookup.get(room_id, room_id),
                    "Sender_ID": sender_clean,
                    "Timestamp": readable_ts,
                    "Message": message_clean,
                }
            )

    return pd.DataFrame(parsed_rows)


def run_interactive(db_path: Path, output_dir: Path) -> int:
    """Interactive single-chat extraction."""
    print("Reading Beeper 'threads' database...")
    threads_df = get_threads(db_path)

    if threads_df.empty:
        print("No chat threads found in the database.")
        return 1

    # Display available chats
    print("\n--- Available Beeper Chats ---")
    for idx, row in threads_df.iterrows():
        print(f"[{idx}] {sanitize_terminal_text(row['chat_name'])}")

    # Get user selection
    try:
        selection = int(input("\nEnter the number corresponding to your group: "))
        target_thread_id = threads_df.iloc[selection]["chat_id"]
        group_name = threads_df.iloc[selection]["chat_name"]
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        return 1

    # Extract messages
    print(f"\nExtracting chat history for '{sanitize_terminal_text(group_name)}'...")
    output_path = _export_chat(db_path, target_thread_id, group_name, output_dir)

    if output_path is None:
        print("No messages found after parsing.")
        return 1

    # Show preview
    df = pd.read_csv(output_path)
    print("\n--- Extracted Data Sample Preview ---")
    print(df.head(10).map(sanitize_terminal_text))
    print(
        f"\nSuccess! Exported {len(df)} total messages into: "
        f"'{sanitize_terminal_text(output_path)}'"
    )

    return 0


def main() -> int:
    """CLI entry point."""
    args = parse_args()

    if not args.db.exists():
        print(f"Error: Database not found at '{args.db}'")
        print("Set DATABASE_PATH in .env or place index.db in the project root.")
        return 1

    if args.all:
        return run_export_all(args.db, args.output_dir)
    else:
        return run_interactive(args.db, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())

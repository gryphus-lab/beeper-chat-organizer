"""Message parsing and cleanup utilities."""

import json
from datetime import datetime

import pandas as pd


def parse_messages(messages_raw: list[tuple]) -> pd.DataFrame:
    """Parse raw database rows into a clean DataFrame.

    Args:
        messages_raw: List of (sender_id, timestamp, message) tuples.

    Returns:
        DataFrame with Sender_ID, Timestamp, and Message columns.
    """
    parsed_rows = []

    for row in messages_raw:
        sender_raw = str(row[0]) if row[0] is not None else "Unknown"
        ts_raw = row[1]
        message_body = str(row[2]) if row[2] is not None else ""

        sender_clean = _clean_sender(sender_raw)
        readable_ts = _parse_timestamp(ts_raw)
        message_clean = _clean_message(message_body)

        if message_clean:
            parsed_rows.append(
                {
                    "Sender_ID": sender_clean,
                    "Timestamp": readable_ts,
                    "Message": message_clean,
                }
            )

    return pd.DataFrame(parsed_rows)


def _clean_sender(sender: str) -> str:
    """Clean Matrix user ID into a readable name.

    Strips the Matrix domain suffix and @ prefix.
    Shortens WhatsApp bridge identifiers.
    """
    sender_clean = sender.split(":")[0].replace("@", "")

    if "whatsapp_" in sender_clean:
        sender_clean = f"User_{sender_clean.split('_')[-1][:6]}"

    return sender_clean


def _parse_timestamp(ts_raw) -> str:
    """Parse Matrix epoch timestamp (milliseconds) into readable format."""
    try:
        ts_val = float(ts_raw)
        # Matrix uses millisecond timestamps
        if ts_val > 1_000_000_000_000:
            ts_val = ts_val / 1000.0
        return datetime.fromtimestamp(ts_val).strftime("%Y-%m-%d %I:%M %p")
    except (TypeError, ValueError, OSError):
        return str(ts_raw)


def _clean_message(message: str) -> str:
    """Clean and extract text from message body.

    Handles cases where the message column stores raw JSON dicts.
    """
    message = message.strip()
    if not message:
        return ""

    if message.startswith("{"):
        try:
            msg_json = json.loads(message)
            message = msg_json.get("body", message)
        except (json.JSONDecodeError, TypeError):
            pass

    return message.strip()

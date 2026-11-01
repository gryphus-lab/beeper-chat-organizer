"""Tests for message parser utilities."""

from beeper_chat_organizer.utils.parser import (
    _clean_message,
    _clean_sender,
    _parse_timestamp,
    parse_messages,
)


class TestCleanSender:
    """Test Matrix user ID cleaning."""

    def test_strips_domain_and_at(self):
        assert _clean_sender("@alice:matrix.org") == "alice"

    def test_whatsapp_bridge_user(self):
        result = _clean_sender("@whatsapp_919876543210:beeper.local")
        assert result.startswith("User_")
        assert len(result) <= 12

    def test_plain_sender(self):
        assert _clean_sender("bob") == "bob"

    def test_unknown(self):
        assert _clean_sender("Unknown") == "Unknown"


class TestParseTimestamp:
    """Test timestamp parsing."""

    def test_millisecond_epoch(self):
        # 2024-01-15 12:00:00 UTC in milliseconds
        result = _parse_timestamp(1705320000000)
        assert "2024" in result

    def test_second_epoch(self):
        result = _parse_timestamp(1705320000)
        assert "2024" in result

    def test_invalid_returns_string(self):
        result = _parse_timestamp("not_a_timestamp")
        assert result == "not_a_timestamp"

    def test_none_returns_string(self):
        result = _parse_timestamp(None)
        assert result == "None"


class TestCleanMessage:
    """Test message body cleanup."""

    def test_plain_text(self):
        assert _clean_message("Hello world") == "Hello world"

    def test_json_body(self):
        result = _clean_message('{"body": "Actual message", "type": "m.text"}')
        assert result == "Actual message"

    def test_empty_string(self):
        assert _clean_message("") == ""

    def test_whitespace_only(self):
        assert _clean_message("   ") == ""

    def test_invalid_json_passthrough(self):
        msg = "{broken json"
        assert _clean_message(msg) == msg

    def test_non_string_json_body_does_not_raise(self):
        assert _clean_message('{"body": 42}') == "42"
        assert _clean_message('{"body": null}') == "None"

    def test_deeply_nested_json_does_not_raise(self):
        msg = '{"body":' + "[" * 1100 + "0" + "]" * 1100 + "}"
        assert _clean_message(msg) == msg


class TestParseMessages:
    """Test full message parsing pipeline."""

    def test_basic_parsing(self):
        raw = [
            ("@alice:matrix.org", 1705320000000, "Hello!"),
            ("@bob:matrix.org", 1705320060000, "Hi there"),
        ]
        df = parse_messages(raw)
        assert len(df) == 2
        assert list(df.columns) == ["Sender_ID", "Timestamp", "Message"]
        assert df.iloc[0]["Sender_ID"] == "alice"

    def test_empty_messages_filtered(self):
        raw = [
            ("@alice:matrix.org", 1705320000000, ""),
            ("@bob:matrix.org", 1705320060000, "   "),
            ("@carol:matrix.org", 1705320120000, "Real message"),
        ]
        df = parse_messages(raw)
        assert len(df) == 1
        assert df.iloc[0]["Message"] == "Real message"

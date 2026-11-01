"""Tests for topic analysis utilities."""

import pandas as pd

from beeper_chat_organizer import analyze
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
    df = pd.DataFrame({"Message": ["=1+1"], "Sender_ID": ["@SUM(A1:A2)"], "Count": [1]})

    sanitized = df.map(sanitize_csv_formula)

    assert sanitized.loc[0, "Message"] == "'=1+1"
    assert sanitized.loc[0, "Sender_ID"] == "'@SUM(A1:A2)"
    assert sanitized.loc[0, "Count"] == 1


def test_analyze_chat_topics_returns_empty_after_filtering(tmp_path, capsys):
    csv_path = tmp_path / "messages.csv"
    pd.DataFrame({"Message": [None, "short"]}).to_csv(csv_path, index=False)

    result = analyze.analyze_chat_topics(csv_path, min_message_length=5)

    assert result.empty
    assert "No messages remaining" in capsys.readouterr().out


def test_analyze_chat_topics_clusters_and_reports_without_loading_model(
    tmp_path, monkeypatch, capsys
):
    csv_path = tmp_path / "messages.csv"
    pd.DataFrame(
        {
            "Message": [
                "cats purr softly every evening",
                "cats enjoy warm sunny windows",
                "space rockets explore distant planets",
                None,
                "tiny",
            ]
        }
    ).to_csv(csv_path, index=False)

    class FakeModel:
        def __init__(self, model_name):
            assert model_name == "test-model"

        def encode(self, messages, show_progress_bar):
            assert len(messages) == 3
            assert show_progress_bar is True
            return ["embedding"] * len(messages)

    class FakeKMeans:
        def __init__(self, n_clusters, random_state, n_init):
            assert (n_clusters, random_state, n_init) == (2, 42, 10)

        def fit_predict(self, embeddings):
            assert len(embeddings) == 3
            return [0, 0, 1]

    monkeypatch.setattr(analyze, "SentenceTransformer", FakeModel)
    monkeypatch.setattr(analyze, "KMeans", FakeKMeans)
    result = analyze.analyze_chat_topics(
        csv_path, num_topics=2, min_message_length=5, model_name="test-model"
    )

    assert result["Topic_ID"].tolist() == [0, 0, 1]
    output = capsys.readouterr().out
    assert "TOPIC #0 (2 messages)" in output
    assert "TOPIC #1" not in output


def test_print_topic_report_handles_tfidf_failure(monkeypatch, capsys):
    class FailingVectorizer:
        def __init__(self, **kwargs):
            pass

        def fit_transform(self, _):
            raise ValueError("no terms")

    monkeypatch.setattr(analyze, "TfidfVectorizer", FailingVectorizer)
    dataframe = pd.DataFrame(
        {"Topic_ID": [0, 0], "Message": ["first message", "second message"]}
    )

    analyze._print_topic_report(dataframe, num_topics=1)

    output = capsys.readouterr().out
    assert "Core Keywords:** N/A" in output
    assert "first message" in output


def test_main_missing_csv(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["beeper-analyze", str(tmp_path / "missing.csv")])
    assert analyze.main() == 1
    assert "File not found" in capsys.readouterr().out


def test_main_empty_analysis_does_not_write_output(tmp_path, monkeypatch):
    csv_path = tmp_path / "messages.csv"
    csv_path.touch()
    monkeypatch.setattr("sys.argv", ["beeper-analyze", str(csv_path)])
    monkeypatch.setattr(
        analyze,
        "analyze_chat_topics",
        lambda *args, **kwargs: pd.DataFrame(),
    )
    monkeypatch.chdir(tmp_path)

    assert analyze.main() == 0
    assert not (tmp_path / "output").exists()


def test_main_writes_nonempty_analysis(tmp_path, monkeypatch, capsys):
    csv_path = tmp_path / "messages.csv"
    csv_path.touch()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["beeper-analyze", str(csv_path), "--topics", "2", "--min-length", "4"],
    )
    dataframe = pd.DataFrame({"Message": ["interesting"], "Topic_ID": [0]})
    received = {}

    def fake_analyze(path, **kwargs):
        received["path"] = path
        received.update(kwargs)
        return dataframe

    monkeypatch.setattr(analyze, "analyze_chat_topics", fake_analyze)

    assert analyze.main() == 0
    assert received == {
        "path": csv_path,
        "num_topics": 2,
        "min_message_length": 4,
    }
    assert pd.read_csv(tmp_path / "output" / "categorized_topics.csv").equals(dataframe)
    assert "Success!" in capsys.readouterr().out

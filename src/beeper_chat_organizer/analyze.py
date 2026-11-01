"""Topic analysis of exported chat history using semantic embeddings."""

import argparse
import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import EMBEDDING_MODEL, MIN_MESSAGE_LENGTH, NUM_TOPICS, OUTPUT_DIR
from .utils.output import (
    ensure_private_output_dir,
    sanitize_csv_formula as _sanitize_csv_formula,
    sanitize_terminal_text,
    write_private_csv,
)


def analyze_chat_topics(
    csv_path: Path,
    num_topics: int = NUM_TOPICS,
    min_message_length: int = MIN_MESSAGE_LENGTH,
    model_name: str = EMBEDDING_MODEL,
) -> pd.DataFrame:
    """Cluster chat messages by topic using semantic embeddings.

    Args:
        csv_path: Path to the exported chat CSV.
        num_topics: Number of topic clusters for K-Means.
        min_message_length: Minimum character length to include a message.
        model_name: Sentence transformer model for embeddings.

    Returns:
        DataFrame with Topic_ID column added.
    """
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Drop empty messages
    df = df.dropna(subset=["Message"])
    df["Message"] = df["Message"].astype(str)

    # Filter short messages to reduce noise
    df_filtered = df[df["Message"].str.len() > min_message_length].copy()
    print(
        f"Filtered out short responses. "
        f"Analyzing {len(df_filtered)} long-form messages..."
    )

    if df_filtered.empty:
        print("No messages remaining after filtering.")
        return df_filtered

    # Generate semantic embeddings
    print("Generating semantic vector maps for messages... (may take a minute)")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(df_filtered["Message"].tolist(), show_progress_bar=True)

    # Cluster via K-Means
    print(f"Clustering conversations into {num_topics} major thread topics...")
    kmeans = KMeans(n_clusters=num_topics, random_state=42, n_init=10)
    df_filtered["Topic_ID"] = kmeans.fit_predict(embeddings)

    # Report
    _print_topic_report(df_filtered, num_topics)

    return df_filtered


def _print_topic_report(df: pd.DataFrame, num_topics: int):
    """Print topic analysis report with keywords and samples."""
    print("\n" + "=" * 50)
    print("             TOPIC ANALYSIS REPORT                ")
    print("=" * 50 + "\n")

    vectorizer = TfidfVectorizer(stop_words="english", max_features=10)

    for topic_num in range(num_topics):
        topic_messages = df[df["Topic_ID"] == topic_num]["Message"]

        if len(topic_messages) < 2:
            continue

        # Extract keywords via TF-IDF
        combined_text = " ".join(topic_messages)
        try:
            vectorizer.fit_transform([combined_text])
            feature_names = vectorizer.get_feature_names_out()
            keywords = ", ".join(feature_names[:6])
        except Exception:
            keywords = "N/A"

        print(f"### TOPIC #{topic_num} ({len(topic_messages)} messages)")
        print(f"**Core Keywords:** {sanitize_terminal_text(keywords)}")
        print("**Sample Conversations:**")

        samples = topic_messages.sample(
            min(3, len(topic_messages)), random_state=42
        ).tolist()
        for sample in samples:
            sample = sanitize_terminal_text(sample)
            display = f'"{sample[:120]}..."' if len(sample) > 120 else f'"{sample}"'
            print(f" - {display}")
        print("-" * 50)


def main() -> int:
    """CLI entry point for topic analysis."""
    parser = argparse.ArgumentParser(
        prog="beeper-analyze",
        description="Analyze chat topics from exported CSV.",
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the exported chat CSV file",
    )
    parser.add_argument(
        "--topics",
        type=int,
        default=NUM_TOPICS,
        help=f"Number of topic clusters (default: {NUM_TOPICS})",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=MIN_MESSAGE_LENGTH,
        help=f"Minimum message length to analyze (default: {MIN_MESSAGE_LENGTH})",
    )
    args = parser.parse_args()

    if not args.csv_file.exists():
        print(f"Error: File not found: {args.csv_file}")
        return 1

    df_result = analyze_chat_topics(
        args.csv_file,
        num_topics=args.topics,
        min_message_length=args.min_length,
    )

    if not df_result.empty:
        output_dir = ensure_private_output_dir(OUTPUT_DIR)
        output_csv = output_dir / "categorized_topics.csv"
        write_private_csv(df_result, output_csv)
        print(f"\nSuccess! Categorized chat rows saved to '{output_csv}'")

    return 0


if __name__ == "__main__":
    sys.exit(main())

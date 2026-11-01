"""Configuration variables loaded from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# Path to the Beeper SQLite database
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "index.db"))

# Output directory for exported CSVs
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))

# Default number of topic clusters for analysis
NUM_TOPICS = int(os.environ.get("NUM_TOPICS", "8"))

# Minimum message length for topic analysis (filters out short replies)
MIN_MESSAGE_LENGTH = int(os.environ.get("MIN_MESSAGE_LENGTH", "15"))

# Sentence transformer model for embeddings
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

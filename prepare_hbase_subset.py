"""Create a reproducible, representative HBase session subset without altering raw data."""

from __future__ import annotations

import json
import random
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
RAW_FILE = PROJECT_DIR / "data" / "raw" / "sessions_0.json"
OUTPUT_DIR = PROJECT_DIR / "data" / "hbase"
OUTPUT_FILE = OUTPUT_DIR / "sessions_subset_10000.json"
SAMPLE_SIZE = 10_000


def main() -> None:
    print("Reading the first 100,000-session source file ...")
    with RAW_FILE.open(encoding="utf-8") as source:
        sessions = json.load(source)

    if len(sessions) < SAMPLE_SIZE:
        raise ValueError(f"Need {SAMPLE_SIZE:,} sessions but found only {len(sessions):,}.")

    # Fixed seed makes the exact representative sample reproducible.
    subset = random.Random(42).sample(sessions, SAMPLE_SIZE)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as destination:
        json.dump(subset, destination)

    print("HBase subset prepared")
    print(f"- Source sessions: {len(sessions):,}")
    print(f"- Random sample: {len(subset):,}")
    print(f"- Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

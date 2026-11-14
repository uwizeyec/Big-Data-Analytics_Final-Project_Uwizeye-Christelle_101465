"""Reassemble raw JSON files from data/raw_chunks and verify SHA-256 hashes.

Run from the project root after downloading/cloning every part:
    python restore_raw_files.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    chunks = root / "data" / "raw_chunks"
    raw = root / "data" / "raw"
    manifest_path = chunks / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw.mkdir(parents=True, exist_ok=True)

    for item in manifest["files"]:
        target = raw / item["original_name"]
        print(f"Restoring {target.name} ...")
        with target.open("wb") as out:
            for part_name in item["parts"]:
                part = chunks / part_name
                if not part.exists():
                    raise FileNotFoundError(f"Missing part: {part}")
                with part.open("rb") as inp:
                    for block in iter(lambda: inp.read(1024 * 1024), b""):
                        out.write(block)
        actual = sha256(target)
        if actual != item["sha256"]:
            raise RuntimeError(f"Checksum failed for {target.name}")
        print(f"  verified {target.name}: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

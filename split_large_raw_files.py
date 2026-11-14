"""Split large raw JSON exports into GitHub-safe binary parts.

Run once from the project root:
    python split_large_raw_files.py

The original source files are never changed. Output parts are written to
data/raw_chunks, along with a manifest and a restore script. Each part is
45 MiB, below GitHub's 50 MB large-file warning threshold and the 100 MB hard
limit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CHUNK_SIZE = 45 * 1024 * 1024
FILES = ("sessions_0.json", "sessions_1.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    raw = root / "data" / "raw"
    out = root / "data" / "raw_chunks"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"chunk_size_bytes": CHUNK_SIZE, "files": []}

    for name in FILES:
        source = raw / name
        if not source.exists():
            raise FileNotFoundError(f"Missing source file: {source}")
        print(f"Splitting {name} ({source.stat().st_size:,} bytes) ...")
        parts: list[str] = []
        with source.open("rb") as inp:
            part_no = 1
            while block := inp.read(CHUNK_SIZE):
                part_name = f"{name}.part{part_no:03d}"
                (out / part_name).write_bytes(block)
                parts.append(part_name)
                print(f"  created {part_name}: {len(block):,} bytes")
                part_no += 1
        manifest["files"].append({
            "original_name": name,
            "original_bytes": source.stat().st_size,
            "sha256": sha256(source),
            "parts": parts,
        })

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Created {len(manifest['files'])} chunked file sets in {out}")
    print("Commit data/raw_chunks to GitHub. Restore later with restore_raw_files.py.")


if __name__ == "__main__":
    main()

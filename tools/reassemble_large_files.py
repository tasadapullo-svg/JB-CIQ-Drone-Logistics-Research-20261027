#!/usr/bin/env python3
"""Reassemble split research assets and verify their SHA256 hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "reassembled_large_files"


def reassemble(manifest_path: Path, verify_only: bool = False) -> Path | None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_parent = manifest_path.parent.parent.relative_to(REPOSITORY_ROOT)
    output_path = OUTPUT_ROOT / relative_parent / manifest["target_filename"]
    if not verify_only:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    actual_size = 0
    destination = None if verify_only else output_path.open("wb")
    try:
        for part_name in manifest["parts"]:
            part_path = manifest_path.parent / part_name
            if not part_path.is_file():
                raise FileNotFoundError(f"Missing part: {part_path}")
            with part_path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    actual_size += len(block)
                    digest.update(block)
                    if destination is not None:
                        destination.write(block)
    finally:
        if destination is not None:
            destination.close()

    expected_size = int(manifest["original_size_bytes"])
    if actual_size != expected_size:
        raise RuntimeError(f"Size mismatch: {actual_size} != {expected_size}")
    actual_hash = digest.hexdigest()
    expected_hash = manifest["sha256"].lower()
    if actual_hash != expected_hash:
        raise RuntimeError(f"SHA256 mismatch: {actual_hash} != {expected_hash}")
    return None if verify_only else output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifests = sorted(REPOSITORY_ROOT.rglob("parts_manifest.json"))
    if not manifests:
        raise SystemExit("No split-file manifests were found.")
    for manifest_path in manifests:
        output_path = reassemble(manifest_path, verify_only=args.verify_only)
        label = manifest_path.parent if output_path is None else output_path
        print(f"verified: {label.relative_to(REPOSITORY_ROOT)}")
    print(f"completed: {len(manifests)} files verified")


if __name__ == "__main__":
    main()

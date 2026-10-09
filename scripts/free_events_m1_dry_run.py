#!/usr/bin/env python3
"""Offline JSONL admission preview; no scraping, PostgreSQL mutation or AI."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.free_events_manifest import prepare_manifest  # noqa: E402
from free_events_m0_baseline import load_registry  # noqa: E402

MAX_BATCH_BYTES = 10 * 1024 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview public event catalog candidates offline")
    parser.add_argument("candidates", type=Path, help="Locally reviewed JSONL input; no URLs fetched")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/free_events_m0_sources.json")
    args = parser.parse_args()
    if args.candidates.stat().st_size > MAX_BATCH_BYTES:
        raise ValueError("candidate file exceeds 10 MiB limit")
    registry = load_registry(args.registry)
    with args.candidates.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]
    preview = prepare_manifest(records, registry)
    print(json.dumps(preview, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

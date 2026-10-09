#!/usr/bin/env python3
"""Validate a local MoC JSON export and preview M1 catalog admission only."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.free_events_manifest import prepare_manifest  # noqa: E402
from app.services.free_events_moc_adapter import normalize_moc_record  # noqa: E402
from free_events_m0_baseline import load_registry  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline MoC event JSON admission preview")
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()
    if args.json_file.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("input exceeds bounded 10 MiB")
    raw = json.loads(args.json_file.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) > 5000:
        raise ValueError("expected bounded JSON array of MoC event records")
    admitted = []
    invalid = 0
    for row in raw:
        try:
            if not isinstance(row, dict):
                raise ValueError("expected record object")
            admitted.append(normalize_moc_record(row).model_dump(mode="json"))
        except (ValueError, TypeError):
            invalid += 1
    report = prepare_manifest(admitted, load_registry())
    report["source_adapter"] = "moc_all_categories_offline"
    report["rejected_by_adapter"] = invalid
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

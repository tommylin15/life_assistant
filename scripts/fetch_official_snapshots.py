"""
Fetch Taiwan Official Event Snapshots (Culture & Tourism) using TW Request Router.
Part of Taiwan Activity Discovery Step 01 Batch execution.
Saves lossless gzip/zip and manifests into Google Drive 官方來源快照.
"""

import gzip
import hashlib
import json
import logging
import os
import sys
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple

sys.path.append("backend")
from app.services.tw_request_router import smart_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TPE_TZ = timezone(timedelta(hours=8))

SNAPSHOTS_DIR = Path(
    "/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/官方來源快照"
)

CULTURE_URL = "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do?method=doFindTypeJ&category=all"
TOURISM_URL = "https://media.taiwan.net.tw/XMLReleaseAll_public/v2.0/Zh_tw/Event-json.zip"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_culture_snapshot(date_str: str, target_dir: Path) -> Tuple[bool, Dict[str, Any]]:
    file_name = f"culture-{date_str}.json.gz"
    manifest_name = f"{file_name}.manifest.json"
    gz_path = target_dir / file_name
    manifest_path = target_dir / manifest_name

    logger.info(f"Fetching Culture open data from {CULTURE_URL}...")
    try:
        resp = smart_request(CULTURE_URL, method="GET", timeout=120.0)
        if resp.status_code != 200:
            logger.error(f"Culture endpoint returned HTTP {resp.status_code}")
            return False, {"error": f"HTTP {resp.status_code}"}

        raw_bytes = resp.content
        raw_sha = sha256_bytes(raw_bytes)
        raw_size = len(raw_bytes)

        # Parse JSON and count records
        try:
            records = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(records, list):
                logger.error("Culture raw JSON is not a list")
                return False, {"error": "Invalid JSON format"}
        except Exception as e:
            logger.error(f"Failed to parse Culture JSON: {e}")
            return False, {"error": f"JSON parse error: {e}"}

        unique_uids = {r.get("UID") for r in records if isinstance(r, dict) and r.get("UID")}
        record_count = len(records)
        unique_count = len(unique_uids)

        # Compress lossless to gzip
        gz_bytes = gzip.compress(raw_bytes, compresslevel=9)
        stored_sha = sha256_bytes(gz_bytes)
        stored_size = len(gz_bytes)

        # Write gzip
        with open(gz_path, "wb") as f:
            f.write(gz_bytes)

        # Write manifest
        now_tpe = datetime.now(TPE_TZ).isoformat()
        manifest_data = {
            "source_key": "culture",
            "snapshot_date": date_str,
            "created_at_tpe": now_tpe,
            "file_name": file_name,
            "stored_bytes": stored_size,
            "stored_sha256": stored_sha,
            "raw_bytes": raw_size,
            "raw_sha256": raw_sha,
            "records_count": record_count,
            "unique_records_count": unique_count,
            "status": "PASS",
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Successfully saved {file_name}: {record_count} records ({unique_count} distinct UIDs), stored_bytes={stored_size}"
        )
        return True, manifest_data
    except Exception as e:
        logger.error(f"Exception fetching culture snapshot: {e}")
        return False, {"error": str(e)}


def fetch_tourism_snapshot(date_str: str, target_dir: Path) -> Tuple[bool, Dict[str, Any]]:
    file_name = f"tourism-{date_str}.zip"
    manifest_name = f"{file_name}.manifest.json"
    zip_path = target_dir / file_name
    manifest_path = target_dir / manifest_name

    logger.info(f"Fetching Tourism open data from {TOURISM_URL}...")
    try:
        resp = smart_request(TOURISM_URL, method="GET", timeout=120.0)
        if resp.status_code != 200:
            logger.error(f"Tourism endpoint returned HTTP {resp.status_code}")
            return False, {"error": f"HTTP {resp.status_code}"}

        zip_bytes = resp.content
        stored_sha = sha256_bytes(zip_bytes)
        stored_size = len(zip_bytes)

        # Write ZIP preserving exact official bytes
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        # Inspect ZIP and parse EventList.json
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Find EventList.json
                event_list_names = [n for n in zf.namelist() if "EventList.json" in n]
                if not event_list_names:
                    return False, {"error": "EventList.json not found in ZIP"}
                inner_name = event_list_names[0]
                inner_bytes = zf.read(inner_name)
                # Tolerate UTF-8 BOM
                if inner_bytes.startswith(b"\xef\xbb\xbf"):
                    inner_bytes = inner_bytes[3:]
                inner_sha = sha256_bytes(inner_bytes)
                inner_data = json.loads(inner_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to inspect Tourism ZIP: {e}")
            return False, {"error": f"ZIP inspect error: {e}"}

        # Extract items
        items = []
        if isinstance(inner_data, dict):
            # Typically {"XMLHead": {"Infos": {"Info": [...]}}}
            infos = inner_data.get("XMLHead", {}).get("Infos", {}).get("Info", [])
            items = infos if isinstance(infos, list) else [infos]
        elif isinstance(inner_data, list):
            items = inner_data

        record_count = len(items)
        unique_ids = {it.get("Id") or it.get("EventID") for it in items if isinstance(it, dict)}
        unique_count = len(unique_ids)

        now_tpe = datetime.now(TPE_TZ).isoformat()
        manifest_data = {
            "source_key": "tourism_zip",
            "snapshot_date": date_str,
            "created_at_tpe": now_tpe,
            "file_name": file_name,
            "stored_bytes": stored_size,
            "stored_sha256": stored_sha,
            "event_list_sha256": inner_sha,
            "records_count": record_count,
            "unique_records_count": unique_count,
            "status": "PASS",
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Successfully saved {file_name}: {record_count} records ({unique_count} distinct IDs), stored_bytes={stored_size}"
        )
        return True, manifest_data
    except Exception as e:
        logger.error(f"Exception fetching tourism snapshot: {e}")
        return False, {"error": str(e)}


def main():
    now_tpe = datetime.now(TPE_TZ)
    date_str = now_tpe.strftime("%Y-%m-%d")
    target_dir = SNAPSHOTS_DIR

    if not target_dir.exists():
        logger.warning(f"Target dir {target_dir} not mounted; using /tmp/tw_snapshots")
        target_dir = Path("/tmp/tw_snapshots")
        target_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Starting Official Snapshots Fetch for {date_str} (Asia/Taipei) ===")
    c_ok, c_meta = fetch_culture_snapshot(date_str, target_dir)
    t_ok, t_meta = fetch_tourism_snapshot(date_str, target_dir)

    print(f"Culture snapshot result: ok={c_ok}, meta={c_meta}")
    print(f"Tourism snapshot result: ok={t_ok}, meta={t_meta}")

    if not (c_ok and t_ok):
        print("Warning: One or more snapshots failed (will fall back according to 01-source-quality spec).")
        sys.exit(1)
    else:
        print("Both snapshots fetched and verified successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()

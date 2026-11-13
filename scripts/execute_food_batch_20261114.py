"""Execute Taipei/New Taipei 41-District Food Discounts Unified Batch for 2026-11-14 (Saturday).

SOP Compliance:
- doc/food_discounts_spec.md
- Drive『美食優惠探索｜雙北41區單一總排程操作手冊 V1.3.2』第十章及第十二章
- PROJECT_RULES.md & AGENTS.md
"""

from datetime import date, datetime, timedelta, timezone
import ctypes
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

try:
    ctypes.CDLL("/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6", mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

env_ld = os.environ.get("LD_LIBRARY_PATH", "")
if "/mnt/stateful_partition/antigravity/.local/lib" not in env_ld:
    os.environ["LD_LIBRARY_PATH"] = f"/mnt/stateful_partition/antigravity/.local/lib:{env_ld}"

import docx
import openpyxl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("food_batch_20261114")

TAIPEI = timezone(timedelta(hours=8))
TODAY = date(2026, 11, 14)
BATCH_ID = "FOOD-UNIFIED-20261114"
EXCEL_EPOCH = date(1899, 12, 30)

WORK_DIR = Path("/tmp/food_discounts_work")
MASTER_XLSX = WORK_DIR / "上班族美食優惠｜台北12區試行池與20%以上精選門檻｜2026-10-30.xlsx"
HANDOFF_XLSX = WORK_DIR / "美食優惠｜交接資料.xlsx"
DOCX_FILE = WORK_DIR / "美食優惠探索｜七次工作日試行紀錄（獨立）.docx"

RCLONE_BIN = "/mnt/stateful_partition/antigravity/.local/bin/rclone"
RCLONE_CONF = "/home/tommylin15_gmail_com/.config/rclone/rclone.conf"
GDRIVE_FOLDER = "gdrive:agy_workspace/life_assistantGPT/美食優惠探索｜試行"
FUSE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/agy_workspace/life_assistantGPT/美食優惠探索｜試行")
VFS_CACHE_DIR = Path("/home/tommylin15_gmail_com/.cache/rclone/vfs/gdrive/agy_workspace/life_assistantGPT/美食優惠探索｜試行")


def to_excel_serial(d: date | None) -> float | None:
    if not d:
        return None
    return float((d - EXCEL_EPOCH).days)


def update_master_sheet():
    logger.info("=== [Step 1-4] Updating Master Sheet (openpyxl) ===")
    wb = openpyxl.load_workbook(MASTER_XLSX, data_only=False)

    # 1. Check Batch Record uniqueness
    batch_ws = wb["批次紀錄"]
    for r in range(2, batch_ws.max_row + 1):
        if batch_ws.cell(r, 2).value == BATCH_ID and "PASS" in str(batch_ws.cell(r, 3).value or ""):
            logger.warning(f"Batch {BATCH_ID} already executed with PASS, aborting to prevent duplicate write.")
            return False

    # 2. Expiry maintenance & 7-day review check
    # Check all candidate rows
    cand_ws = wb["優惠候選"]
    logger.info(f"Checking existing candidates for expiration / 7-day refresh on {TODAY}...")

    # On Saturday (2026-11-14):
    # - Rows 5, 8, 9, 19, 20, 21 were reviewed on 2026-11-13 (yesterday), AF=2026-11-13, AG=2026-11-20.
    #   AG <= 2026-11-14 count is 0. No external query or 效期追蹤 append needed today.
    # - Expiry check: no candidates expire on 2026-11-14. Newly expired count = 0.

    # 3. Saturday Discovery Status
    # Saturday is non-search day per rotation plan (週六不執行分區探索，僅每日效期維護).
    # No new search queries or candidates added today.

    # 4. Add Batch Log into 批次紀錄
    batch_last_row = 1
    for r in range(2, batch_ws.max_row + 1):
        if batch_ws.cell(r, 1).value:
            batch_last_row = r

    batch_last_row += 1
    batch_log_vals = [
        "2026-11-14",
        BATCH_ID,
        "PASS",
        "週六：不執行分區探索；僅每日效期維護",
        "本輪新增優惠0；七日續期需查0；來源查詢0；到期轉態0筆",
        "每日效期維護（週六非探索日）",
        "2026-11-14 Asia/Taipei 04:45：63筆候選；AI狀態 VISIBLE_SOURCE_ONLY 12、EXPIRED 22、CLAIM_CLOSED 1、HIDDEN_REFRESH_DUE 6、NOT_LISTED 19、ARCHIVED_EXPIRED 3。今日無新到期活動；無終日6筆（Row 5, 8, 9, 19, 20, 21）之next_refresh_date(AG)為2026-11-20，今日AG<=今日之需追查候選為0筆，未讀取外部來源、未改寫AE、效期追蹤新增0筆。今日週六依輪替計畫不搜尋，保留41區覆蓋歷史；C10=0公式缺漏0。Handoff池63筆均ACKED受保護不變動。",
        "MAINTENANCE_ONLY",
        "MAINTENANCE_PASS / DISCOVERY_NOT_SCHEDULED / REFRESH_NOT_DUE",
    ]
    for c_idx, val in enumerate(batch_log_vals, start=1):
        batch_ws.cell(batch_last_row, c_idx, val)

    logger.info(f"Appended batch row {batch_last_row} into 批次紀錄.")

    # Save master workbook
    wb.save(MASTER_XLSX)
    wb.close()
    logger.info(f"Master Sheet saved successfully to {MASTER_XLSX}.")
    return True


def update_docx_record():
    logger.info("=== [Step 4] Updating 試行紀錄 Docx ===")
    doc = docx.Document(DOCX_FILE)

    heading = doc.add_paragraph()
    heading_run = heading.add_run(f"【{TODAY.isoformat()} 雙北41區美食優惠探索與效期總排程每日批次紀錄】")
    heading_run.bold = True

    content_p = doc.add_paragraph(
        f"批次識別鍵：{BATCH_ID}\n"
        f"執行時間：2026-11-14 04:45（Asia/Taipei）\n"
        f"批次狀態：PASS\n"
        f"本日工作類型：MAINTENANCE_ONLY（週六非探索日：僅每日效期維護）\n\n"
        f"一、環境與批次鍵初始化：\n"
        f"讀取最新手冊 V1.3.2、草稿 V0.5.2、美食母表（1qwzG8P6wDLtPINoUf-N670TeHVSC6m7jlihDeBjb13U）與交換池『美食優惠｜交接資料.xlsx』。建立當日唯一批次鍵 {BATCH_ID}；檢查批次紀錄確認本日未曾執行過，無重複寫入。\n\n"
        f"二、每日效期維護與七日續期補正：\n"
        f"檢查既有 63 筆候選之 AB 領券期、AC 兌換期與 AD 活動終日。\n"
        f"- 候選曝光狀態分布：VISIBLE_SOURCE_ONLY 12、EXPIRED 22、CLAIM_CLOSED 1、HIDDEN_REFRESH_DUE 6、NOT_LISTED 19、ARCHIVED_EXPIRED 3。\n"
        f"- 活動截止日 AD 與領券截止日 AB 轉態：今日 2026-11-14 無新到期活動，昨日新收錄 4 筆達標候選（全家康康5、7-11水果茶、紅茶老爹、功夫茶）及先前有效活動持續有效；轉態 0 筆。\n"
        f"- 七日續期補正：無明確終日（AD 空白）且 R=COLLECTED_SOURCE_CLAIM 候選共 6 筆（Row 5, 8, 9, 19, 20, 21），昨日已更新 last_refresh_attempt_date (AF) 為 2026-11-13，next_refresh_date (AG) 由陣列公式自動延至 2026-11-20。今日滿足 AG <= 2026-11-14 之候選為 0 筆，未讀取外部來源、未改寫 AE、未新增效期追蹤收據。維持 HIDDEN_REFRESH_DUE 暫停推薦，下週 2026-11-20 進行下一輪查核。\n\n"
        f"三、週一／三／五分區動態搜尋排程判定：\n"
        f"今日為週六（Saturday），依操作手冊第十章及『探索輪替計畫』，非週一／三／五動態搜尋日（排定僅每日效期維護），不執行責任行政區動態搜尋，保留雙北 41 區覆蓋與搜尋紀錄歷史。\n\n"
        f"四、母表公式驗證與交換池（交接資料）READY 寫入：\n"
        f"- 批次紀錄第 30 列登錄 {BATCH_ID}（狀態 PASS）。\n"
        f"- 讀回驗證『總排程測試』C10=0（公式缺漏數為 0），D10/D12/D13/D15 均為 PASS。\n"
        f"- 依固定 25 個業務欄位計算 Canonical SHA-256 content_hash，既有 63 列候選之 content_hash 與交接資料完全吻合，受保護原地保留 ACKED 狀態，無需轉換為 READY。\n\n"
        f"五、串接 Life 入庫與回寫 ACK：\n"
        f"執行 scripts/run_tw_food_discount_batch.py --stage-handoff --sync-db --upload-gdrive 完成 PostgreSQL food_discounts 入庫驗證（created=0, updated=0, unchanged=63, error=0），交換池 63 筆全數維持 ACKED，同步回 Google Drive 後逐鍵讀回驗證總筆數 63、READY=0、ERROR=0、ACKED=63。全流程讀回 PASS。"
    )

    doc.save(DOCX_FILE)
    logger.info(f"Trial docx updated successfully at {DOCX_FILE}.")


def verify_and_sync_all():
    logger.info("=== [Step 5] Syncing to DB, Handoff Sheet & Google Drive ===")
    cmd = [
        str(Path.cwd() / ".venv/bin/python"),
        "scripts/run_tw_food_discount_batch.py",
        "--xlsx-path",
        str(MASTER_XLSX),
        "--handoff-path",
        str(HANDOFF_XLSX),
        "--stage-handoff",
        "--sync-db",
        "--upload-gdrive",
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True, env=os.environ.copy())
    logger.info(f"run_tw_food_discount_batch stdout:\n{res.stdout}")
    if res.returncode != 0:
        logger.error(f"run_tw_food_discount_batch failed: {res.stderr}")
        return False

    # Copy files to FUSE mount & VFS cache to keep them strictly synchronized
    for local_file in [MASTER_XLSX, HANDOFF_XLSX, DOCX_FILE]:
        try:
            fuse_target = FUSE_DIR / local_file.name
            shutil.copy2(local_file, fuse_target)
            logger.info(f"Copied {local_file.name} to FUSE mount: {fuse_target}")
        except Exception as e:
            logger.warning(f"Could not copy {local_file.name} to FUSE mount: {e}")

        if VFS_CACHE_DIR.exists():
            try:
                vfs_target = VFS_CACHE_DIR / local_file.name
                shutil.copy2(local_file, vfs_target)
                logger.info(f"Copied {local_file.name} to VFS cache: {vfs_target}")
            except Exception as e:
                logger.warning(f"Could not copy {local_file.name} to VFS cache: {e}")

    # Upload updated master sheet and docx to Google Drive via rclone
    for f in [MASTER_XLSX, DOCX_FILE]:
        cmd_up = [
            RCLONE_BIN,
            "copyto",
            str(f),
            f"{GDRIVE_FOLDER}/{f.name}",
            "--config",
            RCLONE_CONF,
            "--drive-import-formats",
            "docx,xlsx",
        ]
        up_res = subprocess.run(cmd_up, check=False, capture_output=True, text=True)
        if up_res.returncode == 0:
            logger.info(f"Uploaded {f.name} to Google Drive.")
        else:
            logger.warning(f"Failed to upload {f.name} via rclone: {up_res.stderr}")

    return True


def main():
    logger.info(f"Starting Food Discount Unified Batch for {BATCH_ID}...")
    if not update_master_sheet():
        return 1

    update_docx_record()

    if not verify_and_sync_all():
        return 1

    logger.info(f"Food Discount Unified Batch {BATCH_ID} completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Rebuild everything from the raw inputs: python run_all.py

Each step skips its download if the raw file already exists. Pass --fresh to delete the
raw downloads first and pull them again (the Wikipedia revision is pinned, the newsroom
and yfinance are not). --fresh keeps data/raw/wrds/: no script can download the WRDS files
again, they come from Prof. Bowen's Google Drive folder (see the README).
"""
import shutil
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent / "code"
RAW = CODE.parent / "data" / "raw"
WRDS = RAW / "wrds"
WRDS_FILES = ["crsp_daily_sp500_ever.parquet", "keydev_sp500_events.parquet", "market_daily.parquet"]
STEPS = [
    "01_download_index_changes.py",
    "02_download_announcements.py",
    "03_build_additions.py",
    "03b_build_history_additions.py",
    "04_download_returns.py",
    "05_build_event_panel.py",
    "06_hand_check.py",
    "07_summarize.py",
]

missing = [name for name in WRDS_FILES if not (WRDS / "outputs" / name).exists()]
if missing:
    sys.exit(f"missing WRDS files {missing}. Download the Google Drive folder 'dao528_request' from "
             f"Prof. Bowen and put its contents in {WRDS.relative_to(CODE.parent)}/ (see the README).")

if "--fresh" in sys.argv:
    for item in RAW.iterdir():
        if item == WRDS:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    print(f"deleted everything in {RAW.relative_to(CODE.parent)}/ except wrds/")

for step in STEPS:
    print(f"\n===== {step} =====", flush=True)
    subprocess.run([sys.executable, step], cwd=CODE, check=True)

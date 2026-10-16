"""Rebuild everything from the raw inputs: python run_all.py

Each step skips its download if the raw file already exists. Pass --fresh to delete the
raw downloads first and pull them again (the Wikipedia revision is pinned, the newsroom
and yfinance are not).
"""
import shutil
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent / "code"
STEPS = [
    "01_download_index_changes.py",
    "02_download_announcements.py",
    "03_build_additions.py",
    "04_download_returns.py",
    "05_build_event_panel.py",
    "06_hand_check.py",
]

if "--fresh" in sys.argv:
    raw = CODE.parent / "data" / "raw"
    shutil.rmtree(raw, ignore_errors=True)
    print(f"deleted {raw}")

for step in STEPS:
    print(f"\n===== {step} =====", flush=True)
    subprocess.run([sys.executable, step], cwd=CODE, check=True)

"""All paths resolve from the package, independent of the working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
PAPER = ROOT / "paper"
for folder in (PROCESSED, OUTPUT, PAPER):
    folder.mkdir(parents=True, exist_ok=True)

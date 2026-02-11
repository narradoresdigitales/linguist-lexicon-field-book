import json
from pathlib import Path
from typing import List, Dict, Any

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = DATA_DIR / "lexicon.json"

def load_entries() -> List[Dict[str, Any]]:
    if not JSON_PATH.exists():
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_entries(entries: List[Dict[str, Any]]) -> None:
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
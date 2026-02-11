# linguist-lexicon-field-book


A student‑friendly, standalone “Field Book” to capture, organize, and study vocabulary across lectures, videos, articles, and notes.

## Features (MVP)
- Add words with definition, notes, tags, source, and optional timestamp
- Filter/search/sort; inline edit and delete
- Local JSON persistence (upgradeable to SQLite)
- Import/Export (JSON/CSV)
- Clean, fast Streamlit UI

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
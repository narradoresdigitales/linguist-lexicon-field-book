import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from src.storage_json import load_entries, save_entries
from src.utils import normalize_timestamp

st.set_page_config(
    page_title="Linguist Lexicon",
    page_icon="📘",
    layout="wide"
)

# ---------- State & Data ----------
if "entries" not in st.session_state:
    st.session_state.entries = load_entries()

def refresh_table():
    st.session_state.df = pd.DataFrame(st.session_state.entries)

refresh_table()

# ---------- Sidebar Navigation ----------
st.sidebar.title("📘 Linguist Lexicon")
page = st.sidebar.radio(
    "Go to",
    ["Add Word", "Lexicon", "Import / Export", "Settings"],
    index=0
)

# ---------- Add Word ----------
if page == "Add Word":
    st.header("Add a New Word")
    with st.form("add_word"):
        cols = st.columns([2, 3])
        with cols[0]:
            word = st.text_input("Word", placeholder="e.g., glycolysis")
            tags = st.text_input("Tags (comma-separated)", placeholder="biology, exam")
            source = st.text_input("Source (optional)", placeholder="BIO101 Lecture 3")
        with cols[1]:
            definition = st.text_area("Definition", height=120, placeholder="Your definition or pasted from notes/textbook")
            notes = st.text_area("Notes / Context", height=120, placeholder="Where you heard it, sentence used, mnemonic, etc.")
            timestamp = st.text_input("Timestamp (optional)", placeholder="00:12:30 or seconds")

        submitted = st.form_submit_button("➕ Add to Lexicon", use_container_width=True)

    if submitted:
        if not word.strip():
            st.warning("Please enter a word.")
        else:
            entry = {
                "word": word.strip(),
                "definition": definition.strip(),
                "notes": notes.strip(),
                "tags": [t.strip() for t in tags.split(",") if t.strip()],
                "source": source.strip(),
                "timestamp": normalize_timestamp(timestamp),
                "date_added": datetime.utcnow().isoformat(timespec="seconds") + "Z"
            }
            st.session_state.entries.append(entry)
            save_entries(st.session_state.entries)
            refresh_table()
            st.success(f"Added **{entry['word']}** to your Lexicon.")

# ---------- Lexicon View ----------
elif page == "Lexicon":
    st.header("Your Lexicon")

    # Filters
    colf = st.columns([2,2,2,1])
    with colf[0]:
        query = st.text_input("Search word/definition/notes")
    with colf[1]:
        tag_filter = st.text_input("Filter by tag (exact match)")
    with colf[2]:
        source_filter = st.text_input("Filter by source contains")
    with colf[3]:
        sort_by = st.selectbox("Sort", ["word", "date_added"], index=0)

    df = st.session_state.df.copy()

    # Apply filters
    if not df.empty:
        if query:
            mask = (
                df["word"].str.contains(query, case=False, na=False) |
                df["definition"].str.contains(query, case=False, na=False) |
                df["notes"].str.contains(query, case=False, na=False)
            )
            df = df[mask]
        if tag_filter:
            df = df[df["tags"].apply(lambda ts: tag_filter.strip() in (ts or []))]
        if source_filter:
            df = df[df["source"].str.contains(source_filter, case=False, na=False)]
        df = df.sort_values(by=sort_by, ascending=True, na_position="last").reset_index(drop=True)

    # Editable table
    st.caption("Tip: Double-click cells to edit. Use the ⛔ delete button per row.")
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "word": st.column_config.TextColumn("Word"),
            "definition": st.column_config.TextColumn("Definition"),
            "notes": st.column_config.TextColumn("Notes"),
            "tags": st.column_config.ListColumn("Tags"),
            "source": st.column_config.TextColumn("Source"),
            "timestamp": st.column_config.TextColumn("Timestamp (hh:mm:ss)"),
            "date_added": st.column_config.TextColumn("Date Added (UTC)", disabled=True),
        },
        key="editor"
    )

    # Persist edits
    if st.button("💾 Save Changes", type="primary"):
        st.session_state.entries = edited.to_dict(orient="records")
        save_entries(st.session_state.entries)
        refresh_table()
        st.success("All changes saved.")

    # Delete selected row(s) by index via a multiselect
    if not edited.empty:
        to_delete = st.multiselect("Select rows to delete", edited.index.tolist())
        if st.button("⛔ Delete Selected"):
            st.session_state.entries = [
                row for idx, row in edited.iterrows() if idx not in to_delete
            ]
            save_entries(st.session_state.entries)
            refresh_table()
            st.success(f"Deleted {len(to_delete)} entr{'y' if len(to_delete)==1 else 'ies'}.")

# ---------- Import / Export ----------
elif page == "Import / Export":
    st.header("Import / Export")

    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬇️ Export JSON", use_container_width=True):
            st.download_button(
                "Download JSON",
                data=pd.Series(st.session_state.entries).to_json(orient="values"),
                file_name="lexicon.json",
                mime="application/json",
                use_container_width=True
            )
    with c2:
        if st.button("⬇️ Export CSV", use_container_width=True):
            df = pd.DataFrame(st.session_state.entries)
            st.download_button(
                "Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="lexicon.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.divider()
    st.subheader("Import")

    up_json = st.file_uploader("Import JSON (lexicon.json)", type=["json"], key="up_json")
    if up_json and st.button("📤 Import JSON"):
        try:
            df = pd.read_json(up_json)
            # Accepts either list of dicts or flat series
            if isinstance(df, pd.DataFrame):
                entries = df.to_dict(orient="records")
            else:
                entries = list(df.values)
            st.session_state.entries.extend(entries)
            save_entries(st.session_state.entries)
            refresh_table()
            st.success(f"Imported {len(entries)} entries from JSON.")
        except Exception as e:
            st.error(f"Failed to import JSON: {e}")

    up_csv = st.file_uploader("Import CSV (lexicon.csv)", type=["csv"], key="up_csv")
    if up_csv and st.button("📤 Import CSV"):
        try:
            df = pd.read_csv(up_csv)
            # Ensure expected columns exist; fill missing
            defaults = {"definition":"", "notes":"", "tags":"[]", "source":"", "timestamp":"", "date_added":""}
            for k,v in defaults.items():
                if k not in df.columns:
                    df[k] = v
            # Coerce tags from string to list if necessary
            def _safe_tags(x):
                if isinstance(x, list):
                    return x
                s = str(x).strip()
                if s.startswith("["):
                    # naive eval-safe parse
                    return [t.strip(" '\"") for t in s.strip("[]").split(",") if t.strip()]
                return [t.strip() for t in s.split(",") if t.strip()]
            df["tags"] = df["tags"].apply(_safe_tags)
            entries = df.to_dict(orient="records")
            st.session_state.entries.extend(entries)
            save_entries(st.session_state.entries)
            refresh_table()
            st.success(f"Imported {len(entries)} entries from CSV.")
        except Exception as e:
            st.error(f"Failed to import CSV: {e}")

# ---------- Settings ----------
elif page == "Settings":
    st.header("Settings")
    st.write("Future options: switch to SQLite backend, theme, larger fonts, and export defaults.")
    st.info("Data is saved locally on the server where this Streamlit app runs. If you deploy to Streamlit Cloud, consider per-user storage or a database for multi-user scenarios.")

st.divider()
    st.subheader("Import from Word (.docx)")

    st.caption("Two modes supported: (1) Glossary Table with headers (word, definition, notes, tags, source, timestamp) or (2) Free Text to harvest candidate words.")

    docx_file = st.file_uploader("Upload a .docx file", type=["docx"], key="up_docx")

    if docx_file is not None:
        from src.docx_import import load_docx, extract_tables_as_dicts, extract_plain_text, candidate_words_from_text, map_row_to_entry

        default_c1, default_c2 = st.columns([1,1])
        with default_c1:
            default_source = st.text_input("Default source (applied to imported entries)", value="")
        with default_c2:
            default_tags_str = st.text_input("Default tag(s), comma-separated", value="")
        default_tags = [t.strip() for t in default_tags_str.split(",") if t.strip()]

        doc = load_docx(docx_file)

        # --- Mode A: Try tables first ---
        tables = extract_tables_as_dicts(doc)
        imported_rows = 0

        if tables:
            st.write("### Detected Tables")
            for idx, rows in enumerate(tables, start=1):
                st.markdown(f"**Table {idx}** — {len(rows)} row(s)")
                preview = rows[:5] if len(rows) > 5 else rows
                st.json(preview)  # JSON preview helps users see headers/values

            if st.button("📥 Import from Tables"):
                new_entries = []
                for rows in tables:
                    for row in rows:
                        entry = map_row_to_entry(row, default_tags=default_tags, default_source=default_source)
                        if entry["word"]:  # must have a word
                            new_entries.append(entry)

                # De-duplicate against existing words (case-insensitive on 'word')
                existing_words = { (e.get("word") or "").lower() for e in st.session_state.entries }
                new_entries = [e for e in new_entries if (e["word"] or "").lower() not in existing_words]

                if new_entries:
                    st.session_state.entries.extend(new_entries)
                    save_entries(st.session_state.entries)
                    st.success(f"Imported {len(new_entries)} entr{'y' if len(new_entries)==1 else 'ies'} from tables.")
                    imported_rows += len(new_entries)
                else:
                    st.info("No new entries were added (duplicates or empty words).")

        # --- Mode B: Fall back to plain text ---
        text = extract_plain_text(doc)
        if text and st.checkbox("Use Free Text Mode (parse paragraphs for candidate words)", value=not bool(tables)):
            st.text_area("Extracted text (preview)", value=text[:2000] + ("..." if len(text) > 2000 else ""), height=200)

            cands = candidate_words_from_text(text)
            st.write(f"Found **{len(cands)}** unique candidate word(s).")
            # Filter out words that already exist
            existing_words = { (e.get("word") or "").lower() for e in st.session_state.entries }
            fresh = [w for w in cands if w.lower() not in existing_words]
            st.write(f"New (non-duplicate) candidates: **{len(fresh)}**")

            selected = st.multiselect("Select words to import", options=fresh, default=fresh[:30])

            notes_default = st.text_input("Default notes (optional, applied to selected words)", value="")
            if st.button("📥 Import Selected Words"):
                batch = []
                for w in selected:
                    entry = {
                        "word": w,
                        "definition": "",
                        "notes": notes_default,
                        "tags": default_tags,
                        "source": default_source,
                        "timestamp": "",
                        "date_added": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    }
                    batch.append(entry)
                if batch:
                    st.session_state.entries.extend(batch)
                    save_entries(st.session_state.entries)
                    st.success(f"Imported {len(batch)} entr{'y' if len(batch)==1 else 'ies'} from free text.")
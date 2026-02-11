import streamlit as st
import pandas as pd
from datetime import datetime
import os, sys

# Ensure src/ is importable
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.storage_json import load_entries, save_entries
from src.utils import normalize_timestamp


# ---------------------- Page Config ----------------------
st.set_page_config(
    page_title="Linguist Lexicon",
    page_icon="📘",
    layout="wide"
)


# ---------------------- Load Data ----------------------
if "entries" not in st.session_state:
    st.session_state.entries = load_entries()

def refresh_table():
    st.session_state.df = pd.DataFrame(st.session_state.entries)

refresh_table()


# ---------------------- Utility: sanitize entries ----------------------
def df_to_entries(df: pd.DataFrame) -> list[dict]:
    """Convert edited DataFrame rows into JSON‑serializable dicts."""
    if df is None or df.empty:
        return []

    # Ensure expected columns exist
    cols_defaults = {
        "word": "",
        "definition": "",
        "notes": "",
        "tags": [],
        "source": "",
        "timestamp": "",
        "date_added": "",
    }
    for col, default in cols_defaults.items():
        if col not in df.columns:
            df[col] = default

    # NA/NaN -> None
    df = df.where(pd.notnull(df), None)

    # Fix tags: ensure list[str]
    def _fix_tags(v):
        if isinstance(v, list):
            return v
        if v in (None, "", "[]"):
            return []
        s = str(v).strip()
        if s.startswith("[") and s.endswith("]"):
            # bracketed list format
            return [t.strip(" '\"") for t in s[1:-1].split(",") if t.strip()]
        return [t.strip() for t in s.split(",") if t.strip()]

    df["tags"] = df["tags"].apply(_fix_tags)

    # Coerce other fields to clean strings
    for col in ["word", "definition", "notes", "source", "timestamp", "date_added"]:
        df[col] = df[col].apply(lambda x: "" if x is None else str(x))

    # Normalize timestamp formats
    df["timestamp"] = df["timestamp"].apply(normalize_timestamp)

    return df.to_dict(orient="records")


# ---------------------- Sidebar ----------------------
st.sidebar.title("📘 Linguist Lexicon")
page = st.sidebar.radio(
    "Go to",
    ["Add Word", "Lexicon", "Import / Export", "Settings"],
    index=0
)


# ================================================================
# ========================= ADD WORD =============================
# ================================================================
if page == "Add Word":
    st.header("Add a New Word")

    with st.form("add_word"):
        col1, col2 = st.columns([2, 3])

        with col1:
            word = st.text_input("Word", placeholder="e.g., glycolysis")
            tags = st.text_input("Tags (comma-separated)", placeholder="biology, exam")
            source = st.text_input("Source (optional)", placeholder="BIO101 Lecture 3")

        with col2:
            definition = st.text_area("Definition", height=120)
            notes = st.text_area("Notes / Context", height=120)
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


# ================================================================
# ========================== LEXICON =============================
# ================================================================
elif page == "Lexicon":
    st.header("Your Lexicon")

    # ---------- Filters ----------
    colf = st.columns([2, 2, 2, 1])
    with colf[0]:
        query = st.text_input("Search word/definition/notes")
    with colf[1]:
        tag_filter = st.text_input("Filter by tag (exact match)")
    with colf[2]:
        source_filter = st.text_input("Filter by source contains")
    with colf[3]:
        sort_by = st.selectbox("Sort", ["word", "date_added"])

    df = st.session_state.df.copy()

    # ---------- Apply filters ----------
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

        df = df.sort_values(by=sort_by).reset_index(drop=True)

    # ---------- Editable Table ----------
    st.caption("Tip: Double-click cells to edit. Use the delete section below to remove rows.")

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

    if st.button("💾 Save Changes", type="primary"):
        st.session_state.entries = df_to_entries(edited)
        save_entries(st.session_state.entries)
        refresh_table()
        st.success("All changes saved.")

    # ---------- Row deletion ----------
# ---------- Row deletion ----------
st.subheader("Delete entries")

if not st.session_state.df.empty:
    st.caption("Current lexicon (for reference):")
    st.dataframe(st.session_state.df[["word", "definition", "tags", "date_added"]])

    options = [
        f"{row.get('date_added', 'MISSING_DATE')} | {row['word'][:40]}"
        for _, row in st.session_state.df.iterrows()
    ]

    if "delete_selection" not in st.session_state:
        st.session_state.delete_selection = []

    selected_labels = st.multiselect(
        "Select entries to delete (shows date | word preview)",
        options=options,
        default=st.session_state.delete_selection,
        key="delete_multiselect"
    )

    # ── All debug output MUST come AFTER the multiselect ─────────────────────
    st.markdown("**Diagnostic (remove later):**")
    st.write("Total entries right now:", len(st.session_state.entries))
    st.write("Selected items:", selected_labels)

    # Show what dates would actually be targeted
    targeted_dates = []
    for label in selected_labels:
        try:
            date_part = label.split(" | ", 1)[0].strip()
            targeted_dates.append(date_part if date_part else "EMPTY_STRING")
        except:
            targeted_dates.append("PARSE_FAILED")
    st.write("Targeted date_added values:", targeted_dates)

    # Show real data state
    sample_dates = [e.get("date_added", "—missing—") for e in st.session_state.entries[:5]]
    st.write("First 5 date_added in storage:", sample_dates)
    st.write("Any real date_added present?", any(e.get("date_added") for e in st.session_state.entries))
    # ────────────────────────────────────────────────────────────────────────

    if st.button("⛔ Delete Selected", type="primary", key="confirm_delete"):
    if not selected_labels:
        st.warning("No entries selected.")
    else:
        st.info("Safe mode: showing what would be deleted (nothing actually deleted yet)")

        targeted = []
        for label in selected_labels:
            try:
                date_str = label.split(" | ", 1)[0].strip()
                targeted.append(date_str if date_str else "[empty]")
            except:
                targeted.append("[parse failed]")

        st.write("Would target these date_added values:", targeted)

        # Show how many entries actually have each targeted date
        from collections import Counter
        all_dates = [e.get("date_added", "[missing]") for e in st.session_state.entries]
        count_by_date = Counter(all_dates)

        for t in targeted:
            matches = count_by_date.get(t, 0)
            st.write(f"→ '{t}' matches **{matches}** entries in your lexicon")

        # Deliberately do NOT modify entries here yet
        st.warning("No deletion performed — check the counts above. Tell me what you see.")



# ================================================================
# ====================== IMPORT / EXPORT =========================
# ================================================================
elif page == "Import / Export":
    st.header("Import / Export")

    # ------------------ Export ------------------
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

    # ------------------ Import JSON / CSV ------------------
    st.divider()
    st.subheader("Import")

    # ---- Import JSON ----
    up_json = st.file_uploader("Import JSON (lexicon.json)", type=["json"])
    if up_json and st.button("📤 Import JSON"):
        try:
            df = pd.read_json(up_json)
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

    # ---- Import CSV ----
    up_csv = st.file_uploader("Import CSV (lexicon.csv)", type=["csv"])
    if up_csv and st.button("📤 Import CSV"):
        try:
            df = pd.read_csv(up_csv)
            entries = df_to_entries(df)
            st.session_state.entries.extend(entries)
            save_entries(st.session_state.entries)
            refresh_table()
            st.success(f"Imported {len(entries)} entries from CSV.")
        except Exception as e:
            st.error(f"Failed to import CSV: {e}")

    # ------------------ Import from Word (.docx) ------------------
    st.divider()
    st.subheader("Import from Word (.docx)")
    st.caption("Works with (1) glossary tables or (2) free text paragraphs.")

    docx_file = st.file_uploader("Upload a .docx file", type=["docx"])

    if docx_file:
        from src.docx_import import (
            load_docx,
            extract_tables_as_dicts,
            extract_plain_text,
            candidate_words_from_text,
            map_row_to_entry,
        )

        colA, colB = st.columns(2)
        with colA:
            default_source = st.text_input("Default source", value="")
        with colB:
            default_tags_str = st.text_input("Default tags (comma-separated)", value="")

        default_tags = [t.strip() for t in default_tags_str.split(",") if t.strip()]

        doc = load_docx(docx_file)

        # ---- Mode A: tables ----
        tables = extract_tables_as_dicts(doc)
        if tables:
            st.write("### Tables detected")
            for idx, rows in enumerate(tables, start=1):
                st.markdown(f"**Table {idx}** ({len(rows)} rows)")
                st.json(rows[:5])

            if st.button("📥 Import from Tables"):
                new_entries = []
                for rows in tables:
                    for r in rows:
                        entry = map_row_to_entry(
                            r, default_tags=default_tags, default_source=default_source
                        )
                        if entry["word"]:
                            new_entries.append(entry)

                # Eliminate duplicates (case-insensitive)
                existing = {(e["word"] or "").lower() for e in st.session_state.entries}
                new_entries = [
                    e for e in new_entries if e["word"].lower() not in existing
                ]

                st.session_state.entries.extend(new_entries)
                save_entries(st.session_state.entries)
                refresh_table()
                st.success(f"Imported {len(new_entries)} entries from tables.")

        # ---- Mode B: free text ----
        text = extract_plain_text(doc)
        if st.checkbox("Use Free Text Mode", value=not bool(tables)):
            st.text_area("Extracted text (preview)", text[:2000] + ("..." if len(text) > 2000 else ""), height=200)

            words = candidate_words_from_text(text)
            existing = {(e["word"] or "").lower() for e in st.session_state.entries}
            fresh = [w for w in words if w.lower() not in existing]

            selected = st.multiselect("Select words to import", fresh, default=fresh[:20])

            notes_default = st.text_input("Default notes (optional)", value="")

            if st.button("📥 Import Selected Words"):
                batch = [
                    {
                        "word": w,
                        "definition": "",
                        "notes": notes_default,
                        "tags": default_tags,
                        "source": default_source,
                        "timestamp": "",
                        "date_added": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    }
                    for w in selected
                ]

                st.session_state.entries.extend(batch)
                save_entries(st.session_state.entries)
                refresh_table()
                st.success(f"Imported {len(batch)} entries from free text.")


# ================================================================
# =========================== SETTINGS ===========================
# ================================================================
elif page == "Settings":
    st.header("Settings")
    st.info("Your Lexicon data is saved on the server filesystem.\n"
            "For Streamlit Cloud, consider SQLite or per-user storage if needed.")
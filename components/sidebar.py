"""
Reusable Sidebar Component for Agentic Data Analyst.

Handles multi-source dataset ingestion (Upload, Built-in Samples, Recent History),
safe file parsing, session state synchronization, and active dataset metadata badge.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import html
import pandas as pd
import streamlit as st

from utils.auth import get_current_user
from utils.file_handler import dataset_format
from utils.helpers import format_bytes
from utils.history import (
    get_file_path,
    get_history,
    get_sample_datasets,
    get_sample_file_path,
    save_history,
)
from utils.session_state import (
    clear_dataset,
    get_dataset,
    has_dataset,
    init_session_state,
    set_dataset,
)
from components.auth_ui import render_user_profile_badge


def get_supported_file_extensions() -> List[str]:
    """
    Returns list of supported file format extensions for dataset ingestion.
    """
    return ["csv", "xlsx", "xls", "json", "feather", "sqlite", "db", "sqlite3"]


def get_dataset_metadata(
    df: Optional[pd.DataFrame] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extracts summary metadata for display in the sidebar badge.

    Args:
        df: Active DataFrame or None.
        filename: Name of the active file or None.

    Returns:
        Dict with filename, rows, columns, memory, column lists, and flags.
    """
    if df is None or df.empty:
        return {
            "filename": filename or "No dataset loaded",
            "rows": 0,
            "columns": 0,
            "memory": "0 B",
            "memory_bytes": 0,
            "column_names": [],
            "numeric_columns": [],
            "categorical_columns": [],
            "is_empty": True,
            "has_data": False,
        }

    try:
        mem_bytes = int(df.memory_usage(deep=True).sum())
    except Exception:
        mem_bytes = 0

    num_cols = df.select_dtypes(include="number").columns.tolist()
    try:
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    except Exception:
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    return {
        "filename": filename or "Untitled Dataset",
        "rows": len(df),
        "columns": df.shape[1],
        "memory": format_bytes(mem_bytes),
        "memory_bytes": mem_bytes,
        "column_names": list(df.columns),
        "numeric_columns": num_cols,
        "categorical_columns": cat_cols,
        "is_empty": False,
        "has_data": True,
    }


def format_sidebar_badge_html(metadata: Dict[str, Any]) -> str:
    """
    Generates styled HTML for the active dataset metadata card.

    Args:
        metadata: Metadata dictionary produced by get_dataset_metadata().

    Returns:
        HTML string formatted with inline CSS styles.
    """
    safe_filename = html.escape(str(metadata.get("filename", "Untitled Dataset")))
    rows = metadata.get("rows", 0)
    cols = metadata.get("columns", 0)
    memory = metadata.get("memory", "0 B")
    num_count = len(metadata.get("numeric_columns", []))
    cat_count = len(metadata.get("categorical_columns", []))
    has_data = metadata.get("has_data", False)

    if not has_data:
        return (
            """<div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; """
            """border-radius: 8px; padding: 12px; margin-bottom: 12px; text-align: center;">"""
            """<div style="font-size: 0.85rem; color: #64748b; font-weight: 500;">"""
            """📂 No dataset currently active</div>"""
            """<div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">"""
            """Upload a file or choose a sample below</div></div>"""
        )

    return f"""
    <div style="
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 700;">
                Active Dataset
            </div>
            <span style="
                background-color: #dcfce7;
                color: #15803d;
                font-size: 0.70rem;
                font-weight: 600;
                padding: 2px 7px;
                border-radius: 9999px;
                border: 1px solid #bbf7d0;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            ">● Loaded</span>
        </div>
        <div style="
            font-size: 0.95rem;
            font-weight: 700;
            color: #0f172a;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 10px;
        " title="{safe_filename}">
            📄 {safe_filename}
        </div>
        <div style="
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            background-color: #ffffff;
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            font-size: 0.78rem;
        ">
            <div>
                <span style="color: #64748b;">Rows:</span>
                <strong style="color: #1e293b; margin-left: 4px;">{rows:,}</strong>
            </div>
            <div>
                <span style="color: #64748b;">Cols:</span>
                <strong style="color: #1e293b; margin-left: 4px;">{cols}</strong>
            </div>
            <div>
                <span style="color: #64748b;">Memory:</span>
                <strong style="color: #1e293b; margin-left: 4px;">{memory}</strong>
            </div>
            <div>
                <span style="color: #64748b;">Types:</span>
                <span style="color: #1e293b; font-weight: 600; margin-left: 4px;" title="{num_count} numeric, {cat_count} categorical">
                    {num_count}# / {cat_count}A
                </span>
            </div>
        </div>
    </div>
    """


def load_dataset_file(
    file_or_path: Union[str, Path, Any],
    filename: str,
    table_name: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
    """
    Safely parses a dataset file or stream via dataset_format.

    Args:
        file_or_path: File path or uploaded file stream.
        filename: Name of the dataset file.
        table_name: Optional SQLite table name.

    Returns:
        Tuple of (df, filename, error_message).
    """
    try:
        df = dataset_format(file_or_path, filename=filename, table_name=table_name)
        if df is None or not isinstance(df, pd.DataFrame):
            return None, filename, "Parsed output is not a valid pandas DataFrame."
        return df, filename, None
    except Exception as e:
        return None, filename, str(e)


def render_active_dataset_card(
    df: Optional[pd.DataFrame] = None,
    filename: Optional[str] = None,
    key_prefix: str = "sidebar",
) -> bool:
    """
    Renders the active dataset metadata badge card and an unload button.

    Args:
        df: Active DataFrame (if None, fetched from session state).
        filename: Active filename (if None, fetched from session state).
        key_prefix: Unique widget key prefix.

    Returns:
        True if an active dataset is loaded, False otherwise.
    """
    if df is None or filename is None:
        session_df, session_fn = get_dataset()
        df = df if df is not None else session_df
        filename = filename if filename is not None else session_fn

    metadata = get_dataset_metadata(df, filename)
    badge_html = format_sidebar_badge_html(metadata)
    st.markdown(badge_html, unsafe_allow_html=True)

    if metadata["has_data"]:
        if st.button(
            "🗑️ Unload Dataset",
            key=f"{key_prefix}_unload_btn",
            help="Clear current dataset from memory and reset active session",
            width="stretch",
        ):
            clear_dataset()
            st.rerun()
        return True

    return False


def render_data_source_picker(
    key_prefix: str = "sidebar",
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Renders source picker controls (Upload File, Sample Datasets, Recent History)
    and updates session state when a new source is chosen.

    Args:
        key_prefix: Unique widget key prefix.

    Returns:
        Tuple of (df, filename).
    """
    init_session_state()
    current_df, current_filename = get_dataset()
    current_user = get_current_user()

    source_mode = st.radio(
        "Select Ingestion Method:",
        options=["📤 Upload File", "📚 Sample Datasets", "🕒 Recent Files"],
        key=f"{key_prefix}_mode_radio",
        horizontal=False,
    )

    # --------------------------------------------------------------------------
    # 1. Upload File Mode
    # --------------------------------------------------------------------------
    if source_mode == "📤 Upload File":
        uploaded_file = st.file_uploader(
            "Choose a dataset",
            type=get_supported_file_extensions(),
            key=f"{key_prefix}_uploader",
            help="Supported: CSV, Excel (.xlsx, .xls), JSON, Feather, SQLite (.db, .sqlite)",
        )

        if uploaded_file is not None:
            # Avoid reloading if same file is already active in session state
            last_loaded_key = f"{key_prefix}_last_loaded_upload"
            already_loaded = (
                current_filename == uploaded_file.name
                and st.session_state.get(last_loaded_key) == uploaded_file.name
            )

            if not already_loaded:
                with st.spinner(f"Loading '{uploaded_file.name}'..."):
                    try:
                        if current_user:
                            save_history(uploaded_file, username=current_user)
                        else:
                            save_history(uploaded_file)

                        df, name, err = load_dataset_file(uploaded_file, uploaded_file.name)
                        if err:
                            st.error(f"❌ Failed to parse '{uploaded_file.name}': {err}")
                        else:
                            set_dataset(df, name)
                            st.session_state[last_loaded_key] = name
                            st.toast(f"✅ Loaded {name} ({len(df):,} rows)")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error uploading dataset: {e}")

    # --------------------------------------------------------------------------
    # 2. Sample Datasets Mode
    # --------------------------------------------------------------------------
    elif source_mode == "📚 Sample Datasets":
        samples = get_sample_datasets()
        placeholder = "-- Select Sample Dataset --"
        options = [placeholder] + samples

        default_idx = 0
        if current_filename and current_filename in samples:
            default_idx = options.index(current_filename)

        selected_sample = st.selectbox(
            "Sample Datasets:",
            options=options,
            index=default_idx,
            key=f"{key_prefix}_sample_select",
            help="Pre-packaged demo datasets from data/sample/",
        )

        if selected_sample != placeholder and selected_sample != current_filename:
            with st.spinner(f"Loading sample '{selected_sample}'..."):
                try:
                    file_path = get_sample_file_path(selected_sample)
                    df, name, err = load_dataset_file(file_path, selected_sample)
                    if err:
                        st.error(f"❌ Failed to load sample: {err}")
                    else:
                        set_dataset(df, name)
                        st.toast(f"✅ Loaded sample: {name}")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error loading sample '{selected_sample}': {e}")

    # --------------------------------------------------------------------------
    # 3. Recent History Mode
    # --------------------------------------------------------------------------
    elif source_mode == "🕒 Recent Files":
        history = get_history(username=current_user) if current_user else get_history()
        placeholder = "-- Select from History --"
        options = [placeholder] + history

        default_idx = 0
        if current_filename and current_filename in history:
            default_idx = options.index(current_filename)

        selected_recent = st.selectbox(
            "Recent Files:",
            options=options,
            index=default_idx,
            key=f"{key_prefix}_recent_select",
            help="Previously uploaded and demo files",
        )

        if selected_recent != placeholder and selected_recent != current_filename:
            with st.spinner(f"Loading '{selected_recent}'..."):
                try:
                    file_path = (
                        get_file_path(selected_recent, username=current_user)
                        if current_user
                        else get_file_path(selected_recent)
                    )
                    df, name, err = load_dataset_file(file_path, selected_recent)
                    if err:
                        st.error(f"❌ Failed to load file: {err}")
                    else:
                        set_dataset(df, name)
                        st.toast(f"✅ Loaded {name}")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error loading recent file '{selected_recent}': {e}")

    return get_dataset()



def render_sidebar(
    title: str = "📂 Data Source",
    key_prefix: str = "sidebar",
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Main reusable sidebar entry point.
    Renders header, active dataset badge/card, and ingestion picker into st.sidebar.

    Args:
        title: Header title string.
        key_prefix: Unique widget key prefix.

    Returns:
        Tuple of (active_df, active_filename).
    """
    init_session_state()

    with st.sidebar:
        render_user_profile_badge(key_prefix=f"{key_prefix}_profile")
        st.header(title)
        render_active_dataset_card(key_prefix=key_prefix)
        st.divider()
        st.subheader("Import Data")
        render_data_source_picker(key_prefix=key_prefix)

    return get_dataset()

import streamlit as st
import pandas as pd


def init_session_state() -> None:
    """Initialize all required session state variables if not already set."""
    if "df" not in st.session_state:
        st.session_state["df"] = None

    if "filename" not in st.session_state:
        st.session_state["filename"] = None

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None

    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = False


def set_dataset(df: pd.DataFrame, filename: str) -> None:
    """Update session state with a newly selected or uploaded dataset."""
    st.session_state["df"] = df
    st.session_state["filename"] = filename
    # Reset chat conversation when switching to a new dataset
    st.session_state["messages"] = []


def has_dataset() -> bool:
    """Check if a dataset is currently loaded in the session state."""
    return st.session_state.get("df") is not None


def get_dataset() -> tuple[pd.DataFrame | None, str | None]:
    """Retrieve the current DataFrame and filename from session state."""
    return st.session_state.get("df"), st.session_state.get("filename")


def clear_dataset() -> None:
    """Clear the current dataset from session state."""
    st.session_state["df"] = None
    st.session_state["filename"] = None
    st.session_state["messages"] = []
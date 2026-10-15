import streamlit as st
from components.auth_ui import render_auth_gate
from components.sidebar import render_sidebar
from ui.Data_Analysis import analysis_tab
from ui.Data_Visualization import visualization_tab
from utils.session_state import get_dataset, init_session_state

st.set_page_config(
    page_title="My Analyst",
    page_icon="🤖",
    layout="wide",
)

# Initialize session state for persistent dataset, auth, and message history
init_session_state()

# Enforce authentication gate - halts rendering until user logs in
current_user = render_auth_gate()

st.title("🤖 My Analyst")

# Shared modular sidebar for multi-source ingestion & dataset badge
df, filename = render_sidebar()

if df is not None:
    st.caption(f"User: **{current_user}** | Active Dataset: **{filename}** | {df.shape[0]:,} rows × {df.shape[1]} columns")
    tab_eda, tab_viz, tab_chat = st.tabs([
        "📊 Exploratory Data Analysis",
        "📈 Visualization of your Data",
        "🤖 Ask Your Data",
    ])

    with tab_eda:
        analysis_tab(df)

    with tab_viz:
        visualization_tab(df)

    with tab_chat:
        st.info("🤖 Autonomous AI Data Analyst tab will be wired in Phase 6.")
else:
    st.info("👋 Welcome to **Agentic Data Analyst**! Please upload a file or select a sample dataset from the sidebar to begin.")
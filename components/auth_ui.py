"""
Authentication and User Profile UI Components.

Provides a modern login & registration gate to enforce multi-user privacy,
and a sidebar user profile card with one-click logout.
"""

import html
from typing import Optional
import streamlit as st

from utils.auth import (
    get_current_user,
    is_user_authenticated,
    login_user,
    logout_user,
    signup_user,
)


def render_user_profile_badge(key_prefix: str = "auth_profile") -> Optional[str]:
    """
    Renders the active user profile badge and logout button in the Streamlit sidebar.

    Args:
        key_prefix: Unique widget key prefix.

    Returns:
        The current username if authenticated, None otherwise.
    """
    current_user = get_current_user()
    if not current_user:
        return None

    safe_username = html.escape(str(current_user))

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.1rem;">👤</span>
                <div>
                    <div style="font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.05em; color: #1e40af; font-weight: 700;">
                        Authenticated User
                    </div>
                    <div style="font-size: 0.90rem; font-weight: 700; color: #1e3a8a;">
                        {safe_username}
                    </div>
                </div>
            </div>
            <span style="
                background-color: #dbeafe;
                color: #1e40af;
                font-size: 0.70rem;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 9999px;
                border: 1px solid #93c5fd;
            ">Active</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🚪 Log Out",
        key=f"{key_prefix}_logout_btn",
        help="Sign out and purge active session data",
        width="stretch",
    ):
        logout_user()
        st.toast("👋 You have logged out successfully.")
        st.rerun()

    return current_user


def render_auth_gate(
    title: str = "Agentic Data Analyst",
    subtitle: str = "Sign in to access your isolated workspace & private datasets",
    key_prefix: str = "auth_gate",
) -> str:
    """
    Blocks dashboard execution and displays the authentication gate until a user signs in.

    Args:
        title: Main gate title.
        subtitle: Gate description.
        key_prefix: Unique widget key prefix.

    Returns:
        The authenticated username.
    """
    # If already logged in, return current username immediately
    if is_user_authenticated():
        active_user = get_current_user()
        if active_user:
            return active_user

    # Render Authentication Gate UI
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 24px 16px 12px 16px;
            margin-bottom: 16px;
        ">
            <div style="font-size: 2.4rem; margin-bottom: 6px;">🔐</div>
            <h2 style="margin: 0; color: #0f172a; font-weight: 800;">{title}</h2>
            <p style="margin: 6px 0 0 0; color: #64748b; font-size: 0.95rem;">
                {subtitle}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Center card layout using columns
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        tab_signin, tab_signup = st.tabs(["🔑 Sign In", "📝 Create Account"])

        # ----------------------------------------------------------------------
        # Tab 1: Sign In
        # ----------------------------------------------------------------------
        with tab_signin:
            with st.form(key=f"{key_prefix}_signin_form"):
                st.subheader("Welcome Back")
                login_username = st.text_input(
                    "Username",
                    placeholder="Enter your username",
                    key=f"{key_prefix}_login_username",
                )
                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key=f"{key_prefix}_login_password",
                )

                signin_submitted = st.form_submit_button(
                    "Sign In",
                    type="primary",
                    use_container_width=True,
                )

                if signin_submitted:
                    success, msg = login_user(login_username, login_password)
                    if success:
                        st.toast(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # ----------------------------------------------------------------------
        # Tab 2: Create Account
        # ----------------------------------------------------------------------
        with tab_signup:
            with st.form(key=f"{key_prefix}_signup_form"):
                st.subheader("New Account")
                new_username = st.text_input(
                    "Username",
                    placeholder="Choose a username (3-32 characters)",
                    help="Allowed: letters, numbers, underscores, dots, hyphens.",
                    key=f"{key_prefix}_new_username",
                )
                new_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Choose a secure password (min 6 chars)",
                    key=f"{key_prefix}_new_password",
                )
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter your password",
                    key=f"{key_prefix}_confirm_password",
                )

                signup_submitted = st.form_submit_button(
                    "Create Account & Sign In",
                    type="primary",
                    use_container_width=True,
                )

                if signup_submitted:
                    if new_password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    else:
                        created, create_msg = signup_user(new_username, new_password)
                        if created:
                            # Automatically log in the user on successful signup
                            login_user(new_username, new_password)
                            st.toast(f"🎉 {create_msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {create_msg}")

        st.caption(
            "🔒 **Data Privacy:** Each user account maintains an isolated folder (`data/users/<username>/uploads/`). "
            "Your uploaded datasets are strictly private and never shared across user sessions."
        )

    # Block subsequent dashboard page rendering until user is authenticated
    st.stop()

"""
Unit tests for components/auth_ui.py.
Verifies login gate rendering, tab interactions, profile badge display, and logout triggers.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from components.auth_ui import render_auth_gate, render_user_profile_badge
from utils.session_state import init_session_state


class TestAuthUI(unittest.TestCase):
    """Test suite for authentication UI components."""

    def setUp(self):
        if hasattr(st, "session_state"):
            st.session_state.clear()
        init_session_state()

    @patch("components.auth_ui.get_current_user", return_value=None)
    @patch("streamlit.markdown")
    def test_render_user_profile_badge_unauthenticated(self, mock_markdown, mock_get_user):
        """Verifies profile badge renders nothing when user is not authenticated."""
        res = render_user_profile_badge()
        self.assertIsNone(res)
        mock_markdown.assert_not_called()

    @patch("components.auth_ui.get_current_user", return_value="alice")
    @patch("streamlit.button", return_value=False)
    @patch("streamlit.markdown")
    def test_render_user_profile_badge_authenticated(self, mock_markdown, mock_button, mock_get_user):
        """Verifies profile badge renders user info and logout button when authenticated."""
        res = render_user_profile_badge()
        self.assertEqual(res, "alice")
        mock_markdown.assert_called_once()
        badge_html = mock_markdown.call_args[0][0]
        self.assertIn("alice", badge_html)
        mock_button.assert_called_once()

    @patch("components.auth_ui.logout_user")
    @patch("streamlit.rerun")
    @patch("streamlit.toast")
    @patch("components.auth_ui.get_current_user", return_value="alice")
    @patch("streamlit.button", return_value=True)
    @patch("streamlit.markdown")
    def test_render_user_profile_badge_logout_clicked(
        self, mock_markdown, mock_button, mock_get_user, mock_toast, mock_rerun, mock_logout
    ):
        """Verifies clicking logout button calls logout_user and triggers rerun."""
        render_user_profile_badge()
        mock_logout.assert_called_once()
        mock_toast.assert_called_once()
        mock_rerun.assert_called_once()

    @patch("components.auth_ui.is_user_authenticated", return_value=True)
    @patch("components.auth_ui.get_current_user", return_value="bob")
    @patch("streamlit.stop")
    def test_render_auth_gate_already_authenticated(self, mock_stop, mock_get_user, mock_is_auth):
        """Verifies auth gate returns current user without halting if already logged in."""
        user = render_auth_gate()
        self.assertEqual(user, "bob")
        mock_stop.assert_not_called()

    @patch("components.auth_ui.is_user_authenticated", return_value=False)
    @patch("streamlit.stop")
    @patch("streamlit.form_submit_button", return_value=False)
    @patch("streamlit.text_input", return_value="")
    @patch("streamlit.tabs", return_value=[MagicMock(), MagicMock()])
    @patch("streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock()])
    @patch("streamlit.markdown")
    def test_render_auth_gate_unauthenticated_halts_via_stop(
        self, mock_markdown, mock_cols, mock_tabs, mock_text, mock_submit, mock_stop, mock_is_auth
    ):
        """Verifies unauthenticated gate renders login/signup forms and calls st.stop()."""
        render_auth_gate()
        mock_stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()

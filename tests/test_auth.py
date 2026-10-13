"""
Unit tests for utils/auth.py.
Verifies password hashing, credential validation, user registration,
login verification, sandboxed folder creation, and session logout handling.
"""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from utils.auth import (
    get_all_usernames,
    get_current_user,
    get_user_upload_dir,
    hash_password,
    is_user_authenticated,
    load_auth_db,
    login_user,
    logout_user,
    save_auth_db,
    signup_user,
    validate_password,
    validate_username,
    verify_password,
)
from utils.session_state import init_session_state, set_dataset


class TestAuthEngine(unittest.TestCase):
    """Test suite for core authentication functions and cryptography."""

    def setUp(self):
        # Create isolated temporary directory for testing auth database and user folders
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.auth_file = self.temp_path / "auth.json"
        self.users_dir = self.temp_path / "users"

        if hasattr(st, "session_state"):
            st.session_state.clear()
        init_session_state()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hash_and_verify_password(self):
        """Verifies that password hashing produces consistent and verifiable digests."""
        salt = "abcdef1234567890"
        pwd = "SecretPassword123"
        hashed = hash_password(pwd, salt)
        self.assertIsInstance(hashed, str)
        self.assertEqual(len(hashed), 64)  # SHA-256 output is 64 hex characters

        # Verification tests
        self.assertTrue(verify_password(pwd, salt, hashed))
        self.assertFalse(verify_password("WrongPassword", salt, hashed))
        self.assertFalse(verify_password(pwd, "wrong_salt", hashed))

    def test_validate_username(self):
        """Verifies username naming constraints and traversal protection."""
        valid_users = ["alice", "bob_123", "charlie-dev", "data.analyst"]
        for u in valid_users:
            valid, msg = validate_username(u)
            self.assertTrue(valid, f"Expected '{u}' to be valid: {msg}")

        invalid_users = [
            "",  # empty
            "ab",  # too short
            "a" * 35,  # too long
            "../bad_actor",  # path traversal
            "user/name",  # slash
            "user\\name",  # backslash
            "user@domain",  # unsupported symbol
            "user name",  # spaces
        ]
        for u in invalid_users:
            valid, msg = validate_username(u)
            self.assertFalse(valid, f"Expected '{u}' to be rejected")

    def test_validate_password(self):
        """Verifies password validation bounds."""
        valid, _ = validate_password("abcdef")
        self.assertTrue(valid)

        invalid_short, msg = validate_password("12345")
        self.assertFalse(invalid_short)
        self.assertIn("at least 6", msg)

        invalid_empty, _ = validate_password("")
        self.assertFalse(invalid_empty)

    def test_signup_user_creates_account_and_sandbox_dir(self):
        """Verifies successful registration creates credentials and user's uploads directory."""
        ok, msg = signup_user(
            "alice",
            "password123",
            auth_file=self.auth_file,
            users_dir=self.users_dir,
        )
        self.assertTrue(ok)
        self.assertIn("created successfully", msg)

        # Check auth.json contents
        db = load_auth_db(self.auth_file)
        self.assertIn("alice", db)
        self.assertIn("salt", db["alice"])
        self.assertIn("password_hash", db["alice"])

        # Check sandboxed directory creation
        user_uploads = self.users_dir / "alice" / "uploads"
        self.assertTrue(user_uploads.exists() and user_uploads.is_dir())

    def test_signup_duplicate_username_rejected(self):
        """Verifies duplicate registrations (including case-insensitive) are rejected."""
        signup_user("alice", "pwd123", auth_file=self.auth_file, users_dir=self.users_dir)

        # Exact match
        ok, msg = signup_user("alice", "another_pwd", auth_file=self.auth_file, users_dir=self.users_dir)
        self.assertFalse(ok)
        self.assertIn("already registered", msg)

        # Case-insensitive match
        ok_upper, msg_upper = signup_user("ALICE", "pwd456", auth_file=self.auth_file, users_dir=self.users_dir)
        self.assertFalse(ok_upper)
        self.assertIn("already registered", msg_upper)

    def test_login_user_success_sets_session_state(self):
        """Verifies logging in sets authenticated_user and is_authenticated in session state."""
        signup_user("bob", "mypassword", auth_file=self.auth_file, users_dir=self.users_dir)

        ok, msg = login_user("bob", "mypassword", auth_file=self.auth_file, users_dir=self.users_dir)
        self.assertTrue(ok)
        self.assertIn("Welcome back", msg)

        self.assertTrue(is_user_authenticated())
        self.assertEqual(get_current_user(), "bob")

    def test_login_user_invalid_credentials(self):
        """Verifies login fails on wrong password or unregistered username."""
        signup_user("bob", "mypassword", auth_file=self.auth_file, users_dir=self.users_dir)

        ok_bad_pwd, msg_bad_pwd = login_user("bob", "wrong_pwd", auth_file=self.auth_file)
        self.assertFalse(ok_bad_pwd)
        self.assertIn("Invalid username or password", msg_bad_pwd)

        ok_bad_user, msg_bad_user = login_user("nonexistent", "pwd123", auth_file=self.auth_file)
        self.assertFalse(ok_bad_user)
        self.assertIn("Invalid username or password", msg_bad_user)

    def test_logout_user_purges_session(self):
        """Verifies logout purges credentials, active dataset, and conversation state."""
        # Setup active session with dataset and user
        st.session_state["authenticated_user"] = "charlie"
        st.session_state["is_authenticated"] = True
        st.session_state["df"] = "dummy_df"
        st.session_state["filename"] = "dummy.csv"
        st.session_state["messages"] = [{"role": "user", "content": "hello"}]
        st.session_state["sidebar_uploader"] = "file"

        logout_user()

        self.assertFalse(is_user_authenticated())
        self.assertIsNone(get_current_user())
        self.assertIsNone(st.session_state.get("df"))
        self.assertIsNone(st.session_state.get("filename"))
        self.assertEqual(st.session_state.get("messages"), [])
        self.assertNotIn("sidebar_uploader", st.session_state)

    def test_get_all_usernames(self):
        """Verifies get_all_usernames returns sorted list of registered usernames."""
        signup_user("zara", "pass123", auth_file=self.auth_file, users_dir=self.users_dir)
        signup_user("adam", "pass123", auth_file=self.auth_file, users_dir=self.users_dir)

        users = get_all_usernames(self.auth_file)
        self.assertEqual(users, ["adam", "zara"])


if __name__ == "__main__":
    unittest.main()

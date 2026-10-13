"""
Unit tests for sandboxed per-user storage in utils/history.py.
Verifies multi-user isolation, cross-user privacy protection, path traversal security,
and shared sample dataset access.
"""

import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import utils.history as history_module
from utils.history import (
    get_file_path,
    get_history,
    get_sample_datasets,
    get_sample_file_path,
    get_user_uploads,
    resolve_user_upload_dir,
    sanitize_filename,
    save_history,
)


class TestHistorySandbox(unittest.TestCase):
    """Test suite for sandboxed dataset storage and multi-user privacy."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.mock_users_dir = self.temp_path / "users"
        self.mock_sample_dir = self.temp_path / "sample"
        self.mock_users_dir.mkdir(parents=True)
        self.mock_sample_dir.mkdir(parents=True)

        # Create a mock public sample dataset
        (self.mock_sample_dir / "public_sample.csv").write_text("a,b\n1,2\n")

        # Patch module-level directories
        self.patcher_users = patch.object(history_module, "USERS_DIR", self.mock_users_dir)
        self.patcher_sample = patch.object(history_module, "SAMPLE_DIR", self.mock_sample_dir)
        self.patcher_users.start()
        self.patcher_sample.start()

    def tearDown(self):
        self.patcher_users.stop()
        self.patcher_sample.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_filename(self):
        """Verifies directory traversal and invalid filenames are strictly rejected."""
        valid_filenames = ["dataset.csv", "report_2026.xlsx", "sales.data.json"]
        for fn in valid_filenames:
            self.assertEqual(sanitize_filename(fn), fn)

        invalid_filenames = [
            "",
            "../secret.txt",
            "../../etc/passwd",
            "nested/dir/file.csv",
            "nested\\dir\\file.csv",
            ".hidden_file",
        ]
        for fn in invalid_filenames:
            with self.assertRaises(ValueError):
                sanitize_filename(fn)

    def test_save_history_sandboxed_per_user(self):
        """Verifies uploaded files are stored strictly inside the user's isolated folder."""
        file_obj = io.BytesIO(b"x,y\n10,20\n")
        file_obj.name = "alice_records.csv"

        saved_path = save_history(file_obj, username="alice")
        self.assertIsNotNone(saved_path)
        expected_path = self.mock_users_dir / "alice" / "uploads" / "alice_records.csv"
        self.assertEqual(saved_path, expected_path)
        self.assertTrue(expected_path.exists())
        self.assertEqual(expected_path.read_text(), "x,y\n10,20\n")

    def test_cross_user_isolation(self):
        """Verifies that user A cannot see or access user B's uploaded files."""
        # Save file for Alice
        file_a = io.BytesIO(b"a,b\n1,2\n")
        file_a.name = "alice_private.csv"
        save_history(file_a, username="alice")

        # Save file for Bob
        file_b = io.BytesIO(b"c,d\n3,4\n")
        file_b.name = "bob_private.csv"
        save_history(file_b, username="bob")

        # Check Alice's view: Sees Alice's uploads and public sample, NOT Bob's
        alice_history = get_history(username="alice")
        self.assertIn("alice_private.csv", alice_history)
        self.assertIn("public_sample.csv", alice_history)
        self.assertNotIn("bob_private.csv", alice_history)

        # Check Bob's view: Sees Bob's uploads and public sample, NOT Alice's
        bob_history = get_history(username="bob")
        self.assertIn("bob_private.csv", bob_history)
        self.assertIn("public_sample.csv", bob_history)
        self.assertNotIn("alice_private.csv", bob_history)

        # Alice attempts to access Bob's private file -> FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            get_file_path("bob_private.csv", username="alice")

        # Bob attempts to access Alice's private file -> FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            get_file_path("alice_private.csv", username="bob")

        # Both can access public sample
        alice_sample_path = get_file_path("public_sample.csv", username="alice")
        bob_sample_path = get_file_path("public_sample.csv", username="bob")
        self.assertEqual(alice_sample_path, bob_sample_path)

    def test_get_user_uploads(self):
        """Verifies get_user_uploads lists only private uploads for that user."""
        file_a = io.BytesIO(b"val\n1\n")
        file_a.name = "file1.csv"
        save_history(file_a, username="charlie")

        uploads = get_user_uploads(username="charlie")
        self.assertEqual(uploads, ["file1.csv"])

        # Another user has empty uploads
        self.assertEqual(get_user_uploads(username="dave"), [])


if __name__ == "__main__":
    unittest.main()

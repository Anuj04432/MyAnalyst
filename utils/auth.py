"""
User Authentication and Credential Management Engine.

Provides secure credential storage, salted cryptographic password hashing,
session state authentication tracking, and sandboxed user folder initialization.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
USERS_DIR = PROJECT_ROOT / "data" / "users"
AUTH_FILE = USERS_DIR / "auth.json"

# Enforce secure username format: alphanumeric, underscore, hyphen, dot, 3-32 chars
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
MIN_PASSWORD_LENGTH = 6
PBKDF2_ITERATIONS = 100_000


def get_default_users_dir() -> Path:
    """Returns the base directory for sandboxed users."""
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    return USERS_DIR


def get_default_auth_file() -> Path:
    """Returns the path to the auth credentials file."""
    get_default_users_dir()
    return AUTH_FILE


def hash_password(password: str, salt: str) -> str:
    """
    Computes salted PBKDF2-HMAC-SHA256 password hash.

    Args:
        password: Raw plain-text password.
        salt: Random hex salt string.

    Returns:
        Hex-encoded hashed string.
    """
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return key.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """
    Verifies a plain-text password against a stored salt and hash using constant-time comparison.

    Args:
        password: Raw plain-text password.
        salt: Stored salt.
        expected_hash: Stored hash hex string.

    Returns:
        True if valid match, False otherwise.
    """
    computed = hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validates username against naming rules and directory traversal risks.

    Args:
        username: Proposed username string.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not username or not isinstance(username, str):
        return False, "Username cannot be empty."

    cleaned = username.strip()
    if len(cleaned) < 3 or len(cleaned) > 32:
        return False, "Username must be between 3 and 32 characters."

    if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        return False, "Username contains invalid characters or path sequences."

    if not USERNAME_REGEX.match(cleaned):
        return False, "Username may only contain letters, numbers, underscores, dots, and hyphens."

    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validates password length and complexity requirements.

    Args:
        password: Raw plain-text password.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    return True, ""


def load_auth_db(auth_file: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Safely reads users database from disk.

    Args:
        auth_file: Optional custom path to credentials file.

    Returns:
        Dictionary of registered users.
    """
    target = auth_file or get_default_auth_file()
    if not target.exists():
        return {}

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        return {}


def save_auth_db(data: Dict[str, Dict[str, Any]], auth_file: Optional[Path] = None) -> bool:
    """
    Safely writes users database to disk.

    Args:
        data: User credentials dictionary.
        auth_file: Optional custom path to credentials file.

    Returns:
        True if write succeeded, False otherwise.
    """
    target = auth_file or get_default_auth_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_user_upload_dir(username: str, users_dir: Optional[Path] = None) -> Path:
    """
    Retrieves and initializes the sandboxed upload folder for a user.

    Args:
        username: Sanitized username.
        users_dir: Optional base directory.

    Returns:
        Path to user's 'uploads' directory.
    """
    base = users_dir or get_default_users_dir()
    user_upload_path = base / username / "uploads"
    user_upload_path.mkdir(parents=True, exist_ok=True)
    return user_upload_path


def signup_user(
    username: str,
    password: str,
    auth_file: Optional[Path] = None,
    users_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Validates, hashes, registers a new user, and initializes their sandboxed storage.

    Args:
        username: Proposed username.
        password: User password.
        auth_file: Optional credentials file path.
        users_dir: Optional base user folder path.

    Returns:
        Tuple of (success, message).
    """
    u_valid, u_err = validate_username(username)
    if not u_valid:
        return False, u_err

    p_valid, p_err = validate_password(password)
    if not p_valid:
        return False, p_err

    clean_user = username.strip()
    users = load_auth_db(auth_file)

    # Check case-insensitive username collision
    lower_map = {k.lower(): k for k in users.keys()}
    if clean_user.lower() in lower_map:
        return False, f"Username '{clean_user}' is already registered. Please choose another."

    salt = secrets.token_hex(16)
    p_hash = hash_password(password, salt)

    users[clean_user] = {
        "salt": salt,
        "password_hash": p_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if not save_auth_db(users, auth_file):
        return False, "Failed to save user credentials due to a file write error."

    # Initialize user's private upload directory
    get_user_upload_dir(clean_user, users_dir=users_dir)

    return True, f"Account '{clean_user}' created successfully! You can now log in."


def login_user(
    username: str,
    password: str,
    auth_file: Optional[Path] = None,
    users_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Verifies user credentials and updates Streamlit session state on success.

    Args:
        username: Username.
        password: Password.
        auth_file: Optional credentials file path.
        users_dir: Optional base user folder path.

    Returns:
        Tuple of (success, message).
    """
    if not username or not password:
        return False, "Please enter both username and password."

    clean_user = username.strip()
    users = load_auth_db(auth_file)

    user_record = users.get(clean_user)
    if not user_record:
        # Case-insensitive fallback check
        for registered_user, data in users.items():
            if registered_user.lower() == clean_user.lower():
                user_record = data
                clean_user = registered_user
                break

    if not user_record:
        return False, "Invalid username or password."

    salt = user_record.get("salt", "")
    expected_hash = user_record.get("password_hash", "")

    if not verify_password(password, salt, expected_hash):
        return False, "Invalid username or password."

    # Initialize user's sandboxed directory if not present
    get_user_upload_dir(clean_user, users_dir=users_dir)

    # Set authentication in session state
    if hasattr(st, "session_state"):
        st.session_state["authenticated_user"] = clean_user
        st.session_state["is_authenticated"] = True

    return True, f"Welcome back, {clean_user}!"


def logout_user() -> None:
    """
    Purges authenticated user session, resets loaded datasets and chat history,
    preventing any state or data leakage between users.
    """
    if hasattr(st, "session_state"):
        # Reset core analyst state
        st.session_state["authenticated_user"] = None
        st.session_state["is_authenticated"] = False
        st.session_state["df"] = None
        st.session_state["filename"] = None
        st.session_state["messages"] = []

        # Clear any cached component keys
        keys_to_clear = [
            k for k in list(st.session_state.keys())
            if k.startswith("sidebar_") or k.startswith("auth_") or k.startswith("eda_")
        ]
        for k in keys_to_clear:
            del st.session_state[k]


def get_current_user() -> Optional[str]:
    """
    Retrieves the currently authenticated username from session state.

    Returns:
        Username string if authenticated, None otherwise.
    """
    if hasattr(st, "session_state"):
        if st.session_state.get("is_authenticated", False):
            return st.session_state.get("authenticated_user")
    return None


def is_user_authenticated() -> bool:
    """
    Checks if a user is currently logged in.

    Returns:
        True if authenticated, False otherwise.
    """
    return get_current_user() is not None


def get_all_usernames(auth_file: Optional[Path] = None) -> List[str]:
    """
    Returns list of all registered usernames.

    Args:
        auth_file: Optional credentials file path.

    Returns:
        List of usernames.
    """
    users = load_auth_db(auth_file)
    return sorted(list(users.keys()))

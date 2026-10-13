"""
Sandboxed Dataset History and File Management Engine.

Enforces per-user directory isolation to prevent data leaks between concurrent users,
while providing shared access to public sample datasets.
"""

from pathlib import Path
from typing import List, Optional
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploaded"
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"
USERS_DIR = PROJECT_ROOT / "data" / "users"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    ".csv", ".xlsx", ".xls", ".json", ".feather", ".db", ".sqlite", ".sqlite3"
}


def sanitize_filename(filename: str) -> str:
    """
    Validates and extracts base filename to prevent directory traversal attacks.

    Args:
        filename: Provided filename string.

    Returns:
        Safe base filename string.

    Raises:
        ValueError: If filename contains directory traversal patterns or invalid characters.
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename must be a non-empty string.")

    cleaned = Path(filename).name.strip()
    if not cleaned or cleaned.startswith(".") or ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(f"Security alert: Invalid or unsafe filename '{filename}'.")

    return cleaned


def resolve_user_upload_dir(username: Optional[str] = None) -> Path:
    """
    Determines and initializes the sandboxed directory for uploads.
    If username is not provided, attempts to retrieve current logged-in user from session state.
    Falls back to legacy global UPLOAD_DIR when no user is authenticated.

    Args:
        username: Optional username string.

    Returns:
        Path to the target user upload directory.
    """
    target_user = username
    if target_user is None:
        try:
            from utils.auth import get_current_user
            target_user = get_current_user()
        except ImportError:
            target_user = None

    if target_user:
        # Sanitize username against traversal
        safe_user = Path(target_user).name.strip()
        user_dir = USERS_DIR / safe_user / "uploads"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    return UPLOAD_DIR


def save_history(file, username: Optional[str] = None) -> Optional[Path]:
    """
    Saves an uploaded file into the user's isolated sandboxed directory.

    Args:
        file: Uploaded file object (with .name and .getbuffer()).
        username: Optional target username.

    Returns:
        Path to saved file, or None if file is invalid.
    """
    if not file:
        return None

    safe_name = sanitize_filename(getattr(file, "name", "uploaded_file"))
    target_dir = resolve_user_upload_dir(username)
    file_path = target_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(file.getbuffer())

    if hasattr(file, "seek"):
        file.seek(0)

    return file_path


def get_sample_datasets() -> List[str]:
    """
    Retrieves all valid public sample datasets in data/sample/.

    Returns:
        Sorted list of sample filenames.
    """
    if not SAMPLE_DIR.exists():
        return []

    datasets = [
        f.name
        for f in SAMPLE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith(".")
    ]
    return sorted(datasets)


def get_sample_file_path(filename: str) -> Path:
    """
    Retrieves the absolute path of a public sample dataset.

    Args:
        filename: Sample dataset filename.

    Returns:
        Path to the sample file.

    Raises:
        FileNotFoundError: If the file does not exist in data/sample/.
        ValueError: If filename is unsafe.
    """
    safe_name = sanitize_filename(filename)
    file_path = SAMPLE_DIR / safe_name
    if file_path.exists() and file_path.is_file():
        return file_path
    raise FileNotFoundError(f"Sample dataset '{filename}' not found in {SAMPLE_DIR}")


def get_user_uploads(username: Optional[str] = None) -> List[str]:
    """
    Lists files uploaded privately by the specified or active user.

    Args:
        username: Optional username.

    Returns:
        Sorted list of user upload filenames.
    """
    target_dir = resolve_user_upload_dir(username)
    if not target_dir.exists():
        return []

    uploads = [
        f.name
        for f in target_dir.iterdir()
        if f.is_file()
        and not f.name.startswith(".")
        and f.name != ".gitkeep"
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(uploads)


def get_history(username: Optional[str] = None) -> List[str]:
    """
    Returns available datasets accessible to the specified user:
    Strictly combines the user's private uploads and public samples.
    Cross-user data leakage is strictly prohibited.

    Args:
        username: Optional username.

    Returns:
        Sorted unique list of dataset filenames.
    """
    target_dir = resolve_user_upload_dir(username)
    accessible = set()

    # Add user private uploads
    if target_dir.exists():
        for f in target_dir.iterdir():
            if (
                f.is_file()
                and not f.name.startswith(".")
                and f.name != ".gitkeep"
                and f.suffix.lower() in SUPPORTED_EXTENSIONS
            ):
                accessible.add(f.name)

    # Add shared public samples
    for sample_name in get_sample_datasets():
        accessible.add(sample_name)

    return sorted(list(accessible))


def get_file_path(filename: str, username: Optional[str] = None) -> Path:
    """
    Resolves the absolute path for a dataset filename accessible to the user.
    Validates ownership by checking the user's sandboxed directory first,
    then the shared public sample directory.

    Args:
        filename: Dataset filename.
        username: Optional username.

    Returns:
        Path to the resolved file.

    Raises:
        FileNotFoundError: If file is not found in user uploads or sample datasets.
        ValueError: If filename contains unsafe patterns.
    """
    safe_name = sanitize_filename(filename)
    user_dir = resolve_user_upload_dir(username)

    # Check user sandbox first
    candidate_user = user_dir / safe_name
    if candidate_user.exists() and candidate_user.is_file():
        return candidate_user

    # Check shared sample directory second
    candidate_sample = SAMPLE_DIR / safe_name
    if candidate_sample.exists() and candidate_sample.is_file():
        return candidate_sample

    raise FileNotFoundError(
        f"Dataset '{filename}' not found in user storage ({user_dir}) or sample directory."
    )

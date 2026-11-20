from pathlib import Path

from utils.firebase_utils import (
    get_streamlit_firebase_secrets,
    get_firebase_storage_bucket,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_DIR / "assets" / "uploads"
STORAGE_PREFIX = "profile_photos/"


def save_profile_photo(filename, content, content_type):
    if get_streamlit_firebase_secrets() is not None:
        object_name = f"{STORAGE_PREFIX}{filename}"
        blob = get_firebase_storage_bucket().blob(object_name)
        blob.upload_from_string(content, content_type=content_type)
        return object_name

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / filename).write_bytes(content)
    return filename


def load_profile_photo(photo_name):
    if not photo_name:
        return None

    if photo_name.startswith(STORAGE_PREFIX):
        return get_firebase_storage_bucket().blob(photo_name).download_as_bytes()

    local_path = UPLOADS_DIR / photo_name
    if local_path.is_file():
        return local_path.read_bytes()
    return None

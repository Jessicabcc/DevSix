from functools import lru_cache
import os
from pathlib import Path, PurePosixPath

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from utils.firebase_utils import (
    get_streamlit_firebase_secrets,
    get_firebase_storage_bucket,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_DIR / "assets" / "uploads"
STORAGE_PREFIX = "profile_photos/"
SUPABASE_PHOTO_MARKER = "supabase:"


def _supabase_settings():
    try:
        settings = dict(st.secrets["supabase"])
    except (KeyError, StreamlitSecretNotFoundError):
        settings = {}

    url = settings.get("url") or os.environ.get("SUPABASE_URL")
    secret_key = settings.get("secret_key") or os.environ.get("SUPABASE_SECRET_KEY")
    configured_bucket = (
        settings.get("bucket")
        or os.environ.get("SUPABASE_STORAGE_BUCKET")
    )
    bucket = configured_bucket or "profile-photos"
    if not url and not secret_key:
        if configured_bucket:
            raise ValueError(
                "Configure supabase.url e supabase.secret_key nos Secrets do Streamlit."
            )
        return None
    if not url or not secret_key:
        raise ValueError(
            "Configure supabase.url e supabase.secret_key nos Secrets do Streamlit."
        )
    return url, secret_key, bucket


@lru_cache(maxsize=1)
def _get_supabase_client():
    settings = _supabase_settings()
    if settings is None:
        raise ValueError("As credenciais do Supabase não estão configuradas.")

    from supabase import create_client

    url, secret_key, _ = settings
    return create_client(url, secret_key)


def _supabase_object_path(photo_name):
    if not photo_name.startswith(SUPABASE_PHOTO_MARKER):
        raise ValueError("Referência de foto do Supabase inválida.")

    object_path = photo_name[len(SUPABASE_PHOTO_MARKER):]
    parts = PurePosixPath(object_path).parts
    if (
        len(parts) != 2
        or parts[0] != STORAGE_PREFIX.rstrip("/")
        or parts[1] in ("", ".", "..")
        or "\\" in object_path
    ):
        raise ValueError("Caminho de foto do Supabase inválido.")
    return object_path


def save_profile_photo(filename, content, content_type):
    settings = _supabase_settings()
    if settings is not None:
        _, _, bucket_name = settings
        object_path = f"{STORAGE_PREFIX}{filename}"
        _get_supabase_client().storage.from_(bucket_name).upload(
            object_path,
            content,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
        return f"{SUPABASE_PHOTO_MARKER}{object_path}"

    if get_streamlit_firebase_secrets() is not None:
        raise ValueError(
            "Configure Supabase Storage antes de enviar fotos. "
            "Novos uploads não são enviados ao Firebase Storage."
        )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / filename).write_bytes(content)
    return filename


def load_profile_photo(photo_name):
    if not photo_name:
        return None

    if photo_name.startswith(SUPABASE_PHOTO_MARKER):
        settings = _supabase_settings()
        if settings is None:
            raise ValueError(
                "A foto está no Supabase, mas as credenciais do Supabase não estão configuradas."
            )
        _, _, bucket_name = settings
        object_path = _supabase_object_path(photo_name)
        return (
            _get_supabase_client()
            .storage.from_(bucket_name)
            .download(object_path)
        )

    if photo_name.startswith(STORAGE_PREFIX):
        return get_firebase_storage_bucket().blob(photo_name).download_as_bytes()

    if Path(photo_name).name != photo_name:
        raise ValueError("Nome de foto local inválido.")
    local_path = UPLOADS_DIR / photo_name
    if local_path.is_file():
        return local_path.read_bytes()
    return None

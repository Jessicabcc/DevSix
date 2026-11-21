import logging
import os
from functools import lru_cache
from pathlib import Path, PurePosixPath

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
import httpx

from utils.firebase_utils import (
    get_streamlit_firebase_secrets,
    get_firebase_storage_bucket,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_DIR / "assets" / "uploads"
STORAGE_PREFIX = "profile_photos/"
SUPABASE_PHOTO_MARKER = "supabase:"
logger = logging.getLogger(__name__)


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
    url = str(url).strip().rstrip("/")
    for suffix in (
        "/storage/v1/s3",
        "/storage/v1",
        "/rest/v1",
        "/auth/v1",
    ):
        if url.lower().endswith(suffix):
            url = url[: -len(suffix)]
            break
    if url.endswith(".storage.supabase.co"):
        project_ref = url.split("//", 1)[-1].split(".", 1)[0]
        url = f"https://{project_ref}.supabase.co"
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
        url, secret_key, _ = settings
        try:
            response = httpx.post(
                f"{url}/storage/v1/object/{bucket_name}/{object_path}",
                headers={
                    "Authorization": f"Bearer {secret_key}",
                    "apikey": secret_key,
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
                content=content,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            logger.warning(
                "Falha no upload para o Supabase Storage",
                extra={
                    "bucket": bucket_name,
                    "status": status_code,
                },
            )
            if status_code in (401, 403):
                mensagem = (
                    "A chave do Supabase não tem permissão para acessar o Storage."
                )
            elif status_code == 404:
                mensagem = (
                    f"O bucket '{bucket_name}' não existe no projeto Supabase configurado."
                )
            else:
                mensagem = (
                    f"Não foi possível enviar a foto ao Supabase Storage "
                    f"(bucket '{bucket_name}')."
                )
            raise ValueError(
                mensagem
                + " Confirme o bucket, a chave secreta e as permissões nos Secrets."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Erro de rede no upload para o Supabase Storage",
                extra={"bucket": bucket_name},
            )
            raise ValueError(
                f"Não foi possível conectar ao Supabase Storage "
                f"(bucket '{bucket_name}'). Confirme a URL e a chave nos Secrets."
            ) from exc
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

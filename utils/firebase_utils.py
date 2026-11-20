from functools import lru_cache
import os

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore, storage
from streamlit.errors import StreamlitSecretNotFoundError


FIREBASE_PROJECT_ID = "reservasalas-6622c"


def get_streamlit_firebase_secrets():
    try:
        return dict(st.secrets["firebase"])
    except (KeyError, StreamlitSecretNotFoundError):
        return None


def _storage_bucket_name():
    secrets = get_streamlit_firebase_secrets()
    return (
        (secrets or {}).get("storage_bucket")
        or os.environ.get("FIREBASE_STORAGE_BUCKET")
    )


@lru_cache(maxsize=1)
def get_firebase_app():
    secrets = get_streamlit_firebase_secrets()
    project_id = (
        (secrets or {}).get("project_id")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or FIREBASE_PROJECT_ID
    )
    options = {"projectId": project_id}
    bucket_name = _storage_bucket_name()
    if bucket_name:
        options["storageBucket"] = bucket_name
    try:
        return firebase_admin.get_app()
    except ValueError:
        if secrets is None:
            return firebase_admin.initialize_app(options=options)

        required = ("project_id", "client_email", "private_key")
        missing = [key for key in required if not secrets.get(key)]
        if missing:
            raise ValueError(
                "Configure firebase.project_id, firebase.client_email e "
                "firebase.private_key nos Secrets do Streamlit."
            )

        credential = credentials.Certificate({
            "type": "service_account",
            "project_id": secrets["project_id"],
            "client_email": secrets["client_email"],
            "private_key": secrets["private_key"],
        })
        return firebase_admin.initialize_app(credential, options=options)


@lru_cache(maxsize=1)
def get_firestore_client():
    return firestore.client(app=get_firebase_app())


def get_firebase_storage_bucket():
    bucket_name = _storage_bucket_name()
    if not bucket_name:
        raise ValueError(
            "Configure firebase.storage_bucket nos Secrets do Streamlit ou "
            "FIREBASE_STORAGE_BUCKET no ambiente."
        )
    return storage.bucket(bucket_name, app=get_firebase_app())
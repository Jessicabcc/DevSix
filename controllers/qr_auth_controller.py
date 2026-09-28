from datetime import datetime, timedelta
from io import BytesIO
import os
import secrets
import socket
from urllib.parse import urlsplit, urlunsplit

import qrcode
import streamlit as st

from models.db_manager import get_data


TOKEN_LIFETIME = timedelta(minutes=2)
PUBLIC_URL_ENV = "STREAMLIT_PUBLIC_URL"


@st.cache_resource
def _pending_logins():
    return {}


def create_login_token(usuario):
    agora = datetime.now()
    tokens = _pending_logins()
    for token, registro in list(tokens.items()):
        if registro["expira_em"] <= agora:
            tokens.pop(token, None)

    token = secrets.token_urlsafe(32)
    tokens[token] = {"usuario": usuario, "expira_em": agora + TOKEN_LIFETIME}
    return token


def consume_login_token(token):
    registro = _pending_logins().pop(str(token or ""), None)
    if not registro or registro["expira_em"] <= datetime.now():
        return None

    usuarios = get_data("usuarios")
    encontrado = usuarios[usuarios["nome"] == registro["usuario"]]
    if encontrado.empty:
        return None
    usuario = encontrado.iloc[0]
    return {
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
        "foto": usuario["foto"],
    }


def gerar_qr_png(conteudo):
    codigo = qrcode.QRCode(box_size=7, border=2)
    codigo.add_data(conteudo)
    codigo.make(fit=True)
    imagem = codigo.make_image(fill_color="#102044", back_color="#ffffff")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def url_para_qr(url_atual):
    configurada = os.getenv(PUBLIC_URL_ENV, "").strip().rstrip("/")
    if configurada:
        return configurada

    partes = urlsplit(str(url_atual or ""))
    if not partes.scheme or not partes.netloc:
        return None
    if partes.hostname not in ("localhost", "127.0.0.1", "::1"):
        return urlunsplit((partes.scheme, partes.netloc, "", "", "")).rstrip("/")

    conexao = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        conexao.connect(("8.8.8.8", 80))
        endereco_rede = conexao.getsockname()[0]
    except OSError:
        return None
    finally:
        conexao.close()

    if endereco_rede.startswith("127."):
        return None
    host = endereco_rede
    if partes.port:
        host = f"{host}:{partes.port}"
    return urlunsplit((partes.scheme, host, partes.path, "", "")).rstrip("/")

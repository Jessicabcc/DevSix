from datetime import datetime, timedelta
import uuid

import pandas as pd

from models.db_manager import get_data, registrar_historico, save_data, add_user


PAPEIS_CONVITE = ("Professor", "Coordenador", "Administrador", "Secretário")


def create_invitation(tipo_conta, criado_por, tipo_criador):
    if tipo_conta not in PAPEIS_CONVITE:
        return None
    if tipo_conta in ("Coordenador", "Administrador", "Secretário") and tipo_criador != "Administrador":
        return None
    if tipo_conta == "Professor" and tipo_criador not in ("Administrador", "Coordenador", "Secretário"):
        return None

    convite = {
        "token": str(uuid.uuid4()),
        "usado": "False",
        "expiracao": (datetime.now() + timedelta(minutes=15)).isoformat(),
        "tipo_conta": tipo_conta,
        "criado_por": criado_por,
    }
    convites = get_data("convites")
    save_data("convites", pd.concat([convites, pd.DataFrame([convite])], ignore_index=True))
    registrar_historico("Convite criado", f"Convite para {tipo_conta}", criado_por, tipo_criador)
    return convite


def get_invitation(token):
    token = str(token or "").strip()
    if not token:
        return "ausente", None
    convites = get_data("convites")
    encontrados = convites[(convites["token"] == token) & (convites["usado"].str.casefold() != "true")]
    if encontrados.empty:
        return "invalido", None
    convite = encontrados.iloc[-1].to_dict()
    try:
        expiracao = datetime.fromisoformat(convite["expiracao"])
    except (TypeError, ValueError):
        return "invalido", None
    if datetime.now() > expiracao:
        return "expirado", None
    return "valido", convite


def register_with_invitation(token, nome, email, senha):
    estado, convite = get_invitation(token)
    if estado != "valido":
        return False, estado
    email = str(email or "").strip().casefold()
    if not nome.strip() or not email or "@" not in email or not senha:
        return False, "campos"
    if not add_user(nome, senha, convite["tipo_conta"], convite.get("criado_por"), email=email):
        return False, "duplicado"

    convites = get_data("convites")
    convites.loc[convites["token"] == token, "usado"] = "True"
    save_data("convites", convites)
    registrar_historico("Conta criada", f"Conta de {convite['tipo_conta']} criada para {nome}", nome, convite["tipo_conta"])
    return True, convite["tipo_conta"]
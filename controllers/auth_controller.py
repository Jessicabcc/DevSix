from models.db_manager import get_data, save_data, set_user_status
from utils.password_utils import hash_password, verify_password


def authenticate(usuario, senha):
    usuarios = get_data("usuarios")
    credencial = str(usuario or "").strip().casefold()
    encontrados = usuarios[
        (usuarios["nome"].str.strip().str.casefold() == credencial)
        | (usuarios["email"].str.strip().str.casefold() == credencial)
    ]
    if encontrados.empty:
        return None
    indice = encontrados.index[0]
    registro = usuarios.loc[indice]
    senha_armazenada = str(registro["senha"])
    if not verify_password(senha, senha_armazenada):
        return None
    if not senha_armazenada.startswith(("scrypt:", "pbkdf2:")):
        usuarios.loc[indice, "senha"] = hash_password(senha)
        save_data("usuarios", usuarios)
    return {
        "nome": registro["nome"],
        "email": registro["email"],
        "tipo": registro["tipo"],
        "foto": registro["foto"],
        "status": registro["status"],
    }


def login(usuario, tipo, email="", foto=""):
    set_user_status(usuario, "Online")
    return {
        "logged_in": True,
        "usuario": usuario,
        "tipo": tipo,
        "email": email,
        "foto": foto,
    }


def logout(usuario):
    set_user_status(usuario, "Offline")
    return {"logged_in": False, "usuario": "", "tipo": "", "email": "", "foto": ""}

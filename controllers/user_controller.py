from io import BytesIO
from pathlib import Path
import uuid

from PIL import Image, UnidentifiedImageError

from models.db_manager import PROJECT_DIR, add_user, delete_user, get_data, registrar_historico, save_data


def create_user(nome, senha, tipo, criado_por, email=""):
    if not str(nome or "").strip() or not senha:
        return False
    return add_user(nome.strip(), senha, tipo, criado_por, email=email)


def remove_user(nome, excluido_por):
    usuarios = get_data("usuarios")
    alvo = usuarios[usuarios["nome"] == nome]
    if alvo.empty or not delete_user(nome, excluido_por):
        return False
    favoritos = get_data("favoritos")
    save_data("favoritos", favoritos[favoritos["professor"] != nome])
    registrar_historico("Usuário removido", f"Conta {nome} removida", excluido_por, "")
    return True


def update_profile(nome_atual, novo_nome, imagem=None):
    usuarios = get_data("usuarios")
    atual = usuarios[usuarios["nome"] == nome_atual]
    novo_nome = str(novo_nome or "").strip()
    if atual.empty or not novo_nome:
        return False, "Informe um nome válido."
    if novo_nome.casefold() != nome_atual.casefold() and usuarios["nome"].str.casefold().eq(novo_nome.casefold()).any():
        return False, "Este nome já está em uso."

    nome_foto = str(atual.iloc[0]["foto"] or "")
    if imagem is not None and imagem.size:
        if imagem.size > 5 * 1024 * 1024:
            return False, "A imagem deve ter no máximo 5 MB."
        conteudo = imagem.getvalue()
        try:
            with Image.open(BytesIO(conteudo)) as imagem_validada:
                formato = imagem_validada.format
                imagem_validada.verify()
        except (UnidentifiedImageError, OSError):
            return False, "O arquivo enviado não é uma imagem válida."
        extensoes = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}
        extensao = extensoes.get(formato)
        if not extensao:
            return False, "Use uma imagem PNG, JPG, GIF ou WEBP."
        nome_foto = f"{uuid.uuid4()}{extensao}"
        destino = PROJECT_DIR / "assets" / "uploads" / nome_foto
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)

    usuario_atual = usuarios["nome"] == nome_atual
    usuarios.loc[usuario_atual, "nome"] = novo_nome
    usuarios.loc[usuario_atual, "foto"] = nome_foto
    save_data("usuarios", usuarios)

    if novo_nome != nome_atual:
        reservas = get_data("agendamentos")
        reservas.loc[reservas["professor"] == nome_atual, "professor"] = novo_nome
        save_data("agendamentos", reservas)
        favoritos = get_data("favoritos")
        favoritos.loc[favoritos["professor"] == nome_atual, "professor"] = novo_nome
        save_data("favoritos", favoritos)

    registrar_historico("Perfil atualizado", f"Perfil de {novo_nome} atualizado", novo_nome, str(atual.iloc[0]["tipo"]))
    return True, {"nome": novo_nome, "foto": nome_foto}

"""Informações de versão e ambiente da aplicação."""

import os

APP_NOME = "UniSapiens"
APP_VERSAO = "1.0.0"
APP_AMBIENTE = os.getenv("APP_ENV", "desenvolvimento")


def texto_rodape():
    """Retorna o texto exibido no rodapé com nome, versão e ambiente."""
    return f"{APP_NOME} v{APP_VERSAO} | Ambiente: {APP_AMBIENTE}"
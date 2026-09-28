from datetime import datetime
import re
import unicodedata
import uuid

import pandas as pd

from models.db_manager import get_data, registrar_historico, save_data
from views.campus_metadata import CATEGORIAS_SALA, categoria_da_sala, visual_predio


def listar_predios():
    salas = get_data("salas")
    predios = {}
    cadastrados = get_data("predios")
    if not cadastrados.empty:
        for _, registro in cadastrados.iterrows():
            chave = str(registro["id_predio"])
            predios[chave] = {
                "id_predio": chave,
                "nome": registro["nome"],
                "emoji": registro["emoji"] or visual_predio(chave)["emoji"],
                "total_salas": int((salas["predio"] == chave).sum()) if not salas.empty else 0,
                "salas": salas_do_predio(chave),
            }
    elif not salas.empty:
        for chave in salas["predio"].dropna().unique().tolist():
            visual = visual_predio(chave)
            predios[chave] = {
                "id_predio": chave,
                "nome": chave,
                "emoji": visual["emoji"],
                "total_salas": int((salas["predio"] == chave).sum()),
                "salas": salas_do_predio(chave),
            }
    return predios


def salas_do_predio(predio):
    salas = get_data("salas")
    if salas.empty:
        return []

    registros = []
    for _, sala in salas[salas["predio"] == predio].iterrows():
        status = str(sala.get("status") or "Ativa")
        registros.append({
            "id_sala": sala["id_sala"],
            "predio": sala["predio"],
            "nome_sala": sala["nome_sala"],
            "observacoes": sala.get("observacoes", ""),
            "categoria": categoria_da_sala(sala["predio"], sala.get("categoria")),
            "status": status,
        })
    return registros


def reservas_enriquecidas():
    reservas = get_data("agendamentos")
    salas = get_data("salas")
    mapa_predio = {}
    if not salas.empty:
        for _, sala in salas.iterrows():
            mapa_predio[str(sala["nome_sala"]).strip()] = sala["predio"]

    itens = []
    if reservas.empty:
        return itens

    for _, reserva in reservas.iterrows():
        nome_sala = reserva["nome_sala"]
        itens.append({
            "id_reserva": reserva["id_reserva"],
            "sala": nome_sala,
            "data": reserva["data"],
            "turno": reserva["turno"],
            "professor": reserva["professor"],
            "status": reserva["status"],
            "predio_nome": mapa_predio.get(str(nome_sala).strip(), "Campus"),
            "predio": reserva["predio"],
            "email": reserva["email"],
            "solicitado_em": reserva["solicitado_em"],
            "responsavel": reserva["responsavel"],
            "decidido_em": reserva["decidido_em"],
        })
    return itens


def calcular_metricas(reservas):
    hoje = datetime.now().date()
    total = len(reservas)
    aprovadas = len([r for r in reservas if r.get("status") == "Aprovado"])
    pendentes = len([r for r in reservas if r.get("status") == "Pendente"])
    rejeitadas = len([r for r in reservas if r.get("status") == "Rejeitado"])
    semana, mes = 0, 0
    for reserva in reservas:
        try:
            data_reserva = datetime.strptime(str(reserva.get("data", "")), "%Y-%m-%d").date()
            diff = (hoje - data_reserva).days
            if 0 <= diff <= 7:
                semana += 1
            if 0 <= diff <= 30:
                mes += 1
        except ValueError:
            continue
    return {
        "total": total,
        "aprovadas": aprovadas,
        "pendentes": pendentes,
        "rejeitadas": rejeitadas,
        "semana": semana,
        "mes": mes,
    }


def ranking_ocupacao():
    reservas = reservas_enriquecidas()
    salas = get_data("salas")
    contagem = {}
    for reserva in reservas:
        if reserva.get("status") == "Aprovado":
            sala = reserva.get("sala")
            contagem[sala] = contagem.get(sala, 0) + 1

    valores = list(contagem.values())
    media = sum(valores) / len(valores) if valores else 0
    ranking = []
    if salas.empty:
        return ranking

    for _, sala in salas.iterrows():
        nome_sala = sala["nome_sala"]
        total_reservas = contagem.get(nome_sala, 0)
        ranking.append({
            "nome_sala": nome_sala,
            "predio_nome": sala["predio"],
            "total_reservas": total_reservas,
            "status_cor": "vermelho" if total_reservas > media and total_reservas > 0 else "verde",
            "status_sala": str(sala.get("status") or "Ativa"),
        })
    ranking.sort(key=lambda item: item["total_reservas"], reverse=True)
    return ranking


def slug_predio(texto):
    sem_acento = "".join(
        caractere for caractere in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento).strip("_").lower() or str(uuid.uuid4())[:8]


def criar_predio(nome, emoji, usuario, tipo):
    if tipo not in ("Administrador", "Coordenador", "Secretário") or not str(nome).strip():
        return False
    predios = get_data("predios")
    chave = slug_predio(nome)
    if predios["id_predio"].eq(chave).any():
        chave = f"{chave}_{str(uuid.uuid4())[:4]}"
    novo = pd.DataFrame([{"id_predio": chave, "nome": str(nome).strip(), "emoji": str(emoji or "🏢").strip()}])
    save_data("predios", pd.concat([predios, novo], ignore_index=True))
    registrar_historico("Novo Prédio", f"Prédio '{nome}' cadastrado no sistema", usuario, tipo)
    return True


def criar_sala(predio, nome, observacoes, categoria, usuario, tipo):
    if tipo not in ("Administrador", "Coordenador", "Secretário"):
        return False
    predios = get_data("predios")
    salas = get_data("salas")
    nome = str(nome or "").strip()
    if not nome or not predios["id_predio"].eq(predio).any():
        return False
    if ((salas["predio"] == predio) & (salas["nome_sala"].str.casefold() == nome.casefold())).any():
        return False
    if categoria not in CATEGORIAS_SALA:
        categoria = "Normal"
    nova = pd.DataFrame([{
        "id_sala": str(uuid.uuid4()),
        "predio": predio,
        "nome_sala": nome,
        "observacoes": str(observacoes or "").strip(),
        "categoria": categoria,
        "status": "Ativa",
    }])
    save_data("salas", pd.concat([salas, nova], ignore_index=True))
    predio_nome = predios.loc[predios["id_predio"] == predio, "nome"].iloc[0]
    registrar_historico("Nova Sala", f"Sala '{nome}' cadastrada em {predio_nome} (categoria: {CATEGORIAS_SALA[categoria]['label']})", usuario, tipo)
    return True


def alterar_status_sala(id_sala, acao, usuario, tipo):
    if tipo != "Administrador" or acao not in ("bloquear", "desbloquear"):
        return False
    salas = get_data("salas")
    alvo = salas["id_sala"] == id_sala
    if not alvo.any():
        return False
    novo_status = "Bloqueada" if acao == "bloquear" else "Ativa"
    nome = salas.loc[alvo, "nome_sala"].iloc[0]
    salas.loc[alvo, "status"] = novo_status
    save_data("salas", salas)
    acao_historico = "Bloqueio de Sala" if acao == "bloquear" else "Desbloqueio de Sala"
    registrar_historico(acao_historico, f"Sala '{nome}' ficou {novo_status.lower()}", usuario, tipo)
    return True


def favoritos_do_usuario(usuario):
    favoritos = get_data("favoritos")
    salas = get_data("salas")
    predios = listar_predios()
    ids = set(favoritos.loc[favoritos["professor"] == usuario, "id_sala"].astype(str))
    resultado = []
    for sala in salas[salas["id_sala"].astype(str).isin(ids)].to_dict("records"):
        sala["predio_nome"] = predios.get(sala["predio"], {}).get("nome", sala["predio"])
        resultado.append(sala)
    return resultado


def alternar_favorito(usuario, id_sala, tipo):
    if tipo != "Professor":
        return False
    salas = get_data("salas")
    if not salas["id_sala"].astype(str).eq(str(id_sala)).any():
        return False
    favoritos = get_data("favoritos")
    existente = (favoritos["professor"] == usuario) & (favoritos["id_sala"].astype(str) == str(id_sala))
    if existente.any():
        favoritos = favoritos[~existente]
        acao = "Favorito removido"
    else:
        favorito = pd.DataFrame([{"professor": usuario, "id_sala": str(id_sala)}])
        favoritos = pd.concat([favoritos, favorito], ignore_index=True)
        acao = "Favorito adicionado"
    save_data("favoritos", favoritos)
    registrar_historico(acao, f"Sala {id_sala}", usuario, tipo)
    return True

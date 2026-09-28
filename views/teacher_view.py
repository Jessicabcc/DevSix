import streamlit as st

from models.db_manager import get_data
from controllers.campus_controller import listar_predios, reservas_enriquecidas, salas_do_predio
from views import streamlit_pages


def _notificacoes(usuario):
    trocas = get_data("trocas")
    reservas = get_data("agendamentos")
    if trocas.empty or reservas.empty:
        return []

    por_id = reservas.set_index("id_reserva")
    avisos = []
    for _, troca in trocas.iterrows():
        if troca["status"] != "Pendente":
            continue
        try:
            r1 = por_id.loc[troca["id_reserva_1"]]
            r2 = por_id.loc[troca["id_reserva_2"]]
        except KeyError:
            continue
        if r1["professor"] != usuario:
            continue
        avisos.append({
            "id_troca": troca["id_troca"],
            "status": troca["status"],
            "sala_1": r1["nome_sala"],
            "data_1": r1["data"],
            "turno_1": r1["turno"],
            "sala_2": r2["nome_sala"],
            "data_2": r2["data"],
            "turno_2": r2["turno"],
            "prof_2": r2["professor"],
        })
    return avisos


def render(pagina="inicio", predio=""):
    usuario = st_usuario()
    tipo = st_tipo()
    predios = listar_predios()
    reservas = reservas_enriquecidas()
    minhas = [r for r in reservas if r["professor"] == usuario]
    minhas_aprovadas = [r for r in minhas if r["status"] == "Aprovado"]

    if pagina == "predio":
        nome = predio if predio in predios else (next(iter(predios), "Campus"))
        streamlit_pages.pagina_predio(usuario, tipo, nome, salas_do_predio(nome), pode_agendar=(tipo == "Professor"))
        return
    if pagina == "reservas":
        streamlit_pages.pagina_reservas(usuario, tipo, minhas)
        return
    if pagina == "notificacoes":
        streamlit_pages.pagina_notificacoes(usuario, tipo, _notificacoes(usuario))
        return
    if pagina == "dashboard":
        streamlit_pages.pagina_dashboard_professor(usuario, reservas=minhas)
        return
    if pagina == "perfil":
        streamlit_pages.pagina_perfil(usuario, tipo)
        return

    streamlit_pages.pagina_inicio(usuario, tipo, predios, reservas, minhas_aprovadas)


def st_usuario():
    return st.session_state.get("usuario", "")


def st_tipo():
    return st.session_state.get("tipo", "")

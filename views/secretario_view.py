import time

import streamlit as st

from controllers.campus_controller import calcular_metricas, listar_predios, ranking_ocupacao, reservas_enriquecidas, salas_do_predio
from controllers.exchange_controller import approve_exchange, update_exchange_status
from controllers.user_controller import create_user, remove_user
from models.db_manager import get_data
from views import streamlit_pages
from utils import mensagens as txt

def render(pagina="admin"):
    usuario = st.session_state.get("usuario", "")
    tipo = st.session_state.get("tipo", "")

    if pagina == "dashboard":
        predios = listar_predios()
        reservas = reservas_enriquecidas()
        salas = get_data("salas").to_dict("records")
        streamlit_pages.pagina_dashboard(
            usuario, tipo, calcular_metricas(reservas), ranking_ocupacao(), len(salas), len(predios)
        )
        return
    if pagina == "inicio":
        predios = listar_predios()
        reservas = reservas_enriquecidas()
        streamlit_pages.pagina_inicio(usuario, tipo, predios, reservas, [])
        return
    if pagina == "predio":
        predios = listar_predios()
        nome = st.query_params.get("predio", next(iter(predios), "Campus"))
        streamlit_pages.pagina_predio(usuario, tipo, nome, salas_do_predio(nome), pode_agendar=False)
        return
    if pagina == "perfil":
        streamlit_pages.pagina_perfil(usuario, tipo)
        return

    predios = listar_predios()
    reservas = reservas_enriquecidas()
    salas = get_data("salas").to_dict("records")
    streamlit_pages.pagina_admin(
        usuario,
        tipo,
        [r for r in reservas if r["status"] == "Pendente"],
        salas,
        list(predios.keys()),
    )
    _formularios_secretario()


def _formularios_secretario():
    st.markdown("### Cadastros e análises (Streamlit)")
    tab_trocas, tab_historico, tab_professores = st.tabs(
        ["Aprovar Trocas", "Histórico", "Gerenciar Professores"],
        on_change="rerun",
        key="secretario_tabs",
    )

    with tab_trocas:
        df_trocas = get_data("trocas")
        pendentes = df_trocas[df_trocas["status"] == "Pendente"] if not df_trocas.empty else df_trocas
        if pendentes.empty:
            st.info(txt.MSG_NENHUMA_TROCA_PENDENTE)
        else:
            df_agend = get_data("agendamentos")
            for _, troca in pendentes.iterrows():
                reserva_1 = df_agend[df_agend["id_reserva"] == troca["id_reserva_1"]].iloc[0]
                reserva_2 = df_agend[df_agend["id_reserva"] == troca["id_reserva_2"]].iloc[0]
                st.write("---")
                st.write(f"**Reserva 1:** {reserva_1['nome_sala']} ({reserva_1['data']} - {reserva_1['turno']}) - {reserva_1['professor']}")
                st.write(f"**Reserva 2:** {reserva_2['nome_sala']} ({reserva_2['data']} - {reserva_2['turno']}) - {reserva_2['professor']}")
                c1, c2 = st.columns(2)
                if c1.button("Aprovar Troca", key=f"sec_t_apr_{troca['id_troca']}"):
                    approve_exchange(troca, reserva_1.to_dict(), reserva_2.to_dict())
                    st.rerun()
                if c2.button("Rejeitar Troca", key=f"sec_t_rej_{troca['id_troca']}"):
                    update_exchange_status(troca["id_troca"], "Rejeitado")
                    st.rerun()

    with tab_historico:
        df_agend = get_data("agendamentos")
        processadas = df_agend[df_agend["status"].isin(["Aprovado", "Rejeitado"])]
        if processadas.empty:
            st.info(txt.MSG_NENHUMA_RESERVA_PROCESSADA)
        else:
            st.dataframe(processadas[["nome_sala", "data", "turno", "professor", "status"]], hide_index=True)

    with tab_professores:
        with st.form("form_professor_secretario"):
            nome_professor = st.text_input("Nome do Professor")
            senha_professor = st.text_input("Definir Senha", type="password")
            if st.form_submit_button("Cadastrar Professor", type="primary"):
                if not nome_professor.strip() or not senha_professor:
                    st.error(txt.MSG_USUARIO_SENHA_OBRIGATORIOS)
                elif create_user(nome_professor, senha_professor, "Professor", st.session_state["usuario"]):
                    st.success(txt.MSG_PROFESSOR_CADASTRADO)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(txt.MSG_PROFESSOR_NAO_CADASTRADO)

        professores = get_data("usuarios")
        professores = professores[professores["tipo"] == "Professor"]
        for _, professor in professores.iterrows():
            col_nome, col_acao = st.columns([5, 1])
            col_nome.write(f"{professor['nome']} ({professor['status']})")
            if col_acao.button("Excluir", key=f"secretario_excluir_{professor['nome']}"):
                if remove_user(professor["nome"], st.session_state["usuario"]):
                    st.success(txt.MSG_PROFESSOR_EXCLUIDO)
                    st.rerun()
=======
    if tab_trocas.open:
        with tab_trocas:
            df_trocas = get_data("trocas")
            pendentes = df_trocas[df_trocas["status"] == "Pendente"] if not df_trocas.empty else df_trocas
            if pendentes.empty:
                st.info("Nenhuma solicitação de troca de sala pendente.")
            else:
                df_agend = get_data("agendamentos")
                for _, troca in pendentes.iterrows():
                    reserva_1 = df_agend[df_agend["id_reserva"] == troca["id_reserva_1"]].iloc[0]
                    reserva_2 = df_agend[df_agend["id_reserva"] == troca["id_reserva_2"]].iloc[0]
                    st.write("---")
                    st.write(f"**Reserva 1:** {reserva_1['nome_sala']} ({reserva_1['data']} - {reserva_1['turno']}) - {reserva_1['professor']}")
                    st.write(f"**Reserva 2:** {reserva_2['nome_sala']} ({reserva_2['data']} - {reserva_2['turno']}) - {reserva_2['professor']}")
                    c1, c2 = st.columns(2)
                    if c1.button("Aprovar Troca", key=f"sec_t_apr_{troca['id_troca']}"):
                        approve_exchange(troca, reserva_1.to_dict(), reserva_2.to_dict())
                        st.rerun()
                    if c2.button("Rejeitar Troca", key=f"sec_t_rej_{troca['id_troca']}"):
                        update_exchange_status(troca["id_troca"], "Rejeitado")
                        st.rerun()

    if tab_historico.open:
        with tab_historico:
            df_agend = get_data("agendamentos")
            processadas = df_agend[df_agend["status"].isin(["Aprovado", "Rejeitado"])]
            if processadas.empty:
                st.info("Nenhuma reserva processada ainda.")
            else:
                st.dataframe(processadas[["nome_sala", "data", "turno", "professor", "status"]], hide_index=True)

    if tab_professores.open:
        with tab_professores:
            with st.form("form_professor_secretario"):
                nome_professor = st.text_input("Nome do Professor")
                senha_professor = st.text_input("Definir Senha", type="password")
                if st.form_submit_button("Cadastrar Professor", type="primary"):
                    if not nome_professor.strip() or not senha_professor:
                        st.error("Informe um usuário e uma senha.")
                    elif create_user(nome_professor, senha_professor, "Professor", st.session_state["usuario"]):
                        st.success("Professor cadastrado com sucesso.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário já existe ou você não tem permissão para esta ação.")

            professores = get_data("usuarios")
            professores = professores[professores["tipo"] == "Professor"]
            for _, professor in professores.iterrows():
                col_nome, col_acao = st.columns([5, 1])
                col_nome.write(f"{professor['nome']} ({professor['status']})")
                if col_acao.button("Excluir", key=f"secretario_excluir_{professor['nome']}"):
                    if remove_user(professor["nome"], st.session_state["usuario"]):
                        st.success("Professor excluído com sucesso.")
                        st.rerun()

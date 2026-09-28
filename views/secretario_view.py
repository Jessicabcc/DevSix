import time

import streamlit as st

from controllers.campus_controller import calcular_metricas, listar_predios, ranking_ocupacao, reservas_enriquecidas
from controllers.exchange_controller import approve_exchange, update_exchange_status
from controllers.user_controller import create_user, remove_user
from models.db_manager import get_data
from views import streamlit_pages


def render(pagina="admin"):
    usuario = st.session_state.get("usuario", "")
    tipo = st.session_state.get("tipo", "")
    predios = listar_predios()
    reservas = reservas_enriquecidas()
    salas_df = get_data("salas")
    salas = salas_df.to_dict("records") if not salas_df.empty else []

    if pagina == "dashboard":
        streamlit_pages.pagina_dashboard(
            usuario, tipo, calcular_metricas(reservas), ranking_ocupacao(), len(salas), len(predios)
        )
        return
    if pagina == "perfil":
        streamlit_pages.pagina_perfil(usuario, tipo)
        return
    if pagina == "inicio":
        streamlit_pages.pagina_inicio(usuario, tipo, predios, reservas, [])
        return
    if pagina == "predio":
        from controllers.campus_controller import salas_do_predio
        nome = st.query_params.get("predio", next(iter(predios), "Campus"))
        streamlit_pages.pagina_predio(usuario, tipo, nome, salas_do_predio(nome), pode_agendar=False)
        return

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
    tab_trocas, tab_historico, tab_professores = st.tabs(["Aprovar Trocas", "Histórico", "Gerenciar Professores"])

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

    with tab_historico:
        df_agend = get_data("agendamentos")
        processadas = df_agend[df_agend["status"].isin(["Aprovado", "Rejeitado"])]
        if processadas.empty:
            st.info("Nenhuma reserva processada ainda.")
        else:
            st.dataframe(processadas[["nome_sala", "data", "turno", "professor", "status"]], hide_index=True)

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

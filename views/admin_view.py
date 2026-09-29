from datetime import datetime
from html import escape
from io import BytesIO

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controllers.campus_controller import (
    alterar_status_sala,
    calcular_metricas,
    criar_predio,
    criar_sala,
    listar_predios,
    ranking_ocupacao,
    reservas_enriquecidas,
)
from controllers.exchange_controller import approve_exchange, update_exchange_status
from controllers.invitation_controller import create_invitation
from controllers.qr_auth_controller import gerar_qr_png, url_para_qr
from controllers.reservation_controller import update_reservation_status
from controllers.user_controller import remove_user
from models.db_manager import get_data, registrar_historico
from views.campus_metadata import CATEGORIAS_SALA
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
            usuario,
            tipo,
            calcular_metricas(reservas),
            ranking_ocupacao(),
            len(salas),
            len(predios),
        )
        return

    if pagina == "perfil":
        streamlit_pages.pagina_perfil(usuario, tipo)
        return

    if pagina == "inicio":
        streamlit_pages.pagina_inicio(
            usuario,
            tipo,
            predios,
            reservas,
            [r for r in reservas if r["professor"] == usuario and r["status"] == "Aprovado"],
        )
        return

    if pagina == "predio":
        from controllers.campus_controller import salas_do_predio
        nome = st.query_params.get("predio", next(iter(predios), "Campus"))
        streamlit_pages.pagina_predio(usuario, tipo, nome, salas_do_predio(nome), pode_agendar=False)
        return

    streamlit_pages._navegacao(usuario, tipo)
    st.title("Painel administrativo" if tipo == "Administrador" else "Painel de coordenação")
    st.caption("Escolha uma área para gerenciar o campus.")
    _formularios_admin([r for r in reservas if r["status"] == "Pendente"])


def _formularios_admin(reservas_pendentes):
    usuario = st.session_state.get("usuario", "")
    tipo = st.session_state.get("tipo", "")
    tab_contas, tab_aprovacoes, tab_sala, tab_predios, tab_relatorio, tab_gerenciar = st.tabs([
        "Gerar acessos", "Aprovações", "Adicionar sala", "Cadastrar prédio", "Relatório", "Gerenciar salas"
    ])

    with tab_sala:
        st.subheader("Cadastrar sala")
        with st.expander("Cadastrar prédio ou bloco"):
            with st.form("form_predio_na_sala"):
                novo_predio = st.text_input("Nome do prédio ou bloco")
                simbolo_predio = st.text_input("Símbolo", value="🏢", max_chars=4)
                criar_predio_sala = st.form_submit_button("Cadastrar prédio", type="primary")
            if criar_predio_sala:
                if criar_predio(novo_predio, simbolo_predio, usuario, tipo):
                    st.success(f"Prédio {novo_predio} cadastrado.")
                    st.rerun()
                st.error("Informe um nome de prédio válido.")

        predios = get_data("predios")
        if predios.empty:
            st.info("Cadastre um prédio antes de adicionar salas.")
        else:
            mapa_predios = dict(zip(predios["id_predio"], predios["nome"]))
            with st.form("form_sala"):
                predio = st.selectbox("Prédio", list(mapa_predios), format_func=mapa_predios.get)
                nome_sala = st.text_input("Nome da sala")
                categoria = st.selectbox(
                    "Categoria",
                    list(CATEGORIAS_SALA),
                    format_func=lambda chave: CATEGORIAS_SALA[chave]["label"],
                )
                observacoes = st.text_area("Observações e equipamentos")
                enviar_sala = st.form_submit_button("Criar sala", type="primary")
            if enviar_sala:
                if criar_sala(predio, nome_sala, observacoes, categoria, usuario, tipo):
                    st.success(f"Sala {nome_sala} cadastrada.")
                    st.rerun()
                st.error("Informe um nome único e selecione um prédio válido.")

    with tab_aprovacoes:
        st.subheader("Solicitações de reserva")
        if not reservas_pendentes:
            st.info("Nenhuma solicitação pendente.")
        for indice, reserva in enumerate(reservas_pendentes):
            with st.container(border=True):
                st.subheader(reserva.get("sala", "Sala"))
                st.write(f"Professor: {reserva.get('professor', '')}")
                st.caption(f"{reserva.get('data', '')} | {reserva.get('turno', '')}")
                aprovar, rejeitar = st.columns(2)
                if aprovar.button("Aprovar", key=f"aprovar_{reserva.get('id_reserva', indice)}", type="primary"):
                    update_reservation_status(reserva["id_reserva"], "Aprovado", usuario, tipo)
                    st.rerun()
                if rejeitar.button("Rejeitar", key=f"rejeitar_{reserva.get('id_reserva', indice)}"):
                    update_reservation_status(reserva["id_reserva"], "Rejeitado", usuario, tipo)
                    st.rerun()
                st.caption(f"Solicitado em: {reserva.get('solicitado_em') or 'Não informado'}")

        st.subheader("Propostas de troca pendentes")
        df_trocas = get_data("trocas")
        pendentes = df_trocas[df_trocas["status"] == "Pendente"] if not df_trocas.empty else df_trocas
        if pendentes.empty:
            st.info("Nenhuma solicitação de troca de sala pendente.")
        else:
            df_agend = get_data("agendamentos")
            for _, row in pendentes.iterrows():
                primeira = df_agend[df_agend["id_reserva"] == row["id_reserva_1"]]
                segunda = df_agend[df_agend["id_reserva"] == row["id_reserva_2"]]
                if primeira.empty or segunda.empty:
                    continue
                with st.container(border=True):
                    st.write(f"**Destinatário:** {primeira.iloc[0]['professor']} | {primeira.iloc[0]['nome_sala']}")
                    st.write(f"**Solicitante:** {segunda.iloc[0]['professor']} | {segunda.iloc[0]['nome_sala']}")
                    aprovar, rejeitar = st.columns(2)
                    if aprovar.button("Aceitar troca", key=f"t_apr_{row['id_troca']}"):
                        resultado = approve_exchange(row, primeira.iloc[0].to_dict(), segunda.iloc[0].to_dict())
                        if resultado == "aprovada":
                            st.success("Titularidade das reservas atualizada.")
                        else:
                            st.error("Não foi possível aplicar a troca.")
                        st.rerun()
                    if rejeitar.button("Rejeitar troca", key=f"t_rej_{row['id_troca']}"):
                        update_exchange_status(row["id_troca"], "Rejeitado")
                        registrar_historico("Troca rejeitada", f"Troca {row['id_troca']} rejeitada pela administração", usuario, tipo)
                        st.rerun()

    with tab_contas:
        st.subheader("Gerar convite de cadastro")
        papeis = ["Professor"]
        if tipo == "Administrador":
            papeis.extend(["Coordenador", "Administrador"])
        with st.form("form_convite"):
            papel = st.selectbox("Tipo de conta", papeis)
            gerar = st.form_submit_button("Gerar convite", type="primary")
        if gerar:
            convite = create_invitation(papel, usuario, tipo)
            if convite:
                st.session_state["ultimo_convite"] = convite["token"]
                st.success("Convite criado. Ele expira em 15 minutos e só pode ser usado uma vez.")
            else:
                st.error("Seu perfil não pode gerar esse tipo de convite.")
        token = st.session_state.get("ultimo_convite")
        if token:
            base_url = url_para_qr(st.context.url)
            if base_url:
                link = f"{base_url}/?page=registro&token={token}"
                st.image(gerar_qr_png(link), width=168)
                st.caption("Escaneie para abrir o cadastro. O convite expira em 15 minutos e só pode ser usado uma vez.")
                st.code(link, language=None)
            else:
                st.warning("Defina STREAMLIT_PUBLIC_URL para gerar um QR acessível por outros dispositivos.")

        df_users = get_data("usuarios")
        st.dataframe(df_users[["nome", "email", "tipo", "status"]], hide_index=True)
        gerenciaveis = df_users[df_users["tipo"] != "Administrador"]
        for _, conta in gerenciaveis.iterrows():
            col_nome, col_acao = st.columns([5, 1])
            col_nome.write(f"{conta['nome']} ({conta['tipo']}, {conta['status']})")
            if col_acao.button("Excluir", key=f"excluir_{conta['nome']}"):
                if remove_user(conta["nome"], usuario):
                    st.success(f"{conta['nome']} excluído.")
                    st.rerun()

    with tab_predios:
        st.subheader("Cadastrar prédio")
        with st.form("form_predio"):
            nome_predio = st.text_input("Nome do prédio")
            emoji_predio = st.text_input("Símbolo", value="🏢", max_chars=4)
            criar = st.form_submit_button("Criar prédio", type="primary")
        if criar:
            if criar_predio(nome_predio, emoji_predio, usuario, tipo):
                st.success(f"Prédio {nome_predio} cadastrado.")
                st.rerun()
            st.error("Informe um nome de prédio válido.")
        st.dataframe(get_data("predios"), hide_index=True)

    with tab_relatorio:
        st.write("Exporte as reservas e o histórico de alterações do campus.")
        pdf = _gerar_relatorio_pdf()
        st.download_button(
            "Baixar relatório PDF",
            data=pdf,
            file_name=f"relatorio_unisapiens_{datetime.now():%Y%m%d_%H%M}.pdf",
            mime="application/pdf",
            icon=":material/download:",
        )

    with tab_gerenciar:
        st.subheader("Status das salas")
        df_salas = get_data("salas")
        if not df_salas.empty:
            predios = get_data("predios")
            mapa_predios = dict(zip(predios["id_predio"], predios["nome"]))
            for _, sala in df_salas.iterrows():
                nome_predio = mapa_predios.get(sala["predio"], sala["predio"])
                col_sala, col_estado, col_acao = st.columns([4, 2, 1])
                col_sala.write(f"{sala['nome_sala']} | {nome_predio}")
                col_estado.write(str(sala["status"]))
                if tipo == "Administrador":
                    acao = "desbloquear" if sala["status"] == "Bloqueada" else "bloquear"
                    if col_acao.button(
                        "Liberar" if acao == "desbloquear" else "Bloquear",
                        key=f"status_sala_{sala['id_sala']}",
                    ):
                        alterar_status_sala(sala["id_sala"], acao, usuario, tipo)
                        st.rerun()
        else:
            st.info("Nenhuma sala cadastrada.")

        st.subheader("Histórico de alterações")
        historico = get_data("historico_alteracoes")
        if historico.empty:
            st.info("Nenhuma alteração registrada.")
        else:
            st.dataframe(historico.iloc[::-1], hide_index=True)


def _gerar_relatorio_pdf():
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=landscape(A4), title="Relatório UniSapiens")
    estilos = getSampleStyleSheet()
    reservas = get_data("agendamentos")
    historico = get_data("historico_alteracoes")
    elementos = [
        Paragraph("Relatório de Agendamento de Salas - UniSapiens", estilos["Title"]),
        Paragraph(
            f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por "
            f"{escape(st.session_state.get('usuario', ''))} ({escape(st.session_state.get('tipo', ''))})",
            estilos["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Histórico de Reservas", estilos["Heading2"]),
    ]
    colunas = ["data", "turno", "nome_sala", "professor", "status", "responsavel", "decidido_em"]
    dados = [["Data", "Turno", "Sala", "Professor", "Status", "Responsável", "Decidido em"]]
    dados.extend([[str(valor) for valor in linha] for linha in reservas[colunas].itertuples(index=False, name=None)])
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
    ]))
    elementos.append(tabela)
    elementos.extend([Spacer(1, 20), Paragraph("Registro de Alterações", estilos["Heading2"])])
    historico_dados = [["Data/Hora", "Usuário", "Papel", "Ação", "Detalhes"]]
    historico_dados.extend([
        [str(valor) for valor in linha]
        for linha in historico.iloc[::-1][["data_hora", "usuario", "tipo_usuario", "acao", "detalhes"]]
        .itertuples(index=False, name=None)
    ])
    historico_tabela = Table(historico_dados, repeatRows=1)
    historico_tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(historico_tabela)
    documento.build(elementos)
    return buffer.getvalue()

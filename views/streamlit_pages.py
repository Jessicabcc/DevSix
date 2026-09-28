from datetime import date
from html import escape
from pathlib import Path
import unicodedata

import streamlit as st

from controllers.campus_controller import alternar_favorito, favoritos_do_usuario
from controllers.qr_auth_controller import create_login_token, gerar_qr_png, url_para_qr
from controllers.user_controller import update_profile
from models.db_manager import PROJECT_DIR, get_data

CATEGORIAS_SALA = {
    "Laboratorio": "Laboratório",
    "Normal": "Sala de aula",
    "Metodologia": "Metodologia ativa",
    "Quadra": "Atividade física",
}


def _set_query_params(params):
    st.query_params.clear()
    for key, value in params.items():
        if value not in (None, ""):
            st.query_params[key] = str(value)


def _navegacao(usuario, tipo):
    foto = str(st.session_state.get("foto", ""))
    caminho_foto = PROJECT_DIR / "assets" / "uploads" / foto if foto else None
    pagina_atual = str(st.query_params.get("page", "inicio"))
    if pagina_atual == "dashboard":
        marca = "DASHBOARD INSTITUCIONAL"
    elif pagina_atual == "perfil":
        marca = "MEU PERFIL"
    elif tipo in ("Administrador", "Coordenador") and pagina_atual == "admin":
        marca = "PAINEL ADMIN / COORDENAÇÃO"
    else:
        marca = "UNISAPIENS"

    if tipo in ("Administrador", "Secretário", "Coordenador"):
        links = [("Início", "inicio"), ("Painel Admin", "admin"), ("Dashboard", "dashboard"), ("Meu Perfil", "perfil")]
    elif tipo == "Professor":
        links = [("Início", "inicio"), ("Dashboard", "dashboard"), ("Minhas reservas", "reservas"), ("Notificações", "notificacoes"), ("Meu Perfil", "perfil")]
    else:
        links = [("Início", "inicio"), ("Minhas reservas", "reservas"), ("Notificações", "notificacoes"), ("Meu Perfil", "perfil")]

    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        wrap=False,
        key="app-navbar",
    ):
        st.markdown(f"**{marca}**")
        with st.container(
            horizontal=True,
            horizontal_alignment="right",
            vertical_alignment="center",
            wrap=False,
            key="nav-links",
        ):
            for rotulo, pagina in links:
                st.button(
                    rotulo,
                    key=f"nav_{pagina}",
                    type="primary" if pagina_atual == pagina else "secondary",
                    width="content",
                    on_click=_set_query_params,
                    args=({"page": pagina},),
                )
            with st.container(horizontal=True, vertical_alignment="center", key="nav-user"):
                if caminho_foto and caminho_foto.exists():
                    st.image(str(caminho_foto), width=32)
                st.markdown(f"**{escape(usuario)}**  \n{escape(tipo)}")
            st.button(
                "Sair",
                key="nav_logout",
                icon=":material/logout:",
                type="secondary",
                width="content",
                on_click=_set_query_params,
                args=({"acao": "logout"},),
            )
    st.space(90)


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn").lower().strip()


def pagina_inicio(usuario, tipo, predios, reservas, minhas_aprovadas):
    _navegacao(usuario, tipo)
    st.title("Reserve seu espaço acadêmico")
    st.write("Selecione um prédio para consultar as salas e solicitar um agendamento.")

    predios_ocultos = {"prediocentral", "anexo1", "anexo2anfiteatro", "anexo2antefiatro"}
    predios_visiveis = {
        chave: predio
        for chave, predio in predios.items()
        if "".join(caractere for caractere in _normalizar(predio.get("nome", chave)) if caractere.isalnum())
        not in predios_ocultos
    }

    if predios_visiveis:
        colunas = st.columns(4)
        for indice, (nome, predio) in enumerate(predios_visiveis.items()):
            with colunas[indice % len(colunas)]:
                with st.container(border=True, height=220, key=f"campus-card-{indice}"):
                    st.subheader(f"{predio.get('emoji', '')} {predio.get('nome', nome)}")
                    st.badge(f"{predio.get('total_salas', 0)} salas", color="blue")
                    st.button(
                        "Ver salas",
                        key=f"abrir_predio_{indice}",
                        icon=":material/meeting_room:",
                        width="stretch",
                        on_click=_set_query_params,
                        args=({"page": "predio", "predio": nome},),
                    )
    else:
        st.info("Nenhuma área disponível.")

    st.header("Reservas recentes")
    reservas_visiveis = [reserva for reserva in reservas if reserva.get("status") != "Rejeitado"]
    if not reservas_visiveis:
        st.info("Nenhuma reserva registrada.")

    for indice, reserva in enumerate(reservas_visiveis):
        with st.container(border=True):
            cabecalho, status = st.columns([3, 1])
            cabecalho.subheader(reserva.get("sala", "Sala"))
            status.markdown(f"**{reserva.get('status', 'Sem status')}**")
            st.write(f"Professor: {reserva.get('professor', 'Não informado')}")
            st.caption(
                f"{reserva.get('data', '')} | {reserva.get('turno', '')} | "
                f"{reserva.get('predio_nome', 'Campus')}"
            )

            if (
                tipo == "Professor"
                and reserva.get("professor") != usuario
                and reserva.get("status") == "Aprovado"
            ):
                with st.expander("Propor troca de sala"):
                    if not minhas_aprovadas:
                        st.info("Você precisa ter uma reserva aprovada para propor uma troca.")
                    else:
                        opcoes = {
                            item["id_reserva"]: f"{item['sala']} ({item['data']} - {item['turno']})"
                            for item in minhas_aprovadas
                        }
                        with st.form(f"form_troca_{indice}"):
                            id_origem = st.selectbox(
                                "Sua reserva para oferecer",
                                options=list(opcoes),
                                format_func=opcoes.get,
                                key=f"troca_origem_{indice}",
                            )
                            enviar = st.form_submit_button("Enviar proposta", type="primary")
                        if enviar:
                            _set_query_params({
                                "page": "inicio",
                                "acao": "troca",
                                "id_alvo": reserva.get("id_reserva"),
                                "id_origem": id_origem,
                            })
                            st.rerun()


def pagina_predio(usuario, tipo, predio_nome, salas, pode_agendar):
    _navegacao(usuario, tipo)
    st.title(f"Salas do {predio_nome}")

    filtro_coluna, categoria_coluna = st.columns([2, 1])
    termo = filtro_coluna.text_input("Pesquisar sala ou equipamento", key="filtro_sala_nome")
    categorias = ["Todas"] + list(CATEGORIAS_SALA)
    categoria = categoria_coluna.selectbox(
        "Categoria",
        categorias,
        format_func=lambda valor: "Todas as categorias" if valor == "Todas" else CATEGORIAS_SALA[valor],
        key="filtro_sala_categoria",
    )

    termo_normalizado = _normalizar(termo)
    filtradas = [
        sala for sala in salas
        if (not termo_normalizado or termo_normalizado in _normalizar(sala.get("nome_sala"))
            or termo_normalizado in _normalizar(sala.get("observacoes")))
        and (categoria == "Todas" or sala.get("categoria") == categoria)
    ]
    st.caption(f"Exibindo {len(filtradas)} de {len(salas)} sala(s)")

    if not filtradas:
        st.info("Nenhuma sala corresponde aos filtros.")

    favoritos = get_data("favoritos") if tipo == "Professor" else None
    for indice, sala in enumerate(filtradas):
        categoria_css = {
            "Laboratorio": "laboratorio",
            "Normal": "normal",
            "Metodologia": "metodologia",
            "Quadra": "quadra",
        }.get(sala.get("categoria"), "normal")
        chave_sala = sala.get("id_sala", indice)
        with st.container(border=True, key=f"sala-{categoria_css}-{chave_sala}"):
            st.subheader(sala.get("nome_sala", "Sala"))
            categoria = CATEGORIAS_SALA.get(sala.get("categoria"), "Sala")
            st.badge(categoria, color={
                "Laboratorio": "red",
                "Normal": "green",
                "Metodologia": "blue",
                "Quadra": "orange",
            }.get(sala.get("categoria"), "gray"))
            observacoes = str(sala.get("observacoes") or "").strip()
            st.write(observacoes or "Sem observações adicionais.")
            if tipo == "Professor":
                marcada = (
                    (favoritos["professor"] == usuario)
                    & (favoritos["id_sala"].astype(str) == str(sala["id_sala"]))
                ).any()
                if st.button(
                    "Remover dos favoritos" if marcada else "Adicionar aos favoritos",
                    key=f"favorito_{sala['id_sala']}",
                    icon=":material/star:" if marcada else ":material/star_outline:",
                ):
                    alternar_favorito(usuario, sala["id_sala"], tipo)
                    st.rerun()

            if str(sala.get("status")) == "Bloqueada":
                st.warning("Esta sala está bloqueada para agendamentos.")
            elif pode_agendar:
                with st.form(f"form_reserva_{sala.get('id_sala', indice)}"):
                    data_reserva = st.date_input(
                        "Data do agendamento",
                        value=date.today(),
                        min_value=date.today(),
                        key=f"data_reserva_{indice}",
                    )
                    turno = st.selectbox(
                        "Turno",
                        ["Matutino", "Vespertino", "Noturno"],
                        key=f"turno_reserva_{indice}",
                    )
                    enviar = st.form_submit_button("Solicitar reserva", type="primary")
                if enviar:
                    _set_query_params({
                        "page": "predio",
                        "predio": predio_nome,
                        "acao": "reservar",
                        "sala": sala.get("nome_sala"),
                        "data": data_reserva.isoformat(),
                        "turno": turno,
                    })
                    st.rerun()
            else:
                st.caption("Somente professores podem agendar salas.")


def pagina_reservas(usuario, tipo, reservas):
    _navegacao(usuario, tipo)
    st.title("Minhas solicitações de agendamento")
    if not reservas:
        st.info("Você ainda não possui solicitações de reserva.")
        st.button(
            "Ir para o início",
            on_click=_set_query_params,
            args=({"page": "inicio"},),
        )
        return

    for reserva in reservas:
        with st.container(border=True):
            st.subheader(reserva.get("sala", "Sala"))
            st.write(f"Prédio: {reserva.get('predio_nome', 'Campus')}")
            st.write(f"Data e turno: {reserva.get('data', '')} | {reserva.get('turno', '')}")
            status = reserva.get("status", "Sem status")
            st.markdown(f"**Status: {status}**")
            if status == "Pendente":
                st.caption("Aguardando análise da administração.")
            elif status == "Aprovado":
                st.caption("Reserva confirmada.")
            elif status == "Rejeitado":
                st.caption("Solicitação não aprovada.")


def pagina_notificacoes(usuario, tipo, notificacoes):
    _navegacao(usuario, tipo)
    st.title("Avisos e solicitações")
    st.write("Acompanhe as propostas de troca que envolvem suas reservas.")
    if not notificacoes:
        st.info("Nenhuma proposta de troca no momento.")
        return

    for notificacao in notificacoes:
        with st.container(border=True):
            st.subheader("Proposta de troca")
            st.markdown(f"**Status:** {notificacao.get('status', 'Pendente')}")
            st.write(
                f"Sua reserva: {notificacao.get('sala_1', '')} "
                f"({notificacao.get('data_1', '')} - {notificacao.get('turno_1', '')})"
            )
            st.write(
                f"Outra reserva: {notificacao.get('sala_2', '')} "
                f"({notificacao.get('data_2', '')} - {notificacao.get('turno_2', '')})"
            )
            st.caption(f"Professor: {notificacao.get('prof_2', 'Não informado')}")
            if notificacao.get("status") == "Pendente" and notificacao.get("id_troca"):
                aceitar, rejeitar = st.columns(2)
                for coluna, resposta, rotulo in (
                    (aceitar, "aceitar", "Aceitar troca"),
                    (rejeitar, "rejeitar", "Rejeitar troca"),
                ):
                    if coluna.button(rotulo, key=f"responder_{resposta}_{notificacao['id_troca']}"):
                        _set_query_params({
                            "page": "notificacoes",
                            "acao": "responder_troca",
                            "id": notificacao["id_troca"],
                            "resposta": resposta,
                        })
                        st.rerun()


def pagina_perfil(usuario, tipo):
    _navegacao(usuario, tipo)
    st.title("Meu perfil")
    usuarios = get_data("usuarios")
    atual = usuarios[usuarios["nome"] == usuario]
    registro = atual.iloc[0] if not atual.empty else {}
    foto = str(registro.get("foto", "")) if hasattr(registro, "get") else ""
    caminho_foto = PROJECT_DIR / "assets" / "uploads" / foto if foto else None
    if caminho_foto and caminho_foto.exists():
        st.image(str(caminho_foto), width=112)
    st.write(f"Tipo de conta: {tipo or 'Não informado'}")
    st.write(f"E-mail: {registro.get('email', '') if hasattr(registro, 'get') else ''}")

    with st.form("atualizar_perfil"):
        novo_nome = st.text_input("Nome completo", value=usuario)
        nova_foto = st.file_uploader(
            "Foto de perfil",
            type=["png", "jpg", "jpeg", "gif", "webp"],
            max_upload_size=5,
        )
        salvar = st.form_submit_button("Salvar perfil", type="primary")
    if salvar:
        sucesso, resultado = update_profile(usuario, novo_nome, nova_foto)
        if sucesso:
            st.session_state["usuario"] = resultado["nome"]
            st.session_state["foto"] = resultado["foto"]
            st.success("Perfil atualizado.")
            st.rerun()
        else:
            st.error(resultado)

    st.subheader("Acesso rápido pelo celular")
    if st.button("Gerar QR Code de acesso", icon=":material/qr_code_2:"):
        st.session_state["qr_login_token"] = create_login_token(usuario)
        st.session_state["qr_login_owner"] = usuario
    token_qr = st.session_state.get("qr_login_token")
    if token_qr and st.session_state.get("qr_login_owner") == usuario:
        base_url = url_para_qr(st.context.url)
        if base_url:
            link_qr = f"{base_url}/?page=qr_login&token={token_qr}"
            coluna_qr, coluna_link = st.columns([1, 3])
            coluna_qr.image(gerar_qr_png(link_qr), width=168)
            coluna_link.caption("Escaneie com a câmera do celular. O código expira em 2 minutos e só pode ser usado uma vez.")
            coluna_link.code(link_qr, language=None)
        else:
            st.warning("Defina STREAMLIT_PUBLIC_URL para gerar um QR acessível por outros dispositivos.")

    if tipo == "Professor":
        aba_reservas, aba_favoritas = st.tabs(["Reservas aprovadas", "Salas favoritas"])
        with aba_reservas:
            reservas = get_data("agendamentos")
            aprovadas = reservas[(reservas["professor"] == usuario) & (reservas["status"] == "Aprovado")]
            if aprovadas.empty:
                st.info("Você ainda não possui reservas aprovadas.")
            else:
                st.dataframe(aprovadas[["predio", "nome_sala", "data", "turno", "status"]], hide_index=True)
        with aba_favoritas:
            favoritas = favoritos_do_usuario(usuario)
            if not favoritas:
                st.info("Você ainda não favoritou nenhuma sala.")
            for sala in favoritas:
                with st.container(border=True):
                    st.subheader(sala["nome_sala"])
                    st.caption(f"{sala['predio_nome']} | {CATEGORIAS_SALA.get(sala['categoria'], 'Sala')}")
                    st.write(sala["observacoes"] or "Sem observações adicionais.")
                    st.button(
                        "Remover dos favoritos",
                        key=f"perfil_favorito_{sala['id_sala']}",
                        icon=":material/star:",
                        on_click=alternar_favorito,
                        args=(usuario, sala["id_sala"], tipo),
                    )
                    if sala.get("status") != "Bloqueada":
                        with st.form(f"reservar_favorita_{sala['id_sala']}"):
                            data_reserva = st.date_input(
                                "Data do agendamento",
                                value=date.today(),
                                min_value=date.today(),
                                key=f"data_favorita_{sala['id_sala']}",
                            )
                            turno = st.selectbox(
                                "Turno",
                                ["Matutino", "Vespertino", "Noturno"],
                                key=f"turno_favorita_{sala['id_sala']}",
                            )
                            enviar_reserva = st.form_submit_button("Solicitar reserva", type="primary")
                        if enviar_reserva:
                            _set_query_params({
                                "page": "perfil",
                                "acao": "reservar",
                                "predio": sala["predio"],
                                "sala": sala["nome_sala"],
                                "data": data_reserva.isoformat(),
                                "turno": turno,
                            })
                            st.rerun()


def pagina_admin(usuario, tipo, pendentes, salas, predios):
    _navegacao(usuario, tipo)
    st.title("Painel administrativo" if tipo == "Administrador" else "Painel da secretaria")
    aprovacoes, cadastro_salas = st.tabs(["Aprovações pendentes", "Salas cadastradas"])

    with aprovacoes:
        if not pendentes:
            st.info("Nenhuma solicitação pendente.")
        for indice, reserva in enumerate(pendentes):
            with st.container(border=True):
                st.subheader(reserva.get("sala", "Sala"))
                st.write(f"Professor: {reserva.get('professor', '')}")
                st.caption(f"{reserva.get('data', '')} | {reserva.get('turno', '')}")
                aprovar, rejeitar = st.columns(2)
                aprovar.button(
                    "Aprovar",
                    key=f"aprovar_{reserva.get('id_reserva', indice)}",
                    icon=":material/check:",
                    on_click=_set_query_params,
                    args=({"page": "admin", "acao": "aprovar", "id": reserva.get("id_reserva")},),
                )
                rejeitar.button(
                    "Rejeitar",
                    key=f"rejeitar_{reserva.get('id_reserva', indice)}",
                    icon=":material/close:",
                    on_click=_set_query_params,
                    args=({"page": "admin", "acao": "rejeitar", "id": reserva.get("id_reserva")},),
                )
                st.caption(f"Solicitado em: {reserva.get('solicitado_em') or 'Não informado'}")
                if reserva.get("responsavel") or reserva.get("decidido_em"):
                    st.caption(f"Decidido por {reserva.get('responsavel', '')} em {reserva.get('decidido_em', '')}")

    with cadastro_salas:
        st.caption("Prédios cadastrados: " + (", ".join(predios) if predios else "nenhum"))
        if salas:
            st.dataframe(
                [{"Sala": sala.get("nome_sala"), "Prédio": sala.get("predio")} for sala in salas],
                hide_index=True,
            )
        else:
            st.info("Nenhuma sala cadastrada.")


def pagina_dashboard_professor(usuario, reservas):
    _navegacao(usuario, "Professor")
    st.title("Meu dashboard", icon=":material/dashboard:")
    aprovadas = [reserva for reserva in reservas if reserva.get("status") == "Aprovado"]
    favoritas = favoritos_do_usuario(usuario)

    metricas = st.columns(3)
    metricas[0].metric("Reservas aprovadas", len(aprovadas))
    metricas[1].metric("Salas favoritas", len(favoritas))

    contagem_salas = {}
    for reserva in aprovadas:
        nome_sala = reserva.get("sala", "")
        contagem_salas[nome_sala] = contagem_salas.get(nome_sala, 0) + 1
    sala_mais_reservada = max(contagem_salas, key=contagem_salas.get) if contagem_salas else "Nenhuma ainda"
    metricas[2].metric("Sala mais reservada", sala_mais_reservada)

    st.header("Reservas confirmadas")
    if aprovadas:
        st.dataframe(
            [{
                "Sala": reserva.get("sala", ""),
                "Prédio": reserva.get("predio_nome", "Campus"),
                "Data": reserva.get("data", ""),
                "Turno": reserva.get("turno", ""),
            } for reserva in aprovadas],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Você ainda não possui reservas aprovadas.")

    st.header("Salas favoritas")
    if favoritas:
        for sala in favoritas:
            with st.container(border=True):
                st.subheader(sala.get("nome_sala", "Sala"))
                st.caption(f"{sala.get('predio_nome', 'Campus')} | {CATEGORIAS_SALA.get(sala.get('categoria'), 'Sala')}")
    else:
        st.info("Adicione salas aos favoritos para encontrá-las rapidamente.")


def pagina_dashboard(usuario, tipo, metricas, ranking, total_salas, total_predios):
    _navegacao(usuario, tipo)
    st.title("Visão geral do campus")
    st.write("Métricas consolidadas e ocupação das salas do UniSapiens.")

    indicadores = [
        ("Reservas no total", metricas["total"]),
        ("Aprovadas", metricas["aprovadas"]),
        ("Pendentes", metricas["pendentes"]),
        ("Rejeitadas", metricas["rejeitadas"]),
        ("Últimos 7 dias", metricas["semana"]),
        ("Últimos 30 dias", metricas["mes"]),
        ("Salas cadastradas", total_salas),
        ("Prédios cadastrados", total_predios),
    ]
    for inicio in range(0, len(indicadores), 4):
        colunas = st.columns(4)
        for coluna, (rotulo, valor) in zip(colunas, indicadores[inicio:inicio + 4]):
            coluna.metric(rotulo, valor)

    st.header("Ranking de ocupação")
    if ranking:
        for indice, item in enumerate(ranking):
            with st.container(border=True, key=f"ocupacao-{indice}"):
                coluna_sala, coluna_demanda = st.columns([3, 1])
                coluna_sala.write(f"**{item['nome_sala']}** | {item['predio_nome']}")
                coluna_sala.caption(f"Status: {item['status_sala']}")
                coluna_demanda.metric("Reservas", item["total_reservas"])
                coluna_demanda.badge(
                    "Alta demanda" if item["status_cor"] == "vermelho" else "Ocupação moderada",
                    color="red" if item["status_cor"] == "vermelho" else "green",
                )
    else:
        st.info("Nenhuma sala cadastrada até o momento.")

    st.header("Alterações recentes")
    historico = get_data("historico_alteracoes").iloc[::-1].head(8)
    if historico.empty:
        st.info("Nenhuma alteração estrutural registrada.")
    else:
        st.dataframe(
            historico[["data_hora", "usuario", "tipo_usuario", "acao", "detalhes"]],
            hide_index=True,
        )
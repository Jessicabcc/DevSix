from utils import mensagens as txt
from datetime import date
from html import escape
from pathlib import Path
import unicodedata

import streamlit as st

from controllers.campus_controller import alternar_favorito, favoritos_do_usuario
from controllers.qr_auth_controller import create_login_token, gerar_qr_png, url_para_qr
from controllers.user_controller import update_profile
from models.db_manager import get_data
from views.campus_metadata import categoria_da_sala
from utils.profile_photo_storage import load_profile_photo
from utils.permissoes import pode_agir_como_professor
from utils.versao import APP_NOME

CATEGORIAS_SALA = {
    "Laboratorio": "Laboratório",
    "Normal": "Sala de aula",
    "Metodologia": "Metodologia ativa",
    "Quadra": "Atividade física",
}

EMOJIS_PREDIO_INICIO = {
    "Salas de aula": "📚",
    "Laboratórios": "🧪",
    "Salas de Metodologia Ativa": "🧠",
    "Salas de Atividade Física": "🏃",
}


def _set_query_params(params):
    st.query_params.clear()
    for key, value in params.items():
        if value not in (None, ""):
            st.query_params[key] = str(value)


TITULOS_PAGINA = {
    "inicio": "Início",
    "predio": "Salas",
    "admin": "Painel",
    "dashboard": "Dashboard",
    "meu_dashboard": "Meu dashboard",
    "reservas": "Minhas reservas",
    "notificacoes": "Notificações",
    "perfil": "Meu perfil",
}

ESTADO_MENU = "menu_estado"  # "expandido" ou "recolhido"
MARCAS_CELULAR = ("Mobi", "Android", "iPhone", "iPad")


def _dispositivo_movel():
    """Estimativa pelo User-Agent: o servidor não sabe a largura real da tela."""
    try:
        agente = str(st.context.headers.get("User-Agent", ""))
    except Exception:
        return False
    return any(marca in agente for marca in MARCAS_CELULAR)


def _estado_menu():
    # Computador começa com o menu aberto; celular começa fechado.
    if ESTADO_MENU not in st.session_state:
        st.session_state[ESTADO_MENU] = "recolhido" if _dispositivo_movel() else "expandido"
    return st.session_state[ESTADO_MENU]


def _alternar_menu():
    st.session_state[ESTADO_MENU] = "recolhido" if _estado_menu() == "expandido" else "expandido"


def _fechar_menu():
    st.session_state[ESTADO_MENU] = "recolhido"


def _navegar(params):
    """Troca de página. No celular o menu fecha sozinho depois da escolha."""
    _set_query_params(params)
    if _dispositivo_movel():
        _fechar_menu()


def _grupos_menu(tipo):
    """Opções do menu agrupadas por perfil: [(título do grupo, [(rótulo, página, ícone)])]."""
    inicio = ("Início", "inicio", ":material/home:")
    dashboard = ("Dashboard", "dashboard", ":material/monitoring:")
    reservas = ("Minhas reservas", "reservas", ":material/event_available:")
    notificacoes = ("Notificações", "notificacoes", ":material/notifications:")
    perfil = ("Meu Perfil", "perfil", ":material/person:")
    painel = ("Painel Admin", "admin", ":material/admin_panel_settings:")
    if tipo in ("Administrador", "Coordenador"):
        # Tudo o que o professor tem + as áreas de administração
        meu_dashboard = ("Meu dashboard", "meu_dashboard", ":material/dashboard:")
        dashboard_geral = ("Dashboard geral", "dashboard", ":material/monitoring:")
        return [
            ("Geral", [inicio]),
            ("Minha área", [reservas, notificacoes, meu_dashboard]),
            ("Administração", [painel, dashboard_geral]),
            ("Conta", [perfil]),
        ]
    if tipo == "Secretário":
        return [("Geral", [inicio]), ("Administração", [painel, dashboard]), ("Conta", [perfil])]
    if tipo == "Professor":
        return [("Geral", [inicio]), ("Minha área", [dashboard, reservas, notificacoes]), ("Conta", [perfil])]
    return [("Geral", [inicio]), ("Minha área", [reservas, notificacoes]), ("Conta", [perfil])]


def _navegacao(usuario, tipo):
    """Barra superior + menu lateral retrátil (botão de 3 traços)."""
    foto = str(st.session_state.get("foto", ""))
    imagem_perfil = load_profile_photo(foto) if foto else None
    pagina_atual = str(st.query_params.get("page", "inicio"))
    pagina_destacada = "inicio" if pagina_atual == "predio" else pagina_atual
    estado = _estado_menu()
    recolhido = estado == "recolhido"

    if not recolhido:
        # Área invisível atrás do menu: clicar fora fecha (celular e tablet; o CSS a esconde no computador).
        st.button("Fechar menu", key="menu_fundo", on_click=_fechar_menu)

    # Botão de 3 traços: fixo no canto superior esquerdo (posição definida no CSS).
    st.button(
        "Menu",
        key="menu_toggle",
        icon=":material/menu:",
        help="Abrir ou fechar o menu",
        on_click=_alternar_menu,
    )

    with st.container(key="menu-lateral"):
        # Marcador de estado: o CSS usa :has() nele para recolher o menu e deslocar o conteúdo.
        st.markdown(f'<span class="menu-estado menu-{estado}"></span>', unsafe_allow_html=True)
        with st.container(horizontal=True, vertical_alignment="center", key="menu-usuario"):
            if imagem_perfil:
                st.image(imagem_perfil, width=40)
            else:
                st.markdown(
                    f'<span class="menu-avatar">{escape(usuario[:1].upper())}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div class="menu-usuario-texto"><strong>{escape(usuario)}</strong>'
                f'<span>{escape(tipo)}</span></div>',
                unsafe_allow_html=True,
            )
        for titulo, itens in _grupos_menu(tipo):
            st.markdown(f'<div class="menu-grupo">{escape(titulo)}</div>', unsafe_allow_html=True)
            for rotulo, pagina, icone in itens:
                st.button(
                    rotulo,
                    key=f"nav_{pagina}",
                    icon=icone,
                    help=rotulo if recolhido else None,
                    type="primary" if pagina_destacada == pagina else "secondary",
                    width="stretch",
                    on_click=_navegar,
                    args=({"page": pagina},),
                )
        st.markdown('<div class="menu-grupo"></div>', unsafe_allow_html=True)
        st.button(
            "Sair",
            key="nav_logout",
            icon=":material/logout:",
            help="Sair" if recolhido else None,
            type="secondary",
            width="stretch",
            on_click=_navegar,
            args=({"acao": "logout"},),
        )

    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        wrap=False,
        key="app-navbar",
    ):
        st.markdown(f"**{escape(APP_NOME)}**")
        st.markdown(escape(TITULOS_PAGINA.get(pagina_atual, "")))
    st.space(90)


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn").lower().strip()


TURNOS_RESERVA = ["Matutino", "Vespertino", "Noturno"]
STATUS_FILTRO_RESERVA = ["Aprovado", "Pendente"]
_FILTROS_RESERVAS = {
    "res_filtro_busca": "",
    "res_filtro_predio": "Todos",
    "res_filtro_categoria": "Todas",
    "res_filtro_turno": "Todos",
    "res_filtro_status": "Todos",
}


def _limpar_filtros_reservas():
    for chave, valor in _FILTROS_RESERVAS.items():
        st.session_state[chave] = valor


def _predio_da_reserva(reserva):
    return str(reserva.get("predio") or reserva.get("predio_nome") or "").strip()


def _filtros_reservas(reservas, predios):
    """Mostra os filtros e devolve apenas as reservas que combinam com eles."""
    salas = get_data("salas")
    categoria_por_sala = {}
    if not salas.empty:
        for _, sala in salas.iterrows():
            categoria_por_sala[str(sala["nome_sala"]).strip()] = categoria_da_sala(
                sala["predio"], sala.get("categoria")
            )

    def categoria_da_reserva(reserva):
        return categoria_por_sala.get(str(reserva.get("sala", "")).strip(), "Normal")

    def nome_predio(chave):
        return predios.get(chave, {}).get("nome", chave)

    ids_predios = sorted(
        {_predio_da_reserva(r) for r in reservas if _predio_da_reserva(r)},
        key=lambda chave: _normalizar(nome_predio(chave)),
    )
    opcoes_predio = ["Todos"] + ids_predios
    opcoes_categoria = ["Todas"] + list(CATEGORIAS_SALA)
    opcoes_turno = ["Todos"] + TURNOS_RESERVA
    opcoes_status = ["Todos"] + STATUS_FILTRO_RESERVA

    # garante que um valor antigo (ex.: prédio removido) não quebre o selectbox
    for chave, opcoes in (
        ("res_filtro_predio", opcoes_predio),
        ("res_filtro_categoria", opcoes_categoria),
        ("res_filtro_turno", opcoes_turno),
        ("res_filtro_status", opcoes_status),
    ):
        if st.session_state.get(chave, _FILTROS_RESERVAS[chave]) not in opcoes:
            st.session_state[chave] = _FILTROS_RESERVAS[chave]

    with st.container(border=True, key="filtros-reservas"):
        busca_col, predio_col, categoria_col = st.columns([2, 1.5, 1.5])
        busca = busca_col.text_input(
            "Buscar sala ou professor",
            key="res_filtro_busca",
            placeholder="Ex.: Laboratório 01 ou Prof. Girafales",
        )
        predio = predio_col.selectbox(
            "Prédio", opcoes_predio, key="res_filtro_predio",
            format_func=lambda v: "Todos os prédios" if v == "Todos" else nome_predio(v),
        )
        categoria = categoria_col.selectbox(
            "Tipo de sala", opcoes_categoria, key="res_filtro_categoria",
            format_func=lambda v: "Todos os tipos" if v == "Todas" else CATEGORIAS_SALA[v],
        )
        turno_col, status_col, limpar_col = st.columns([1.5, 1.5, 1], vertical_alignment="bottom")
        turno = turno_col.selectbox(
            "Turno", opcoes_turno, key="res_filtro_turno",
            format_func=lambda v: "Todos os turnos" if v == "Todos" else v,
        )
        status = status_col.selectbox(
            "Status", opcoes_status, key="res_filtro_status",
            format_func=lambda v: "Todos os status" if v == "Todos" else v,
        )
        limpar_col.button(
            "Limpar filtros",
            key="res_filtro_limpar",
            icon=":material/filter_alt_off:",
            width="stretch",
            on_click=_limpar_filtros_reservas,
        )

    termo = _normalizar(busca)
    filtradas = []
    for reserva in reservas:
        if termo and termo not in _normalizar(reserva.get("sala")) and termo not in _normalizar(reserva.get("professor")):
            continue
        if predio != "Todos" and _predio_da_reserva(reserva) != predio:
            continue
        if categoria != "Todas" and categoria_da_reserva(reserva) != categoria:
            continue
        if turno != "Todos" and reserva.get("turno") != turno:
            continue
        if status != "Todos" and reserva.get("status") != status:
            continue
        filtradas.append(reserva)

    st.caption(f"Exibindo {len(filtradas)} de {len(reservas)} reserva(s)")
    return filtradas


def pagina_inicio(usuario, tipo, predios, reservas, minhas_aprovadas):
    _navegacao(usuario, tipo)
    st.title("Reserve seu espaço acadêmico")
    st.write("Selecione uma categoria para consultar as salas e solicitar um agendamento!")

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
                with st.container(border=True, key=f"campus-card-{indice}"):
                    nome_predio = predio.get("nome", nome)
                    emoji_predio = EMOJIS_PREDIO_INICIO.get(nome_predio, predio.get("emoji", ""))
                    st.subheader(f"{emoji_predio} {nome_predio}")
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
        st.info(txt.MSG_NENHUMA_AREA)

    st.header("Reservas recentes")
    reservas_visiveis = [reserva for reserva in reservas if reserva.get("status") != "Rejeitado"]
    if not reservas_visiveis:
        st.info(txt.MSG_NENHUMA_RESERVA_REGISTRADA)
    else:
        reservas_visiveis = _filtros_reservas(reservas_visiveis, predios)
        if not reservas_visiveis:
            st.info("Nenhuma reserva corresponde aos filtros selecionados.")

    for indice, reserva in enumerate(reservas_visiveis):
        chave_reserva = reserva.get("id_reserva", indice)
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
                pode_agir_como_professor(tipo)
                and reserva.get("professor") != usuario
                and reserva.get("status") == "Aprovado"
            ):
                with st.expander("Propor troca de sala"):
                    if not minhas_aprovadas:
                        st.info(txt.MSG_TROCA_SEM_RESERVA_APROVADA)
                    else:
                        opcoes = {
                            item["id_reserva"]: f"{item['sala']} ({item['data']} - {item['turno']})"
                            for item in minhas_aprovadas
                        }
                        with st.form(f"form_troca_{chave_reserva}"):
                            id_origem = st.selectbox(
                                "Sua reserva para oferecer",
                                options=list(opcoes),
                                format_func=opcoes.get,
                                key=f"troca_origem_{chave_reserva}",
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
        st.info(txt.MSG_NENHUMA_SALA_NOS_FILTROS)

    favoritos = get_data("favoritos") if pode_agir_como_professor(tipo) else None
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
            if pode_agir_como_professor(tipo):
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
                st.warning(txt.MSG_SALA_BLOQUEADA)
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
                st.caption("Somente professores, coordenadores e administradores podem agendar salas.")


def pagina_reservas(usuario, tipo, reservas):
    _navegacao(usuario, tipo)
    st.title("Minhas solicitações de agendamento")
    if not reservas:
        st.info(txt.MSG_SEM_SOLICITACOES_RESERVA)
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
        st.info(txt.MSG_NENHUMA_PROPOSTA_TROCA)
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
    imagem_perfil = load_profile_photo(foto) if foto else None
    if imagem_perfil:
        st.image(imagem_perfil, width=112)
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
            st.success(txt.MSG_PERFIL_ATUALIZADO)
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
            st.warning(txt.MSG_DEFINIR_URL_PUBLICA)

    if pode_agir_como_professor(tipo):
        aba_reservas, aba_favoritas = st.tabs(["Reservas aprovadas", "Salas favoritas"])
        with aba_reservas:
            reservas = get_data("agendamentos")
            aprovadas = reservas[(reservas["professor"] == usuario) & (reservas["status"] == "Aprovado")]
            if aprovadas.empty:
                st.info(txt.MSG_SEM_RESERVAS_APROVADAS)
            else:
                st.dataframe(aprovadas[["predio", "nome_sala", "data", "turno", "status"]], hide_index=True)
        with aba_favoritas:
            favoritas = favoritos_do_usuario(usuario)
            if not favoritas:
                st.info(txt.MSG_SEM_FAVORITOS)
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
    aprovacoes, cadastro_salas = st.tabs(
        ["Aprovações pendentes", "Salas cadastradas"],
        on_change="rerun",
        key="admin_aprovacoes_tabs",
    )


    with aprovacoes:
        if not pendentes:
            st.info(txt.MSG_NENHUMA_SOLICITACAO_PENDENTE)
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
            st.info(txt.MSG_NENHUMA_SALA)
    if aprovacoes.open:
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

    if cadastro_salas.open:
        with cadastro_salas:
            st.caption("Prédios cadastrados: " + (", ".join(predios) if predios else "nenhum"))
            if salas:
                st.dataframe(
                    [{"Sala": sala.get("nome_sala"), "Prédio": sala.get("predio")} for sala in salas],
                    hide_index=True,
                )
            else:
                st.info("Nenhuma sala cadastrada.")


def pagina_dashboard_professor(usuario, reservas, tipo="Professor"):
    _navegacao(usuario, tipo)
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
        st.info(txt.MSG_SEM_RESERVAS_APROVADAS)

    st.header("Salas favoritas")
    if favoritas:
        for sala in favoritas:
            with st.container(border=True):
                st.subheader(sala.get("nome_sala", "Sala"))
                st.caption(f"{sala.get('predio_nome', 'Campus')} | {CATEGORIAS_SALA.get(sala.get('categoria'), 'Sala')}")
    else:
        st.info(txt.MSG_ADICIONE_FAVORITOS)


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
        st.info(txt.MSG_NENHUMA_SALA_NO_MOMENTO)

    st.header("Alterações recentes")
    historico = get_data("historico_alteracoes").iloc[::-1].head(8)
    if historico.empty:
        st.info(txt.MSG_NENHUMA_ALTERACAO_ESTRUTURAL)
    else:
        st.dataframe(
            historico[["data_hora", "usuario", "tipo_usuario", "acao", "detalhes"]],
            hide_index=True,
        )
from datetime import date
from pathlib import Path

import streamlit as st

from controllers.auth_controller import authenticate, login, logout as controller_logout
from controllers.exchange_controller import create_exchange, respond_to_exchange
from controllers.qr_auth_controller import consume_login_token
from controllers.reservation_controller import create_reservation, update_reservation_status
from models.db_manager import get_data, init_db
from views import admin_view, registro_view, secretario_view, streamlit_pages, teacher_view

st.set_page_config(page_title="Agendamentos UniSapiens", page_icon="🏫", layout="wide")
init_db()

css_path = Path(__file__).resolve().parent / "style" / "style.css"
eng_style_path = Path(__file__).resolve().parent / "style" / "eng_software_streamlit.css"
identity_style_path = Path(__file__).resolve().parent / "style" / "identity_streamlit.css"
try:
    css = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (css_path, eng_style_path, identity_style_path)
        if path.exists()
    )
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except Exception:
    pass

st.markdown(
    """
    <style>
    .stApp .block-container { padding-top: 0 !important; max-width: 1080px !important; }
    @media (max-width: 640px) {
        .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""
if "tipo" not in st.session_state:
    st.session_state["tipo"] = ""
if "flash" not in st.session_state:
    st.session_state["flash"] = None


def _param(nome, padrao=""):
    valor = st.query_params.get(nome, padrao)
    if isinstance(valor, list):
        return valor[0] if valor else padrao
    return valor or padrao


def _limpar_acao(page, **extras):
    st.query_params.clear()
    st.query_params["page"] = page
    for chave, valor in extras.items():
        if valor:
            st.query_params[chave] = valor


def _flash(tipo, mensagem):
    st.session_state["flash"] = (tipo, mensagem)


def _finalizar_login(credencial):
    st.session_state.pop("login_pendente", None)
    st.session_state.update(login(
        credencial["nome"],
        credencial["tipo"],
        credencial["email"],
        credencial["foto"],
    ))
    st.query_params.clear()
    st.query_params["page"] = "inicio"
    st.rerun()


def processar_acoes():
    acao = _param("acao")
    if not acao:
        return

    predio = _param("predio")

    if acao == "logout":
        st.session_state.update(controller_logout(st.session_state["usuario"]))
        st.query_params.clear()
        st.rerun()

    if not st.session_state["logged_in"]:
        return

    if acao == "reservar" and st.session_state["tipo"] == "Professor":
        sala = _param("sala")
        data_txt = _param("data")
        turno = _param("turno")
        try:
            data_reserva = date.fromisoformat(data_txt)
        except ValueError:
            _flash("error", "Data inválida para a reserva.")
            _limpar_acao("predio", predio=predio)
            st.rerun()
            return
        if data_reserva < date.today():
            _flash("error", "Não é permitido agendar salas em datas passadas.")
        elif create_reservation(
            sala,
            data_reserva,
            turno,
            st.session_state["usuario"],
            email=st.session_state.get("email", ""),
            predio=predio,
        ):
            _flash("success", "Sua reserva foi enviada para aprovação.")
        else:
            _flash("error", "Esta sala já está reservada ou pendente para este dia e turno.")
        _limpar_acao("predio", predio=predio)
        st.rerun()

    if acao == "troca" and st.session_state["tipo"] == "Professor":
        id_alvo = _param("id_alvo")
        id_origem = _param("id_origem")
        agendamentos = get_data("agendamentos")
        origem = agendamentos[agendamentos["id_reserva"] == id_origem]
        alvo = agendamentos[agendamentos["id_reserva"] == id_alvo]
        if origem.empty or alvo.empty or origem.iloc[0]["professor"] != st.session_state["usuario"]:
            _flash("error", "Não foi possível localizar as reservas da troca.")
        else:
            resultado = create_exchange(id_alvo, id_origem, alvo.iloc[0].to_dict(), origem.iloc[0].to_dict())
            if resultado == "invalida":
                _flash("warning", "Troca inválida: mesma sala, dia e turno.")
            elif resultado == "duplicada":
                _flash("warning", "Essa troca já foi registrada.")
            else:
                _flash("success", "A proposta de troca foi enviada para análise.")
        _limpar_acao("inicio")
        st.rerun()

    if acao == "responder_troca" and st.session_state["tipo"] == "Professor":
        resultado = respond_to_exchange(
            _param("id"), _param("resposta"), st.session_state["usuario"]
        )
        if resultado in ("aceita", "rejeitada"):
            _flash("success", "Troca atualizada com sucesso.")
        elif resultado == "sem_permissao":
            _flash("error", "Somente o destinatário da proposta pode responder.")
        else:
            _flash("warning", "Essa proposta não está mais disponível.")
        _limpar_acao("notificacoes")
        st.rerun()

    if acao in ("aprovar", "rejeitar") and st.session_state["tipo"] in ("Administrador", "Coordenador", "Secretário"):
        novo_status = "Aprovado" if acao == "aprovar" else "Rejeitado"
        update_reservation_status(
            _param("id"),
            novo_status,
            st.session_state["usuario"],
            st.session_state["tipo"],
        )
        _flash("success", "Status da reserva atualizado.")
        _limpar_acao("admin")
        st.rerun()


processar_acoes()
if st.session_state.get("flash"):
    tipo_msg, mensagem = st.session_state["flash"]
    {"success": st.success, "error": st.error, "warning": st.warning}.get(tipo_msg, st.info)(mensagem)
    st.session_state["flash"] = None

if not st.session_state["logged_in"]:
    if _param("page") == "qr_login":
        credencial = consume_login_token(_param("token"))
        if credencial:
            _finalizar_login(credencial)
        st.title("Acesso pelo QR Code")
        st.error("Este QR Code expirou ou já foi utilizado. Gere outro no perfil do dispositivo conectado.")
        if st.button("Voltar para o login", icon=":material/login:"):
            st.query_params.clear()
            st.rerun()
    elif _param("page") == "registro":
        registro_view.render()
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("UniSapiens")
            st.caption("Sistema de Agendamento de Salas")
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary"):
                    credencial = authenticate(usuario, senha)
                    if credencial:
                        if credencial.get("status") == "Online":
                            st.session_state["login_pendente"] = credencial
                        else:
                            _finalizar_login(credencial)
                    else:
                        st.error("Credenciais inválidas.")
            st.caption("Cadastros disponíveis por convite | UniSapiens")
        credencial_pendente = st.session_state.get("login_pendente")
        if credencial_pendente:
            st.warning(
                "Esta conta já aparece Online em outro acesso. Confirme sua identidade para continuar."
            )
            confirmar, cancelar = st.columns(2)
            if confirmar.button("Confirmar identidade e entrar", type="primary"):
                _finalizar_login(credencial_pendente)
            if cancelar.button("Cancelar acesso"):
                st.session_state.pop("login_pendente", None)
                st.rerun()
else:
    pagina = _param("page", "inicio")
    predio = _param("predio")
    tipo = st.session_state["tipo"]

    if tipo in ("Administrador", "Coordenador"):
        admin_view.render(pagina)
    elif tipo == "Secretário":
        secretario_view.render(pagina)
    else:
        teacher_view.render(pagina, predio)

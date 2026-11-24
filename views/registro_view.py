import streamlit as st

from controllers.invitation_controller import get_invitation, register_with_invitation
from utils.query_params import get_param, clear_query_params

def render():
    st.title("Criar conta")
    token = get_param("token", "")
    estado, convite = get_invitation(token)
    if estado != "valido":
        avisos = {
             "expirado": txt.MSG_CONVITE_EXPIRADO,
            "invalido": txt.MSG_CONVITE_INVALIDO,
            "ausente": txt.MSG_CONVITE_AUSENTE,
        }

        st.warning(avisos[estado])

        if st.button("Voltar para o login", icon=":material/login:"):
            clear_query_params()
            st.rerun()
        return

    st.caption(f"Cadastro de {convite['tipo_conta']}")

    with st.form("registro_form"):
        nome = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        enviado = st.form_submit_button("Concluir cadastro", type="primary")

    if enviado:
        sucesso, resultado = register_with_invitation(token, nome, email, senha)
        if sucesso:
            st.session_state["flash"] = (
                "success",
                f"Conta de {resultado} criada. Faça login para continuar.",
            )
            clear_query_params()
            st.rerun()
        elif resultado == "campos":
            st.error(txt.MSG_REGISTRO_DADOS_INVALIDOS)
        elif resultado == "expirado":
            st.error(txt.MSG_CONVITE_EXPIRADO)
        elif resultado == "invalido":
            st.error(txt.MSG_CONVITE_INVALIDO)
        else:
            st.error(txt.MSG_REGISTRO_NEGADO)

    if st.button("Voltar para o login", icon=":material/login:"):
        st.query_params.clear()
        st.rerun()
import streamlit as st

from controllers.invitation_controller import get_invitation, register_with_invitation


def render():
    st.title("Criar conta")
    token = st.query_params.get("token", "")
    estado, convite = get_invitation(token)
    if estado != "valido":
        mensagens = {
            "expirado": "Este convite expirou.",
            "invalido": "O convite é inválido ou já foi utilizado.",
            "ausente": "Use um convite válido para criar sua conta.",
        }
        st.warning(mensagens[estado])
        if st.button("Voltar para o login", icon=":material/login:"):
            st.query_params.clear()
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
            st.query_params.clear()
            st.rerun()
        elif resultado == "campos":
            st.error("Informe nome, e-mail válido e senha.")
        elif resultado == "expirado":
            st.error("Este convite expirou.")
        elif resultado == "invalido":
            st.error("O convite é inválido ou já foi utilizado.")
        else:
            st.error("O nome ou e-mail já está cadastrado, ou o convite não tem permissão para este papel.")

    if st.button("Voltar para o login", icon=":material/login:"):
        st.query_params.clear()
        st.rerun()
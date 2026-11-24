import streamlit as st


def get_param(nome, padrao=""):
    valor = st.query_params.get(nome, padrao)

    if isinstance(valor, list):
        return valor[0] if valor else padrao

    return valor or padrao


def set_query_params(params):
    st.query_params.clear()

    for key, value in params.items():
        if value not in (None, ""):
            st.query_params[key] = str(value)


def clear_query_params():
    st.query_params.clear()


def navigate(page, **extras):
    params = {"page": page}
    params.update(extras)
    set_query_params(params)
import streamlit as st
import os
from data.db_manager import init_db, get_data, add_user, set_user_status
from views import admin_view, teacher_view

st.set_page_config(page_title="Agendamentos UniSapiens", page_icon="🏫", layout="wide")

init_db()

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = ''
if 'tipo' not in st.session_state:
    st.session_state['tipo'] = ''

css_file = 'style_dark.css' if st.session_state['theme'] == 'dark' else 'style_light.css'
css_path = os.path.join(os.path.dirname(__file__), 'css', css_file)

try:
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

def logout():
    set_user_status(st.session_state['usuario'], 'Offline')
    st.session_state['logged_in'] = False
    st.session_state['usuario'] = ''
    st.session_state['tipo'] = ''
    st.rerun()

def toggle_theme():
    st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'

if not st.session_state['logged_in']:
    c_theme1, c_theme2 = st.columns([9, 1])
    with c_theme2:
        tema_icone = "☀️ Modo Claro" if st.session_state['theme'] == 'dark' else "🌙 Modo Escuro"
        st.button(tema_icone, on_click=toggle_theme)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #69a88d;'>UNISAPIENS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Agendamento de Salas</p>", unsafe_allow_html=True)
        
        tab_login, tab_registro = st.tabs(["Login", "Registro"])
        
        with tab_login:
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary"):
                    df = get_data('usuarios')
                    user_row = df[(df['nome'] == usuario) & (df['senha'] == senha)]
                    if not user_row.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['usuario'] = usuario
                        st.session_state['tipo'] = user_row.iloc[0]['tipo']
                        set_user_status(usuario, 'Online')
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
                        
        with tab_registro:
            with st.form("reg_form"):
                novo_user = st.text_input("Nome Completo")
                nova_senha = st.text_input("Senha", type="password")
                tipo_conta = st.selectbox("Tipo de Conta", ["Professor", "Administrador"])
                
                if st.form_submit_button("Cadastrar", type="primary"):
                    if add_user(novo_user, nova_senha, tipo_conta):
                        st.success(f"Conta de {tipo_conta} criada! Faça login.")
                    else:
                        st.error("Usuário já existe.")
else:
    c1, c2, c3 = st.columns([8, 1, 1])
    with c1:
        st.markdown(f"**👤 Olá, {st.session_state['usuario']}** ({st.session_state['tipo']})")
    with c2:
        tema_icone = "☀️ Claro" if st.session_state['theme'] == 'dark' else "🌙 Escuro"
        st.button(tema_icone, on_click=toggle_theme, use_container_width=True)
    with c3:
        st.button("Logout", on_click=logout, key="btn_logout", use_container_width=True)
        
    st.markdown("---")
    
    if st.session_state['tipo'] == 'Administrador':
        admin_view.render()
    else:
        teacher_view.render()
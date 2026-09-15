import streamlit as st
from models.db_manager import init_db, get_data
from controllers.auth_controller import authenticate, login, logout as controller_logout
from views import admin_view, secretario_view, teacher_view

st.set_page_config(page_title="Agendamentos UniSapiens", page_icon="🏫", layout="wide")

# Inicializa banco de dados (CSVs)
init_db()

# Carrega o CSS customizado mantendo a interface escura e translúcida
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except:
    pass

# Controle de Sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = ''
if 'tipo' not in st.session_state:
    st.session_state['tipo'] = ''

def logout():
    st.session_state.update(controller_logout(st.session_state['usuario']))
    st.rerun()

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #fbbf24;'>UniSapiens</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sistema de Agendamento de Salas</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                tipo = authenticate(usuario, senha)
                if tipo:
                    st.session_state.update(login(usuario, tipo))
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
else:
    # Cabeçalho pós-login
    c1, c2 = st.columns([8, 1])
    with c1:
        st.markdown(f"**🟢 Online:** {st.session_state['usuario']} ({st.session_state['tipo']})")
    with c2:
        st.button("Sair", on_click=logout, key="btn_logout")
        
    st.markdown("---")
    
    # Roteamento baseado no tipo de usuário
    if st.session_state['tipo'] == 'Administrador':
        admin_view.render()
    elif st.session_state['tipo'] == 'Secretário':
        secretario_view.render()
    else:
        teacher_view.render()
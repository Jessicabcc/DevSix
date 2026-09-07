import streamlit as st
import pandas as pd
import uuid
from data.db_manager import get_data, save_data

def render():
    st.header("Painel do Administrador")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Sala", "Aprovações de Agendamento", "Usuários"])
    
    with tab1:
        st.subheader("Nova Sala / Laboratório")
        with st.form("form_sala"):
            categorias = ["Salas de Aula", "Salas de Atividade Física", "Salas de Metodologia Ativa", "Laboratórios"]
            categoria = st.selectbox("Categoria da Sala", categorias)
            nome_sala = st.text_input("Identificação (Ex: Lab 01, Sala 203)")
            
            c1, c2 = st.columns(2)
            with c1:
                capacidade = st.number_input("Capacidade de Alunos", min_value=1, max_value=200, value=30)
            with c2:
                st.write("")
                st.write("")
                projetor = st.checkbox("Possui Projetor/Equipamento Multimídia")
                
            observacoes = st.text_area("Observações Adicionais")
            submit_sala = st.form_submit_button("Salvar Sala", type="primary")
            
            if submit_sala and nome_sala:
                df_salas = get_data('salas')
                nova_sala = pd.DataFrame([{
                    'id_sala': str(uuid.uuid4()),
                    'categoria': categoria,
                    'nome_sala': nome_sala,
                    'capacidade': capacidade,
                    'projetor': projetor,
                    'observacoes': observacoes
                }])
                save_data('salas', pd.concat([df_salas, nova_sala], ignore_index=True))
                st.toast(f"Sala '{nome_sala}' cadastrada com sucesso! ✅", icon="🏫")
                st.rerun()

    with tab2:
        st.subheader("Reservas Pendentes")
        df_agend = get_data('agendamentos')
        pendentes = df_agend[df_agend['status'] == 'Pendente']
        
        if pendentes.empty:
            st.info("Tudo limpo! Nenhuma reserva pendente.")
        else:
            for i, row in pendentes.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([4, 1, 1])
                    col1.markdown(f"**{row['nome_sala']}** • {row['data']} ({row['turno']})<br>Prof(a): {row['professor']}", unsafe_allow_html=True)
                    if col2.button("Aprovar", key=f"apr_{row['id_reserva']}"):
                        df_agend.loc[df_agend['id_reserva'] == row['id_reserva'], 'status'] = 'Aprovado'
                        save_data('agendamentos', df_agend)
                        st.toast("Reserva aprovada! O professor será notificado.", icon="✅")
                        st.rerun()
                    if col3.button("Rejeitar", key=f"rej_{row['id_reserva']}"):
                        df_agend.loc[df_agend['id_reserva'] == row['id_reserva'], 'status'] = 'Rejeitado'
                        save_data('agendamentos', df_agend)
                        st.toast("Reserva rejeitada.", icon="❌")
                        st.rerun()

    with tab3:
        st.subheader("Status do Corpo Docente")
        df_users = get_data('usuarios')
        st.dataframe(df_users[['nome', 'tipo', 'status']], use_container_width=True, hide_index=True)
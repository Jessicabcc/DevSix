import streamlit as st
import pandas as pd
import uuid
from database.db_manager import get_data, save_data

def render():
    st.header("🏛️ Painel do Administrador - UniSapiens")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Nova Sala", "Aprovar Reservas", "Aprovar Trocas", "Status de Usuários"])
    
    # --- TAB 1: CRIAR SALAS ---
    with tab1:
        st.subheader("Cadastrar Nova Sala")
        with st.form("form_sala"):
            predio = st.selectbox("Prédio", ["Central", "Anexo 1", "Anexo 2"])
            nome_sala = st.text_input("Nome da Sala")
            observacoes = st.text_area("Observações (Equipamentos, capacidade, etc.)")
            submit_sala = st.form_submit_button("Criar Sala")
            
            if submit_sala and nome_sala:
                df_salas = get_data('salas')
                nova_sala = pd.DataFrame([{
                    'id_sala': str(uuid.uuid4()),
                    'predio': predio,
                    'nome_sala': nome_sala,
                    'observacoes': observacoes
                }])
                save_data('salas', pd.concat([df_salas, nova_sala], ignore_index=True))
                st.success(f"Sala {nome_sala} criada no prédio {predio}!")
                st.rerun()

    # --- TAB 2: APROVAR RESERVAS ---
    with tab2:
        st.subheader("Solicitações de Agendamento")
        df_agend = get_data('agendamentos')
        pendentes = df_agend[df_agend['status'] == 'Pendente']
        
        if pendentes.empty:
            st.info("Nenhuma reserva pendente no momento.")
        else:
            for i, row in pendentes.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{row['nome_sala']}** - {row['data']} ({row['turno']}) | Prof: {row['professor']}")
                if col2.button("Aprovar", key=f"apr_{row['id_reserva']}"):
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva'], 'status'] = 'Aprovado'
                    save_data('agendamentos', df_agend)
                    st.rerun()
                if col3.button("Rejeitar", key=f"rej_{row['id_reserva']}"):
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva'], 'status'] = 'Rejeitado'
                    save_data('agendamentos', df_agend)
                    st.rerun()

    # --- TAB 3: APROVAR TROCAS ---
    with tab3:
        st.subheader("Análise de Trocas de Salas")
        df_trocas = get_data('trocas')
        trocas_pendentes = df_trocas[df_trocas['status'] == 'Pendente']
        
        if trocas_pendentes.empty:
            st.info("Nenhuma solicitação de troca de sala pendente.")
        else:
            df_agend = get_data('agendamentos')
            for i, row in trocas_pendentes.iterrows():
                res1 = df_agend[df_agend['id_reserva'] == row['id_reserva_1']].iloc[0]
                res2 = df_agend[df_agend['id_reserva'] == row['id_reserva_2']].iloc[0]
                
                st.write("---")
                st.write(f"🔄 **Solicitação de Troca**")
                st.write(f"**Reserva 1:** Sala {res1['nome_sala']} ({res1['data']} - {res1['turno']}) - Prof. {res1['professor']}")
                st.write(f"**Reserva 2:** Sala {res2['nome_sala']} ({res2['data']} - {res2['turno']}) - Prof. {res2['professor']}")
                
                c1, c2 = st.columns(2)
                if c1.button("Aprovar Troca", key=f"t_apr_{row['id_troca']}"):
                    # Inverter professores
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva_1'], 'professor'] = res2['professor']
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva_2'], 'professor'] = res1['professor']
                    df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Aprovado'
                    save_data('agendamentos', df_agend)
                    save_data('trocas', df_trocas)
                    st.success("Troca aprovada com sucesso!")
                    st.rerun()
                    
                if c2.button("Rejeitar Troca", key=f"t_rej_{row['id_troca']}"):
                    df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Rejeitado'
                    save_data('trocas', df_trocas)
                    st.rerun()

    # --- TAB 4: USUÁRIOS ONLINE/OFFLINE ---
    with tab4:
        st.subheader("Painel de Controle de Usuários")
        filtro = st.radio("Filtrar por Status", ["Todos", "Online", "Offline"], horizontal=True)
        df_users = get_data('usuarios')
        
        if filtro != "Todos":
            df_users = df_users[df_users['status'] == filtro]
            
        st.dataframe(df_users[['nome', 'tipo', 'status']], use_container_width=True, hide_index=True)
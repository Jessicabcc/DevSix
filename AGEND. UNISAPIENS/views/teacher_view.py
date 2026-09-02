import streamlit as st
import pandas as pd
import uuid
from database.db_manager import get_data, save_data

def render():
    st.header(f"🎓 Bem-vindo(a), Prof. {st.session_state['usuario']}")
    
    tab1, tab2 = st.tabs(["Agendar Sala", "Minhas Reservas e Trocas"])
    
    df_salas = get_data('salas')
    df_agend = get_data('agendamentos')
    
    # --- TAB 1: AGENDAR SALA ---
    with tab1:
        st.subheader("Consultar e Reservar")
        if df_salas.empty:
            st.warning("Nenhuma sala cadastrada pelos administradores ainda.")
        else:
            with st.form("form_reserva"):
                sala_selecionada = st.selectbox("Escolha a Sala", df_salas['nome_sala'].tolist())
                data_reserva = st.date_input("Data do Agendamento")
                turno = st.selectbox("Turno", ["Matutino", "Vespertino", "Noturno"])
                
                detalhes_sala = df_salas[df_salas['nome_sala'] == sala_selecionada].iloc[0]
                st.caption(f"**Prédio:** {detalhes_sala['predio']} | **Obs:** {detalhes_sala['observacoes']}")
                
                if st.form_submit_button("Solicitar Reserva", type="primary"):
                    ocupado = df_agend[(df_agend['nome_sala'] == sala_selecionada) & 
                                       (df_agend['data'] == str(data_reserva)) & 
                                       (df_agend['turno'] == turno) & 
                                       (df_agend['status'].isin(['Aprovado', 'Pendente']))]
                    if not ocupado.empty:
                        st.error("Esta sala já está reservada ou pendente para este dia e turno.")
                    else:
                        nova_res = pd.DataFrame([{
                            'id_reserva': str(uuid.uuid4()),
                            'nome_sala': sala_selecionada,
                            'data': str(data_reserva),
                            'turno': turno,
                            'professor': st.session_state['usuario'],
                            'status': 'Pendente'
                        }])
                        save_data('agendamentos', pd.concat([df_agend, nova_res], ignore_index=True))
                        st.success("Sua reserva foi enviada para aprovação do Administrador!")
                        st.rerun()

    # --- TAB 2: MINHAS RESERVAS E SOLICITAR TROCA ---
    with tab2:
        st.subheader("Painel de Trocas de Salas")
        minhas_aprovadas = df_agend[(df_agend['professor'] == st.session_state['usuario']) & (df_agend['status'] == 'Aprovado')]
        outras_aprovadas = df_agend[(df_agend['professor'] != st.session_state['usuario']) & (df_agend['status'] == 'Aprovado')]
        
        st.markdown("##### Suas Reservas Aprovadas")
        st.dataframe(minhas_aprovadas[['nome_sala', 'data', 'turno', 'status']], use_container_width=True, hide_index=True)
        
        st.markdown("##### Propor Troca de Sala com Outra Reserva")
        if minhas_aprovadas.empty or outras_aprovadas.empty:
            st.info("Para propor uma troca, você precisa ter uma sala aprovada e deve existir outra sala aprovada no sistema.")
        else:
            with st.form("form_troca"):
                opcao_minha = st.selectbox("Qual a SUA reserva que deseja oferecer?", 
                                           minhas_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']})", axis=1))
                
                opcao_alvo = st.selectbox("Qual a reserva de OUTRO PROFESSOR que deseja receber em troca?", 
                                          outras_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']} | Prof {r['professor']})", axis=1))
                
                if st.form_submit_button("Sugerir Troca ao Administrador"):
                    idx_minha = minhas_aprovadas.index[minhas_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']})", axis=1) == opcao_minha][0]
                    idx_alvo = outras_aprovadas.index[outras_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']} | Prof {r['professor']})", axis=1) == opcao_alvo][0]
                    
                    id_reserva_1 = minhas_aprovadas.loc[idx_minha, 'id_reserva']
                    id_reserva_2 = outras_aprovadas.loc[idx_alvo, 'id_reserva']
                    
                    df_trocas = get_data('trocas')
                    nova_troca = pd.DataFrame([{
                        'id_troca': str(uuid.uuid4()),
                        'id_reserva_1': id_reserva_1,
                        'id_reserva_2': id_reserva_2,
                        'status': 'Pendente'
                    }])
                    save_data('trocas', pd.concat([df_trocas, nova_troca], ignore_index=True))
                    st.success("A proposta de troca foi enviada ao Administrador para análise!")
                    st.rerun()
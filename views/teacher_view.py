import streamlit as st
import pandas as pd
import uuid
import time
from datetime import date
from models.db_manager import get_data
from controllers.exchange_controller import create_exchange
from controllers.reservation_controller import create_reservation

def render():
    prefixo = "Prof." if st.session_state['tipo'] == 'Professor' else ""
    st.header(f"🎓 Bem-vindo(a), {prefixo} {st.session_state['usuario']}")
    
    tab1, tab2 = st.tabs(["Agendar Sala", "Minhas Reservas e Trocas"])
    
    df_salas = get_data('salas')
    df_agend = get_data('agendamentos')
    
    # --- TAB 1: AGENDAR SALA ---
    with tab1:
        st.subheader("Consultar e Reservar")
        if df_salas.empty:
            st.warning("Nenhuma sala cadastrada pelos administradores ainda.")
        else:
            tipos_sala = sorted(df_salas['predio'].dropna().unique().tolist())
            tipo_sala = st.selectbox("Tipo da Sala", tipos_sala, key="tipo_sala_agendamento")
            salas_do_tipo = df_salas[df_salas['predio'] == tipo_sala]

            with st.form("form_reserva"):
                sala_selecionada = st.selectbox("Escolha a Sala", salas_do_tipo['nome_sala'].tolist())
                data_reserva = st.date_input("Data do Agendamento", min_value=date.today())
                turno = st.selectbox("Turno", ["Matutino", "Vespertino", "Noturno"])
                
                detalhes_sala = df_salas[df_salas['nome_sala'] == sala_selecionada].iloc[0]
                st.caption(f"**Tipo da Sala:** {detalhes_sala['predio']} | **Obs:** {detalhes_sala['observacoes']}")
                
                if st.form_submit_button("Solicitar Reserva", type="primary"):
                    if data_reserva < date.today():
                        st.error("Não é permitido agendar salas em datas passadas. Escolha hoje ou uma data futura.")
                    elif create_reservation(sala_selecionada, data_reserva, turno, st.session_state['usuario']):
                            st.success("Sua reserva foi enviada para aprovação do Administrador!")
                            time.sleep(5)
                            st.rerun()
                    else:
                        st.error("Esta sala já está reservada ou pendente para este dia e turno.")

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

                    reserva_1 = minhas_aprovadas.loc[idx_minha].to_dict()
                    reserva_2 = outras_aprovadas.loc[idx_alvo].to_dict()
                    resultado = create_exchange(id_reserva_1, id_reserva_2, reserva_1, reserva_2)
                    if resultado == 'invalida':
                        st.warning("Troca inválida: não é possível trocar reservas com a mesma sala, mesmo dia e mesmo turno.")
                        time.sleep(5)
                        return

                    if resultado == 'duplicada':
                        st.warning("Essa troca já foi registrada e não pode ser enviada novamente.")
                        time.sleep(5)
                        return
                    st.success("A proposta de troca foi enviada ao Administrador para análise!")
                    time.sleep(5)
                    st.rerun()


import streamlit as st
import pandas as pd
import uuid
from data.db_manager import get_data, save_data

ICONES_CATEGORIA = {
    "Laboratórios": "💻",
    "Salas de Aula": "🧑‍🏫",
    "Salas de Atividade Física": "🏟️",
    "Salas de Metodologia Ativa": "🧪"
}

def render():
    tab_salas, tab_reservas, tab_notificacoes = st.tabs(["Agendar Sala", "Troca de Salas", "Notificações 🔔"])
    
    df_salas = get_data('salas')
    df_agend = get_data('agendamentos')
    df_trocas = get_data('trocas')
    
    with tab_salas:
        categorias = ["Salas de Aula", "Salas de Atividade Física", "Salas de Metodologia Ativa", "Laboratórios"]
        cat_selecionada = st.radio("Selecione a categoria de espaço:", categorias, horizontal=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_filtros, col_grid = st.columns([1, 3])
        
        with col_filtros:
            with st.container(border=True):
                st.markdown("#### Filtros")
                tem_projetor = st.checkbox("Com Projetor")
                capacidade_min = st.slider("Cadeiras", 0, 100, 10)
            
        with col_grid:
            if df_salas.empty:
                st.warning("Nenhuma sala cadastrada no sistema.")
            else:
                salas_filtradas = df_salas[df_salas['categoria'] == cat_selecionada]
                if tem_projetor:
                    salas_filtradas = salas_filtradas[salas_filtradas['projetor'] == True]
                salas_filtradas = salas_filtradas[salas_filtradas['capacidade'] >= capacidade_min]
                
                if salas_filtradas.empty:
                    st.info("Nenhuma sala encontrada com os filtros atuais.")
                else:
                    cols = st.columns(3)
                    for i, row in salas_filtradas.iterrows():
                        with cols[i % 3]:
                            with st.container(border=True):
                                icone = ICONES_CATEGORIA.get(row['categoria'], "📖")
                                st.markdown(f"<h1 style='text-align: center; color: #69a88d;'>{icone}</h1>", unsafe_allow_html=True)
                                st.markdown(f"<p style='text-align: center; font-weight: bold;'>{row['nome_sala']}</p>", unsafe_allow_html=True)
                                
                                with st.expander("Agendar"):
                                    data_reserva = st.date_input("Data", key=f"dt_{row['id_sala']}")
                                    turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"], key=f"tn_{row['id_sala']}")
                                    
                                    if st.button("Confirmar", key=f"btn_{row['id_sala']}", type="primary"):
                                        ocupado = df_agend[(df_agend['nome_sala'] == row['nome_sala']) & 
                                                           (df_agend['data'] == str(data_reserva)) & 
                                                           (df_agend['turno'] == turno) & 
                                                           (df_agend['status'].isin(['Aprovado', 'Pendente']))]
                                        if not ocupado.empty:
                                            st.error("Sala indisponível neste horário.")
                                        else:
                                            nova_res = pd.DataFrame([{
                                                'id_reserva': str(uuid.uuid4()),
                                                'nome_sala': row['nome_sala'],
                                                'data': str(data_reserva),
                                                'turno': turno,
                                                'professor': st.session_state['usuario'],
                                                'status': 'Pendente'
                                            }])
                                            save_data('agendamentos', pd.concat([df_agend, nova_res], ignore_index=True))
                                            st.toast("Agendamento solicitado! Acompanhe na aba de Notificações. 📅", icon="⏳")
                                            st.rerun()

    with tab_reservas:
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Minhas Salas (Aprovadas)")
            minhas_aprovadas = df_agend[(df_agend['professor'] == st.session_state['usuario']) & (df_agend['status'] == 'Aprovado')]
            if minhas_aprovadas.empty:
                st.info("Nenhuma reserva aprovada para realizar trocas.")
            else:
                st.dataframe(minhas_aprovadas[['nome_sala', 'data', 'turno']], use_container_width=True, hide_index=True)
                
        with c2:
            st.subheader("Propor Troca Direta com Colega")
            outras_aprovadas = df_agend[(df_agend['professor'] != st.session_state['usuario']) & (df_agend['status'] == 'Aprovado')]
            
            if minhas_aprovadas.empty or outras_aprovadas.empty:
                st.warning("É necessário que você e outro professor tenham salas aprovadas por um administrador para solicitar uma troca.")
            else:
                with st.form("form_troca"):
                    opcao_minha = st.selectbox("Oferecer minha sala:", 
                                               minhas_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']})", axis=1))
                    
                    opcao_alvo = st.selectbox("Desejo receber a sala:", 
                                              outras_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} | Prof {r['professor']})", axis=1))
                    
                    if st.form_submit_button("Enviar Solicitação de Troca", type="primary"):
                        idx_minha = minhas_aprovadas.index[minhas_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} - {r['turno']})", axis=1) == opcao_minha][0]
                        idx_alvo = outras_aprovadas.index[outras_aprovadas.apply(lambda r: f"{r['nome_sala']} ({r['data']} | Prof {r['professor']})", axis=1) == opcao_alvo][0]
                        
                        nova_troca = pd.DataFrame([{
                            'id_troca': str(uuid.uuid4()),
                            'id_reserva_origem': minhas_aprovadas.loc[idx_minha, 'id_reserva'],
                            'id_reserva_alvo': outras_aprovadas.loc[idx_alvo, 'id_reserva'],
                            'prof_origem': st.session_state['usuario'],
                            'prof_alvo': outras_aprovadas.loc[idx_alvo, 'professor'],
                            'status': 'Pendente'
                        }])
                        save_data('trocas', pd.concat([df_trocas, nova_troca], ignore_index=True))
                        st.toast("Proposta de troca enviada ao professor responsável! 🔄", icon="📩")
                        st.rerun()

    with tab_notificacoes:
        st.subheader("Acompanhamento de Reservas")
        minhas_reservas_todas = df_agend[df_agend['professor'] == st.session_state['usuario']]
        if not minhas_reservas_todas.empty:
            for i, row in minhas_reservas_todas.iterrows():
                cor = "#fbbf24" if row['status'] == 'Pendente' else ("#69a88d" if row['status'] == 'Aprovado' else "#ef4444")
                st.markdown(f"📍 **{row['nome_sala']}** ({row['data']}) - Status: <span style='color:{cor}; font-weight:bold;'>{row['status']}</span>", unsafe_allow_html=True)
        else:
            st.info("Você não possui reservas em andamento.")
            
        st.markdown("---")
        st.subheader("Pedidos de Troca Recebidos")
        trocas_para_mim = df_trocas[(df_trocas['prof_alvo'] == st.session_state['usuario']) & (df_trocas['status'] == 'Pendente')]
        
        if trocas_para_mim.empty:
            st.info("Nenhuma proposta de troca recebida de outros professores.")
        else:
            for i, row in trocas_para_mim.iterrows():
                res_origem = df_agend[df_agend['id_reserva'] == row['id_reserva_origem']].iloc[0]
                res_alvo = df_agend[df_agend['id_reserva'] == row['id_reserva_alvo']].iloc[0]
                
                with st.container(border=True):
                    st.write(f"O(a) professor(a) **{row['prof_origem']}** deseja trocar a sala **{res_origem['nome_sala']}** ({res_origem['data']}) pela sua sala **{res_alvo['nome_sala']}** ({res_alvo['data']}).")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("Aceitar Troca", key=f"t_acc_{row['id_troca']}", type="primary"):
                        df_agend.loc[df_agend['id_reserva'] == row['id_reserva_origem'], 'professor'] = st.session_state['usuario']
                        df_agend.loc[df_agend['id_reserva'] == row['id_reserva_alvo'], 'professor'] = row['prof_origem']
                        df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Aceito'
                        save_data('agendamentos', df_agend)
                        save_data('trocas', df_trocas)
                        st.toast("Troca de sala confirmada e atualizada no sistema! ✅", icon="🤝")
                        st.rerun()
                        
                    if c2.button("Rejeitar", key=f"t_rej_{row['id_troca']}"):
                        df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Rejeitado'
                        save_data('trocas', df_trocas)
                        st.toast("Proposta de troca recusada.", icon="❌")
                        st.rerun()
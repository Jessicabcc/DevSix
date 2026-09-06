import streamlit as st
import pandas as pd
import uuid
import time
from database.db_manager import get_data, save_data, add_user, delete_user, SUPORTE_TI, troca_invalida, troca_ja_registrada

def render():
    st.header("🏛️ Painel do Administrador - UniSapiens")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Nova Sala", "Aprovar Reservas", "Aprovar Trocas", "Histórico de Aprovações", "Status de Usuários"])
    
    # --- TAB 1: CRIAR SALAS ---
    with tab1:
        st.subheader("Cadastrar Nova Sala")
        with st.form("form_sala"):
            predio = st.selectbox("Tipo da Sala", ["Salas de aula", "Salas de Atividade Física", "Salas de Metodologia Ativa", "Laboratórios"])
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
                    time.sleep(5)
                    st.rerun()
                if col3.button("Rejeitar", key=f"rej_{row['id_reserva']}"):
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva'], 'status'] = 'Rejeitado'
                    save_data('agendamentos', df_agend)
                    time.sleep(5)
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
                    if troca_invalida(res1.to_dict(), res2.to_dict()):
                        st.warning("Troca inválida: não é possível aprovar reservas com a mesma sala, mesmo dia e mesmo turno.")
                        time.sleep(5)
                        st.rerun()
                        return
                    if troca_ja_registrada(row['id_reserva_1'], row['id_reserva_2'], df_trocas):
                        st.warning("Essa troca já foi registrada e não pode ser aprovada novamente.")
                        time.sleep(5)
                        st.rerun()
                        return
                    # Troca somente as salas, mantendo cada reserva com seu professor.
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva_1'], 'nome_sala'] = res2['nome_sala']
                    df_agend.loc[df_agend['id_reserva'] == row['id_reserva_2'], 'nome_sala'] = res1['nome_sala']
                    df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Aprovado'
                    save_data('agendamentos', df_agend)
                    save_data('trocas', df_trocas)
                    st.success("Troca aprovada com sucesso!")
                    time.sleep(5)
                    st.rerun()
                    
                if c2.button("Rejeitar Troca", key=f"t_rej_{row['id_troca']}"):
                    df_trocas.loc[df_trocas['id_troca'] == row['id_troca'], 'status'] = 'Rejeitado'
                    save_data('trocas', df_trocas)
                    st.rerun()

    # --- TAB 4: HISTÓRICO DE APROVAÇÕES ---
    with tab4:
        st.subheader("Histórico de Aprovações")
        st.markdown("#### Reservas")
        df_agend_historico = get_data('agendamentos')
        reservas_processadas = df_agend_historico[
            df_agend_historico['status'].isin(['Aprovado', 'Rejeitado'])
        ]
        if reservas_processadas.empty:
            st.info("Nenhuma reserva aprovada ou rejeitada ainda.")
        else:
            st.dataframe(
                reservas_processadas[
                    ['nome_sala', 'data', 'turno', 'professor', 'status']
                ].sort_index(ascending=False),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### Trocas")
        df_trocas_historico = get_data('trocas')
        trocas_processadas = df_trocas_historico[
            df_trocas_historico['status'].isin(['Aprovado', 'Rejeitado'])
        ]
        if trocas_processadas.empty:
            st.info("Nenhuma troca aprovada ou rejeitada ainda.")
        else:
            reservas_por_id = df_agend_historico.set_index('id_reserva')
            historico_trocas = []
            pares_vistos = set()
            for _, troca in trocas_processadas.iterrows():
                par = tuple(sorted([str(troca['id_reserva_1']), str(troca['id_reserva_2'])]))
                if par in pares_vistos:
                    continue
                pares_vistos.add(par)
                reserva_1 = reservas_por_id.loc[troca['id_reserva_1']]
                reserva_2 = reservas_por_id.loc[troca['id_reserva_2']]
                historico_trocas.append({
                    'Professor 1': reserva_1['professor'],
                    'Professor 2': reserva_2['professor'],
                    'Sala 1': reserva_1['nome_sala'],
                    'Sala 2': reserva_2['nome_sala'],
                    'Data Sala 1': reserva_1['data'],
                    'Data Sala 2': reserva_2['data'],
                    'Turno 1': reserva_1['turno'],
                    'Turno 2': reserva_2['turno'],
                    'Status': troca['status'],
                })

            st.dataframe(
                pd.DataFrame(historico_trocas),
                use_container_width=True,
                hide_index=True,
            )

    # --- TAB 5: USUÁRIOS ONLINE/OFFLINE ---
    with tab5:
        st.subheader("Painel de Controle de Usuários")
        st.markdown("#### Cadastrar Usuário")
        with st.form("form_professor"):
            nome_professor = st.text_input("Nome do Usuário")
            senha_professor = st.text_input("Definir Senha", type="password")
            tipos_permitidos = ["Professor"]
            if st.session_state['usuario'] == SUPORTE_TI:
                tipos_permitidos.append("Secretário")
            tipo_usuario = st.selectbox("Tipo de Usuário", tipos_permitidos)
            cadastrar_professor = st.form_submit_button("Cadastrar Usuário", type="primary")

            if cadastrar_professor:
                if not nome_professor.strip() or not senha_professor:
                    st.error("Informe um usuário e uma senha.")
                elif add_user(nome_professor.strip(), senha_professor, tipo_usuario, st.session_state['usuario']):
                    st.success(f"{tipo_usuario} cadastrado com sucesso.")
                    time.sleep(5)
                    st.rerun()
                else:
                    st.error("Usuário já existe no sistema.")
                    time.sleep(5)
                    st.rerun()

        st.markdown("#### Usuários cadastrados")
        filtro = st.radio("Filtrar por Status", ["Todos", "Online", "Offline"], horizontal=True)
        df_users = get_data('usuarios')
        
        if filtro != "Todos":
            df_users = df_users[df_users['status'] == filtro]
            
        st.dataframe(df_users[['nome', 'tipo', 'status']], use_container_width=True, hide_index=True)

        professores = df_users[df_users['tipo'].isin(['Professor', 'Secretário'])]
        if not professores.empty:
            st.markdown("#### Excluir Usuário")
            for _, professor in professores.iterrows():
                col_nome, col_acao = st.columns([5, 1])
                col_nome.write(f"{professor['nome']} ({professor['status']})")
                if col_acao.button("Excluir", key=f"excluir_{professor['nome']}"):
                    if delete_user(professor['nome'], st.session_state['usuario']):
                        st.success(f"Professor {professor['nome']} excluído.")
                        time.sleep(5)
                        st.rerun()
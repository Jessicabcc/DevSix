import streamlit as st
import pandas as pd
from database.db_manager import get_data, save_data, add_user, delete_user


def render():
	st.header(f"📋 Painel do Secretário - {st.session_state['usuario']}")

	tab_reservas, tab_trocas, tab_historico, tab_professores = st.tabs([
		"Aprovar Reservas",
		"Aprovar Trocas",
		"Histórico de Aprovações",
		"Gerenciar Professores",
	])

	with tab_reservas:
		st.subheader("Solicitações de Agendamento")
		df_agend = get_data('agendamentos')
		pendentes = df_agend[df_agend['status'] == 'Pendente']

		if pendentes.empty:
			st.info("Nenhuma reserva pendente no momento.")
		else:
			for _, reserva in pendentes.iterrows():
				col_info, col_aprovar, col_rejeitar = st.columns([3, 1, 1])
				col_info.write(
					f"**{reserva['nome_sala']}** - {reserva['data']} "
					f"({reserva['turno']}) | Prof: {reserva['professor']}"
				)
				if col_aprovar.button("Aprovar", key=f"sec_apr_{reserva['id_reserva']}"):
					df_agend.loc[df_agend['id_reserva'] == reserva['id_reserva'], 'status'] = 'Aprovado'
					save_data('agendamentos', df_agend)
					st.rerun()
				if col_rejeitar.button("Rejeitar", key=f"sec_rej_{reserva['id_reserva']}"):
					df_agend.loc[df_agend['id_reserva'] == reserva['id_reserva'], 'status'] = 'Rejeitado'
					save_data('agendamentos', df_agend)
					st.rerun()

	with tab_trocas:
		st.subheader("Análise de Trocas de Salas")
		df_trocas = get_data('trocas')
		trocas_pendentes = df_trocas[df_trocas['status'] == 'Pendente']

		if trocas_pendentes.empty:
			st.info("Nenhuma solicitação de troca de sala pendente.")
		else:
			df_agend = get_data('agendamentos')
			for _, troca in trocas_pendentes.iterrows():
				reserva_1 = df_agend[df_agend['id_reserva'] == troca['id_reserva_1']].iloc[0]
				reserva_2 = df_agend[df_agend['id_reserva'] == troca['id_reserva_2']].iloc[0]
				st.write("---")
				st.write("🔄 **Solicitação de Troca**")
				st.write(
					f"**Reserva 1:** Sala {reserva_1['nome_sala']} "
					f"({reserva_1['data']} - {reserva_1['turno']}) - Prof. {reserva_1['professor']}"
				)
				st.write(
					f"**Reserva 2:** Sala {reserva_2['nome_sala']} "
					f"({reserva_2['data']} - {reserva_2['turno']}) - Prof. {reserva_2['professor']}"
				)

				col_aprovar, col_rejeitar = st.columns(2)
				if col_aprovar.button("Aprovar Troca", key=f"sec_t_apr_{troca['id_troca']}"):
					df_agend.loc[df_agend['id_reserva'] == troca['id_reserva_1'], 'nome_sala'] = reserva_2['nome_sala']
					df_agend.loc[df_agend['id_reserva'] == troca['id_reserva_2'], 'nome_sala'] = reserva_1['nome_sala']
					df_trocas.loc[df_trocas['id_troca'] == troca['id_troca'], 'status'] = 'Aprovado'
					save_data('agendamentos', df_agend)
					save_data('trocas', df_trocas)
					st.rerun()
				if col_rejeitar.button("Rejeitar Troca", key=f"sec_t_rej_{troca['id_troca']}"):
					df_trocas.loc[df_trocas['id_troca'] == troca['id_troca'], 'status'] = 'Rejeitado'
					save_data('trocas', df_trocas)
					st.rerun()

	with tab_historico:
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
			for _, troca in trocas_processadas.iterrows():
				reserva_1 = reservas_por_id.loc[troca['id_reserva_1']]
				reserva_2 = reservas_por_id.loc[troca['id_reserva_2']]
				historico_trocas.append({
					'Professor 1': reserva_1['professor'],
					'Professor 2': reserva_2['professor'],
					'Sala 1': reserva_1['nome_sala'],
					'Sala 2': reserva_2['nome_sala'],
					'Data Sala 1': reserva_1['data'],
					'Data Sala 2': reserva_2['data'],
					'Status': troca['status'],
				})

			st.dataframe(
				pd.DataFrame(historico_trocas),
				use_container_width=True,
				hide_index=True,
			)

	with tab_professores:
		st.subheader("Gerenciar Professores")
		with st.form("form_professor_secretario"):
			nome_professor = st.text_input("Nome do Professor")
			senha_professor = st.text_input("Definir Senha", type="password")
			cadastrar = st.form_submit_button("Cadastrar Professor", type="primary")

			if cadastrar:
				if not nome_professor.strip() or not senha_professor:
					st.error("Informe um usuário e uma senha.")
				elif add_user(nome_professor.strip(), senha_professor, "Professor", st.session_state['usuario']):
					st.success("Professor cadastrado com sucesso.")
					st.rerun()
				else:
					st.error("Usuário já existe ou você não tem permissão para esta ação.")

		professores = get_data('usuarios')
		professores = professores[professores['tipo'] == 'Professor']
		if professores.empty:
			st.info("Nenhum professor cadastrado.")
		else:
			for _, professor in professores.iterrows():
				col_nome, col_acao = st.columns([5, 1])
				col_nome.write(f"{professor['nome']} ({professor['status']})")
				if col_acao.button("Excluir", key=f"secretario_excluir_{professor['nome']}"):
					if delete_user(professor['nome'], st.session_state['usuario']):
						st.success("Professor excluído com sucesso.")
						st.rerun()

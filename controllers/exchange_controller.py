import pandas as pd
import uuid

from models.db_manager import get_data, save_data, troca_invalida, troca_ja_registrada


def create_exchange(id_reserva_1, id_reserva_2, reserva_1, reserva_2):
    if troca_invalida(reserva_1, reserva_2):
        return 'invalida'

    trocas = get_data('trocas')
    if troca_ja_registrada(id_reserva_1, id_reserva_2, trocas):
        return 'duplicada'

    nova_troca = pd.DataFrame([{
        'id_troca': str(uuid.uuid4()),
        'id_reserva_1': id_reserva_1,
        'id_reserva_2': id_reserva_2,
        'status': 'Pendente'
    }])
    save_data('trocas', pd.concat([trocas, nova_troca], ignore_index=True))
    return 'criada'


def update_exchange_status(id_troca, status):
    trocas = get_data('trocas')
    trocas.loc[trocas['id_troca'] == id_troca, 'status'] = status
    save_data('trocas', trocas)


def approve_exchange(troca, reserva_1, reserva_2):
    if troca_invalida(reserva_1, reserva_2):
        return 'invalida'

    trocas = get_data('trocas')
    if troca_ja_registrada(troca['id_reserva_1'], troca['id_reserva_2'], trocas):
        return 'duplicada'

    agendamentos = get_data('agendamentos')
    agendamentos.loc[agendamentos['id_reserva'] == troca['id_reserva_1'], 'nome_sala'] = reserva_2['nome_sala']
    agendamentos.loc[agendamentos['id_reserva'] == troca['id_reserva_2'], 'nome_sala'] = reserva_1['nome_sala']
    trocas.loc[trocas['id_troca'] == troca['id_troca'], 'status'] = 'Aprovado'
    save_data('agendamentos', agendamentos)
    save_data('trocas', trocas)
    return 'aprovada'

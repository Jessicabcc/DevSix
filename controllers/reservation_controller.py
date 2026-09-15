import pandas as pd
import uuid

from models.db_manager import get_data, save_data


def create_reservation(nome_sala, data_reserva, turno, professor):
    agendamentos = get_data('agendamentos')
    data_texto = str(data_reserva)
    ocupado = agendamentos[
        (agendamentos['nome_sala'] == nome_sala) &
        (agendamentos['data'] == data_texto) &
        (agendamentos['turno'] == turno) &
        (agendamentos['status'].isin(['Aprovado', 'Pendente']))
    ]
    if not ocupado.empty:
        return False

    nova_reserva = pd.DataFrame([{
        'id_reserva': str(uuid.uuid4()),
        'nome_sala': nome_sala,
        'data': data_texto,
        'turno': turno,
        'professor': professor,
        'status': 'Pendente'
    }])
    save_data('agendamentos', pd.concat([agendamentos, nova_reserva], ignore_index=True))
    return True


def update_reservation_status(id_reserva, status):
    agendamentos = get_data('agendamentos')
    agendamentos.loc[agendamentos['id_reserva'] == id_reserva, 'status'] = status
    save_data('agendamentos', agendamentos)

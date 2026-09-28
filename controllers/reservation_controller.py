from datetime import datetime
import uuid

import pandas as pd

from models.db_manager import get_data, save_data


def create_reservation(nome_sala, data_reserva, turno, professor, email="", predio=""):
    agendamentos = get_data('agendamentos')
    salas = get_data("salas")
    sala = salas[salas["nome_sala"] == nome_sala]
    if predio:
        sala = sala[sala["predio"] == predio]
    if sala.empty or str(sala.iloc[0]["status"]) == "Bloqueada":
        return False
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
        'predio': predio or sala.iloc[0]["predio"],
        'nome_sala': nome_sala,
        'data': data_texto,
        'turno': turno,
        'professor': professor,
        'email': email,
        'status': 'Pendente',
        'solicitado_em': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'responsavel': "",
        'decidido_em': "",
    }])
    save_data('agendamentos', pd.concat([agendamentos, nova_reserva], ignore_index=True))
    return True


def update_reservation_status(id_reserva, status, responsavel="", tipo_responsavel=""):
    agendamentos = get_data('agendamentos')
    alvo = agendamentos["id_reserva"] == id_reserva
    if not alvo.any():
        return False
    agendamentos.loc[alvo, "status"] = status
    agendamentos.loc[alvo, "responsavel"] = responsavel
    agendamentos.loc[alvo, "decidido_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data('agendamentos', agendamentos)
    from models.db_manager import registrar_historico
    registrar_historico(f"Reserva {status.lower()}", f"Reserva {id_reserva}", responsavel, tipo_responsavel)
    return True

import pandas as pd
import uuid

from models.db_manager import get_data, save_data, troca_invalida, troca_ja_registrada


def create_exchange(id_reserva_1, id_reserva_2, reserva_1, reserva_2):
    if troca_invalida(reserva_1, reserva_2):
        return 'invalida'
    if reserva_1.get("status") != "Aprovado" or reserva_2.get("status") != "Aprovado":
        return "invalida"

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
    proposta = (trocas["id_troca"] == troca["id_troca"]) & (trocas["status"] == "Pendente")
    if not proposta.any():
        return "indisponivel"

    agendamentos = get_data('agendamentos')
    primeira = agendamentos["id_reserva"] == troca["id_reserva_1"]
    segunda = agendamentos["id_reserva"] == troca["id_reserva_2"]
    if not primeira.any() or not segunda.any():
        return "invalida"
    professor_1, email_1 = reserva_1.get("professor", ""), reserva_1.get("email", "")
    professor_2, email_2 = reserva_2.get("professor", ""), reserva_2.get("email", "")
    agendamentos.loc[primeira, ["professor", "email"]] = [professor_2, email_2]
    agendamentos.loc[segunda, ["professor", "email"]] = [professor_1, email_1]
    trocas.loc[trocas['id_troca'] == troca['id_troca'], 'status'] = 'Aceito'
    save_data('agendamentos', agendamentos)
    save_data('trocas', trocas)
    from models.db_manager import registrar_historico
    registrar_historico("Troca aceita", f"Troca {troca['id_troca']} aceita pela administração")
    return 'aprovada'


def respond_to_exchange(id_troca, resposta, usuario):
    trocas = get_data("trocas")
    achada = trocas[(trocas["id_troca"] == id_troca) & (trocas["status"] == "Pendente")]
    if achada.empty:
        return "indisponivel"
    troca = achada.iloc[0]
    agendamentos = get_data("agendamentos")
    alvo = agendamentos[agendamentos["id_reserva"] == troca["id_reserva_1"]]
    origem = agendamentos[agendamentos["id_reserva"] == troca["id_reserva_2"]]
    if alvo.empty or origem.empty or alvo.iloc[0]["professor"] != usuario:
        return "sem_permissao"
    if resposta == "aceitar":
        resultado = approve_exchange(troca, alvo.iloc[0].to_dict(), origem.iloc[0].to_dict())
        if resultado == "aprovada":
            return "aceita"
        return resultado
    update_exchange_status(id_troca, "Rejeitado")
    from models.db_manager import registrar_historico
    registrar_historico("Troca rejeitada", f"Troca {id_troca} rejeitada pelo destinatário", usuario, "Professor")
    return "rejeitada"

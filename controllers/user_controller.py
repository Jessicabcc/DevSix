from models.db_manager import add_user, delete_user


def create_user(nome, senha, tipo, criado_por):
    if not nome.strip() or not senha:
        return False
    return add_user(nome.strip(), senha, tipo, criado_por)


def remove_user(nome, excluido_por):
    return delete_user(nome, excluido_por)

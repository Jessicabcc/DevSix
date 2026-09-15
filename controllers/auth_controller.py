from models.db_manager import get_data, set_user_status


def authenticate(usuario, senha):
    usuarios = get_data('usuarios')
    usuario_encontrado = usuarios[(usuarios['nome'] == usuario) & (usuarios['senha'] == senha)]
    if usuario_encontrado.empty:
        return None
    return usuario_encontrado.iloc[0]['tipo']


def login(usuario, tipo):
    set_user_status(usuario, 'Online')
    return {'logged_in': True, 'usuario': usuario, 'tipo': tipo}


def logout(usuario):
    set_user_status(usuario, 'Offline')
    return {'logged_in': False, 'usuario': '', 'tipo': ''}

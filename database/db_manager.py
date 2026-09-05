import pandas as pd
import os
from datetime import datetime

# Caminhos dos arquivos
DB_PATH = 'database/'
SUPORTE_TI = 'Suporte.ti'
FILES = {
    'usuarios': f'{DB_PATH}usuarios.csv',
    'salas': f'{DB_PATH}salas.csv',
    'agendamentos': f'{DB_PATH}agendamentos.csv',
    'trocas': f'{DB_PATH}trocas.csv'
}

def init_db():
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
        
    if not os.path.exists(FILES['usuarios']):
        pd.DataFrame(columns=['nome', 'senha', 'tipo', 'status']).to_csv(FILES['usuarios'], index=False)
        # Admin padrão
        add_user('Suporte.ti', 'admin123', 'Administrador')
    else:
        try:
            usuarios = pd.read_csv(FILES['usuarios'])
            if 'admin' in usuarios['nome'].values and SUPORTE_TI not in usuarios['nome'].values:
                usuarios.loc[usuarios['nome'] == 'admin', 'nome'] = SUPORTE_TI
                save_data('usuarios', usuarios)
        except pd.errors.EmptyDataError:
            pd.DataFrame(columns=['nome', 'senha', 'tipo', 'status']).to_csv(FILES['usuarios'], index=False)
            add_user('Suporte.ti', 'admin123', 'Administrador')
        
    if not os.path.exists(FILES['salas']):
        pd.DataFrame(columns=['id_sala', 'predio', 'nome_sala', 'observacoes']).to_csv(FILES['salas'], index=False)
        
    if not os.path.exists(FILES['agendamentos']):
        pd.DataFrame(columns=['id_reserva', 'nome_sala', 'data', 'turno', 'professor', 'status']).to_csv(FILES['agendamentos'], index=False)
        
    if not os.path.exists(FILES['trocas']):
        pd.DataFrame(columns=['id_troca', 'id_reserva_1', 'id_reserva_2', 'status']).to_csv(FILES['trocas'], index=False)

def get_data(table):
    return pd.read_csv(FILES[table])

def save_data(table, df):
    df.to_csv(FILES[table], index=False)

def add_user(nome, senha, tipo, criado_por=None):
    df = get_data('usuarios')
    if tipo == 'Secretário' and criado_por != SUPORTE_TI:
        return False
    if tipo == 'Professor' and criado_por is not None:
        criador = df[df['nome'] == criado_por]
        if criador.empty or criador.iloc[0]['tipo'] not in ['Administrador', 'Secretário']:
            return False

    if nome not in df['nome'].values:
        novo = pd.DataFrame([{'nome': nome, 'senha': senha, 'tipo': tipo, 'status': 'Offline'}])
        df = pd.concat([df, novo], ignore_index=True)
        save_data('usuarios', df)
        return True
    return False

def delete_user(nome, excluido_por=None):
    df = get_data('usuarios')
    usuario = df[df['nome'] == nome]
    if usuario.empty or usuario.iloc[0]['tipo'] == 'Administrador':
        return False
    if excluido_por is not None:
        excluidor = df[df['nome'] == excluido_por]
        if excluidor.empty:
            return False
        if excluidor.iloc[0]['tipo'] == 'Secretário' and usuario.iloc[0]['tipo'] != 'Professor':
            return False
        if excluidor.iloc[0]['tipo'] not in ['Administrador', 'Secretário']:
            return False

    save_data('usuarios', df[df['nome'] != nome])
    return True

def set_user_status(nome, status):
    df = get_data('usuarios')
    df.loc[df['nome'] == nome, 'status'] = status
    save_data('usuarios', df)
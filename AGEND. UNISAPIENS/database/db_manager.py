import pandas as pd
import os
from datetime import datetime

# Caminhos dos arquivos
DB_PATH = 'database/'
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
        add_user('admin', 'admin123', 'Administrador')
        
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

def add_user(nome, senha, tipo):
    df = get_data('usuarios')
    if nome not in df['nome'].values:
        novo = pd.DataFrame([{'nome': nome, 'senha': senha, 'tipo': tipo, 'status': 'Offline'}])
        df = pd.concat([df, novo], ignore_index=True)
        save_data('usuarios', df)
        return True
    return False

def set_user_status(nome, status):
    df = get_data('usuarios')
    df.loc[df['nome'] == nome, 'status'] = status
    save_data('usuarios', df)
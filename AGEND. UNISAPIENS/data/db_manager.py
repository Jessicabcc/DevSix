import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'csv_files')
FILES = {
    'usuarios': os.path.join(DB_PATH, 'usuarios.csv'),
    'salas': os.path.join(DB_PATH, 'salas.csv'),
    'agendamentos': os.path.join(DB_PATH, 'agendamentos.csv'),
    'trocas': os.path.join(DB_PATH, 'trocas.csv')
}

def init_db():
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
        
    if not os.path.exists(FILES['usuarios']):
        pd.DataFrame(columns=['nome', 'senha', 'tipo', 'status']).to_csv(FILES['usuarios'], index=False)
        add_user('admin', 'admin123', 'Administrador')
        
    if not os.path.exists(FILES['salas']):
        pd.DataFrame(columns=['id_sala', 'categoria', 'nome_sala', 'capacidade', 'projetor', 'observacoes']).to_csv(FILES['salas'], index=False)
        
    if not os.path.exists(FILES['agendamentos']):
        pd.DataFrame(columns=['id_reserva', 'nome_sala', 'data', 'turno', 'professor', 'status']).to_csv(FILES['agendamentos'], index=False)
        
    if not os.path.exists(FILES['trocas']):
        pd.DataFrame(columns=['id_troca', 'id_reserva_origem', 'id_reserva_alvo', 'prof_origem', 'prof_alvo', 'status']).to_csv(FILES['trocas'], index=False)

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
    if not df.empty and nome in df['nome'].values:
        df.loc[df['nome'] == nome, 'status'] = status
        save_data('usuarios', df)
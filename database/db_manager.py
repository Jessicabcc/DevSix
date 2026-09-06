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

REQUIRED_COLUMNS = {
    'usuarios': ['nome', 'senha', 'tipo', 'status'],
    'salas': ['id_sala', 'predio', 'nome_sala', 'observacoes'],
    'agendamentos': ['id_reserva', 'nome_sala', 'data', 'turno', 'professor', 'status'],
    'trocas': ['id_troca', 'id_reserva_1', 'id_reserva_2', 'status'],
}

COLUMN_ALIASES = {
    'agendamentos': {'statusj': 'status'}
}


def normalize_table(table, df):
    if df is None or df.empty and table not in FILES:
        return df

    aliases = COLUMN_ALIASES.get(table, {})
    if aliases:
        df = df.rename(columns=aliases)

    required = REQUIRED_COLUMNS.get(table, [])
    for column in required:
        if column not in df.columns:
            if column == 'status' and table == 'agendamentos':
                df[column] = 'Pendente'
            else:
                df[column] = ''

    return df


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

def _deduplicate_trocas(df):
    if df.empty or 'id_reserva_1' not in df.columns or 'id_reserva_2' not in df.columns:
        return df

    registros = []
    vistos = set()
    for registro in reversed(df.to_dict('records')):
        chave = tuple(sorted([
            str(registro.get('id_reserva_1', '')),
            str(registro.get('id_reserva_2', ''))
        ]))
        if chave in vistos:
            continue
        vistos.add(chave)
        registros.append(registro)

    registros.reverse()
    return pd.DataFrame(registros, columns=df.columns)


def troca_invalida(reserva_1, reserva_2):
    return (
        str(reserva_1.get('data', '')).strip() == str(reserva_2.get('data', '')).strip() and
        str(reserva_1.get('turno', '')).strip() == str(reserva_2.get('turno', '')).strip() and
        str(reserva_1.get('nome_sala', '')).strip() == str(reserva_2.get('nome_sala', '')).strip()
    )


def troca_ja_registrada(id_reserva_1, id_reserva_2, df_trocas=None):
    if df_trocas is None:
        df_trocas = get_data('trocas')

    if df_trocas.empty:
        return False

    id1 = str(id_reserva_1)
    id2 = str(id_reserva_2)
    par = tuple(sorted([id1, id2]))

    for _, troca in df_trocas.iterrows():
        atual = tuple(sorted([str(troca.get('id_reserva_1', '')), str(troca.get('id_reserva_2', ''))]))
        if atual == par:
            return True

    return False


def get_data(table):
    df = pd.read_csv(FILES[table])
    df = normalize_table(table, df)
    if table == 'agendamentos' and 'status' in df.columns and 'statusj' in df.columns:
        df = df.drop(columns=['statusj'], errors='ignore')
    if table == 'trocas':
        df = _deduplicate_trocas(df)
    return df


def save_data(table, df):
    df = normalize_table(table, df)
    if table == 'trocas':
        df = _deduplicate_trocas(df)
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
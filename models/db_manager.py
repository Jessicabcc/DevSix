from datetime import datetime
from pathlib import Path
import uuid

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_DIR / "assets" / "data"
LEGACY_DIR = DB_DIR / "legacy"
DB_PATH = str(DB_DIR) + "/"
SUPORTE_TI = "Suporte.ti"
FILES = {
    "usuarios": DB_DIR / "usuarios.csv",
    "salas": DB_DIR / "salas.csv",
    "agendamentos": DB_DIR / "agendamentos.csv",
    "trocas": DB_DIR / "trocas.csv",
    "convites": DB_DIR / "convites.csv",
    "predios": DB_DIR / "predios.csv",
    "favoritos": DB_DIR / "favoritos.csv",
    "historico_alteracoes": DB_DIR / "historico_alteracoes.csv",
}

REQUIRED_COLUMNS = {
    "usuarios": ["nome", "email", "senha", "tipo", "status", "foto"],
    "salas": ["id_sala", "predio", "nome_sala", "observacoes", "categoria", "status"],
    "agendamentos": [
        "id_reserva", "predio", "nome_sala", "data", "turno", "professor",
        "email", "status", "solicitado_em", "responsavel", "decidido_em",
    ],
    "trocas": ["id_troca", "id_reserva_1", "id_reserva_2", "status"],
    "convites": ["token", "usado", "expiracao", "tipo_conta", "criado_por"],
    "predios": ["id_predio", "nome", "emoji"],
    "favoritos": ["professor", "id_sala"],
    "historico_alteracoes": ["data_hora", "usuario", "tipo_usuario", "acao", "detalhes"],
}

DEFAULTS = {
    "status": {
        "usuarios": "Offline",
        "salas": "Ativa",
        "agendamentos": "Pendente",
        "trocas": "Pendente",
    },
    "categoria": "Normal",
    "email": "",
    "foto": "",
    "observacoes": "",
    "solicitado_em": "",
    "responsavel": "",
    "decidido_em": "",
    "criado_por": "",
}

LEGACY_FILES = {
    "usuarios": "usuarios.csv",
    "salas": "salas.csv",
    "agendamentos": "agendamentos.csv",
    "trocas": "trocas_salas.csv",
    "convites": "convites.csv",
    "predios": "predios.csv",
    "favoritos": "favoritos.csv",
    "historico_alteracoes": "historico_alteracoes.csv",
}

IMPORT_KEYS = {
    "usuarios": ["nome"],
    "salas": ["id_sala"],
    "agendamentos": ["id_reserva"],
    "trocas": ["id_troca"],
    "convites": ["token"],
    "predios": ["id_predio"],
    "favoritos": ["professor", "id_sala"],
    "historico_alteracoes": ["data_hora", "usuario", "acao", "detalhes"],
}


def normalize_table(table, df):
    if table not in REQUIRED_COLUMNS:
        raise KeyError(f"Tabela desconhecida: {table}")
    if df is None:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS[table])
    aliases = {"statusj": "status"} if table == "agendamentos" else {}
    if aliases:
        df = df.rename(columns=aliases)
    for column in REQUIRED_COLUMNS[table]:
        if column not in df.columns:
            default = DEFAULTS.get(column, "")
            if column == "status":
                default = DEFAULTS["status"].get(table, "")
            df[column] = default
    return df[REQUIRED_COLUMNS[table]].fillna("")


def _read_csv(path, table):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS[table])
    return normalize_table(table, df)


def _import_legacy_data():
    marcador = DB_DIR / ".legacy_imported"
    if not LEGACY_DIR.exists():
        return

    arquivos = LEGACY_FILES.items()
    if marcador.exists():
        arquivos = [("historico_alteracoes", LEGACY_FILES["historico_alteracoes"])]

    for table, filename in arquivos:
        source_path = LEGACY_DIR / filename
        if not source_path.exists():
            continue
        try:
            legado = pd.read_csv(source_path, encoding="utf-8-sig", dtype=str).fillna("")
        except pd.errors.EmptyDataError:
            continue

        if table == "historico_alteracoes" and "data_hora" not in legado.columns:
            legado = pd.read_csv(
                source_path,
                header=None,
                names=REQUIRED_COLUMNS[table],
                encoding="utf-8-sig",
                dtype=str,
            ).fillna("")

        if table == "agendamentos" and "sala" in legado.columns:
            legado = legado.rename(columns={"sala": "nome_sala"})
        elif table == "trocas":
            legado = legado.rename(columns={
                "id_reserva_alvo": "id_reserva_1",
                "id_reserva_origem": "id_reserva_2",
                "status_troca": "status",
            })
        legado = normalize_table(table, legado)
        atual = _read_csv(FILES[table], table)
        chaves = IMPORT_KEYS[table]
        existentes = {
            tuple(str(valor).strip().casefold() for valor in registro)
            for registro in atual[chaves].itertuples(index=False, name=None)
        }
        novos = []
        for registro in legado.to_dict("records"):
            chave = tuple(str(registro.get(coluna, "")).strip().casefold() for coluna in chaves)
            if not any(chave) or chave in existentes:
                continue
            existentes.add(chave)
            novos.append(registro)
        if novos:
            atual = pd.concat([atual, pd.DataFrame(novos)], ignore_index=True)
        save_data(table, atual)

    marcador.write_text(datetime.now().isoformat(), encoding="utf-8")


def init_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    for table, path in FILES.items():
        if not path.exists():
            pd.DataFrame(columns=REQUIRED_COLUMNS[table]).to_csv(path, index=False, encoding="utf-8")
        else:
            try:
                columns = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()
            except pd.errors.EmptyDataError:
                columns = []
            if columns != REQUIRED_COLUMNS[table]:
                save_data(table, _read_csv(path, table))

    _import_legacy_data()

    salas = get_data("salas")
    predios = get_data("predios")
    existentes = set(predios["id_predio"].astype(str))
    faltantes = [
        str(predio)
        for predio in salas["predio"].dropna().unique()
        if str(predio).strip() and str(predio) not in existentes
    ]
    if faltantes:
        novos_predios = pd.DataFrame([
            {"id_predio": predio, "nome": predio, "emoji": "🏢"}
            for predio in faltantes
        ])
        save_data("predios", pd.concat([predios, novos_predios], ignore_index=True))

    usuarios = get_data("usuarios")
    if usuarios.empty:
        add_user(SUPORTE_TI, "admin123", "Administrador")

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
    df = _read_csv(FILES[table], table)
    if table == 'trocas':
        df = _deduplicate_trocas(df)
    return df


def save_data(table, df):
    df = normalize_table(table, df)
    if table == 'trocas':
        df = _deduplicate_trocas(df)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(FILES[table], index=False, encoding="utf-8")

def add_user(nome, senha, tipo, criado_por=None, email="", foto=""):
    from utils.password_utils import hash_password

    df = get_data("usuarios")
    nome = str(nome or "").strip()
    email = str(email or "").strip().casefold()
    tipos_validos = ("Professor", "Secretário", "Coordenador", "Administrador")
    if not nome or not senha or tipo not in tipos_validos:
        return False
    if df["nome"].str.strip().str.casefold().eq(nome.casefold()).any():
        return False
    if email and df["email"].str.strip().str.casefold().eq(email).any():
        return False

    criador = df[df["nome"].str.strip().str.casefold() == str(criado_por or "").strip().casefold()]
    papel_criador = criador.iloc[0]["tipo"] if not criador.empty else ""
    if tipo in ("Administrador", "Coordenador", "Secretário") and papel_criador != "Administrador":
        if not (tipo == "Administrador" and df.empty and criado_por is None):
            return False
    if tipo == "Professor" and criado_por is not None and papel_criador not in (
        "Administrador", "Coordenador", "Secretário"
    ):
        return False

    novo = pd.DataFrame([{
        "nome": nome,
        "email": email,
        "senha": hash_password(str(senha)),
        "tipo": tipo,
        "status": "Offline",
        "foto": foto,
    }])
    save_data("usuarios", pd.concat([df, novo], ignore_index=True))
    return True

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


def registrar_historico(acao, detalhes, usuario="Sistema", tipo_usuario=""):
    historico = get_data("historico_alteracoes")
    novo = pd.DataFrame([{
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario or "Sistema",
        "tipo_usuario": tipo_usuario or "",
        "acao": acao,
        "detalhes": detalhes,
    }])
    save_data("historico_alteracoes", pd.concat([historico, novo], ignore_index=True))
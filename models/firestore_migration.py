from datetime import datetime, timezone

import pandas as pd

from models.db_manager import (
    DB_DIR,
    FILES,
    IMPORT_KEYS,
    LEGACY_DIR,
    LEGACY_FILES,
    REQUIRED_COLUMNS,
    _read_csv,
    normalize_table,
)
from models.firestore_store import (
    MAX_BATCH_WRITES,
    MIGRATION_COLLECTION,
    MIGRATION_DOCUMENT,
    MIGRATION_SOURCE,
    build_firestore_documents,
)
from utils.firebase_utils import get_firestore_client


def _read_legacy_csv(path, table):
    try:
        legacy = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None

    if table == "historico_alteracoes" and "data_hora" not in legacy.columns:
        legacy = pd.read_csv(
            path,
            header=None,
            names=REQUIRED_COLUMNS[table],
            encoding="utf-8-sig",
            dtype=str,
        ).fillna("")
    elif table == "agendamentos" and "sala" in legacy.columns:
        legacy = legacy.rename(columns={"sala": "nome_sala"})
    elif table == "trocas":
        legacy = legacy.rename(columns={
            "id_reserva_alvo": "id_reserva_1",
            "id_reserva_origem": "id_reserva_2",
            "status_troca": "status",
        })

    return normalize_table(table, legacy)


def _load_table(table):
    current = _read_csv(FILES[table], table)
    if not LEGACY_DIR.exists():
        return current

    legacy_tables = list(LEGACY_FILES.items())
    if (DB_DIR / ".legacy_imported").exists():
        legacy_tables = [
            ("historico_alteracoes", LEGACY_FILES["historico_alteracoes"])
        ]

    for legacy_table, filename in legacy_tables:
        if legacy_table != table:
            continue

        legacy = _read_legacy_csv(LEGACY_DIR / filename, table)
        if legacy is None:
            continue

        keys = IMPORT_KEYS[table]
        existing = {
            tuple(str(value).strip().casefold() for value in row)
            for row in current[keys].itertuples(index=False, name=None)
        }
        new_records = []
        for record in legacy.to_dict("records"):
            key = tuple(
                str(record.get(column, "")).strip().casefold()
                for column in keys
            )
            if not any(key) or key in existing:
                continue
            existing.add(key)
            new_records.append(record)

        if new_records:
            current = pd.concat([current, pd.DataFrame(new_records)], ignore_index=True)

    return normalize_table(table, current)


def _expected_documents(table):
    records = _load_table(table).to_dict("records")
    documents = build_firestore_documents(table, records, IMPORT_KEYS[table])
    return {
        document_id: {
            **document,
            "__migration_source": MIGRATION_SOURCE,
        }
        for document_id, document in documents
    }


def _write_documents(client, collection, documents):
    items = list(documents.items())
    for offset in range(0, len(items), MAX_BATCH_WRITES):
        batch = client.batch()
        for document_id, data in items[offset:offset + MAX_BATCH_WRITES]:
            batch.set(collection.document(document_id), data)
        batch.commit()


def migrate_csv_to_firestore(client=None):
    client = client or get_firestore_client()
    migration_ref = client.collection(MIGRATION_COLLECTION).document(MIGRATION_DOCUMENT)
    migration_snapshot = migration_ref.get()
    migration_data = migration_snapshot.to_dict() if migration_snapshot.exists else None
    if migration_data and migration_data.get("completed"):
        return migration_data.get("counts", {})

    expected_by_table = {
        table: _expected_documents(table)
        for table in REQUIRED_COLUMNS
    }

    for table, expected in expected_by_table.items():
        collection = client.collection(table)
        existing = {snapshot.id: snapshot.to_dict() for snapshot in collection.stream()}
        unexpected_ids = set(existing) - set(expected)
        if unexpected_ids:
            raise RuntimeError(
                f"A coleção {table!r} já contém documentos fora desta migração; "
                "nenhum dado foi alterado."
            )

        for document_id, data in existing.items():
            if data != expected[document_id]:
                raise RuntimeError(
                    f"O documento {table}/{document_id} não corresponde aos CSVs; "
                    "nenhum dado foi alterado."
                )

    for table, expected in expected_by_table.items():
        _write_documents(client, client.collection(table), expected)

    counts = {}
    for table, expected in expected_by_table.items():
        actual = {
            snapshot.id: snapshot.to_dict()
            for snapshot in client.collection(table).stream()
        }
        if actual != expected:
            raise RuntimeError(
                f"A verificação da coleção {table!r} falhou; "
                "a migração não foi marcada como concluída."
            )
        counts[table] = len(actual)

    migration_ref.set({
        "completed": True,
        "source": MIGRATION_SOURCE,
        "counts": counts,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    return counts


if __name__ == "__main__":
    migrated_counts = migrate_csv_to_firestore()
    for collection, count in migrated_counts.items():
        print(f"{collection}: {count} documento(s)")

import hashlib
import json


MIGRATION_COLLECTION = "migration_metadata"
MIGRATION_DOCUMENT = "csv_to_firestore_v1"
MIGRATION_SOURCE = "csv_migration_v1"
MAX_BATCH_WRITES = 450


def build_firestore_documents(table, records, key_columns):
    occurrences = {}
    documents = []

    for row_order, record in enumerate(records):
        identity = tuple(str(record.get(column, "") or "") for column in key_columns)
        if not any(identity):
            identity = tuple(
                f"{column}={value}"
                for column, value in sorted(record.items())
            )

        payload = json.dumps(
            [table, identity],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        occurrence = occurrences.get(digest, 0)
        occurrences[digest] = occurrence + 1
        document_id = digest if occurrence == 0 else f"{digest}-{occurrence}"

        document = dict(record)
        document["__row_order"] = row_order
        documents.append((document_id, document))

    return documents

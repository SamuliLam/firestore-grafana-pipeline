import os

from google.cloud import firestore
from src.db import insert_sensor_rows, get_oldest_timestamp_from_db, get_newest_timestamp_from_db
from src.SensorDataParser import SensorDataParser
from src.utils.sync_status import sync_status

# Firestore client
project_id = os.getenv("GCP_PROJECT_ID")
CLIENT = None


def get_firestore_client():
    global CLIENT
    if CLIENT is None:
        try:
            CLIENT = firestore.Client(project=project_id)
        except Exception as e:
            print(f"Failed to initialize Firestore client: {e}")
            return None
    return CLIENT


# Firestore collections to fetch history from
COLLECTIONS = os.getenv("FIRESTORE_COLLECTIONS", "").split(",")


def sync_firestore_to_timescale():
    sync_status["state"] = "running"
    sync_status["error"] = None

    client = get_firestore_client()
    if not client:
        sync_status["state"] = "failed"
        sync_status["error"] = "Firestore client not initialized (check credentials)"
        print("Firestore client initialization failed. Skipping sync.")
        return

    try:
        for collection_name in COLLECTIONS:
            newest_ts = get_newest_timestamp_from_db(collection_name)
            oldest_ts = get_oldest_timestamp_from_db(collection_name)
            parser = SensorDataParser(collection_name)

            query = client.collection(collection_name)
            if newest_ts:
                query = query.where("timestamp", ">", newest_ts)

            new_docs = query.stream()
            process_and_batch_save(new_docs, parser)

            if oldest_ts:
                print(f"Checking for history older than {oldest_ts}...")
                history_docs = client.collection(collection_name) \
                    .where("timestamp", "<", oldest_ts) \
                    .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                    .stream()
                process_and_batch_save(history_docs, parser)

        sync_status["state"] = "success"
    except Exception as e:
        sync_status["state"] = "failed"
        sync_status["error"] = str(e)
        print(f"Synchronization failed: {e}")
    finally:
        print("Synchronization process completed.")


def process_and_batch_save(docs, parser):
    current_chunk = []
    chunk_limit = 20000
    total_processed = 0

    print("Starting stream processing...")

    for doc in docs:
        rows = parser.process_raw_sensor_data(doc.to_dict())
        if rows:
            current_chunk.extend(rows)

        if len(current_chunk) >= chunk_limit:
            save_now(current_chunk)
            total_processed += len(current_chunk)
            current_chunk = []

    if current_chunk:
        save_now(current_chunk)
        total_processed += len(current_chunk)

    print(f"Sync complete! Total rows processed: {total_processed}")


def save_now(rows_to_save):
    """Apufunktio lajitteluun ja tallennukseen."""
    print(f"Sorting and saving {len(rows_to_save)} rows...")
    rows_to_save.sort(key=lambda x: x['timestamp'])

    for i in range(0, len(rows_to_save), 5000):
        batch = rows_to_save[i:i + 5000]
        insert_sensor_rows(batch)
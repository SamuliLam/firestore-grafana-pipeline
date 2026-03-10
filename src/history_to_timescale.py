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


def get_all_firestore_project_ids():
    client = get_firestore_client()
    project_docs = client.collection("projects").list_documents()
    project_ids = [doc.id for doc in project_docs]
    print(f"Discovery found {len(project_ids)} projects in Firestore: {project_ids}")
    return project_ids


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
        project_ids = get_all_firestore_project_ids()

        for pid in project_ids:

            newest_ts = get_newest_timestamp_from_db(pid)
            oldest_ts = get_oldest_timestamp_from_db(pid)

            parser = SensorDataParser(pid)

            query_base = client.collection_group("readings").where("project_id", "==", pid)

            new_query = query_base
            if newest_ts:
                new_query = new_query.where("timestamp", ">", newest_ts)

            print(f"Fetching new records for {pid}...")
            process_and_batch_save(new_query.stream(), parser, pid)

            if oldest_ts:
                print(f"Checking for older history for {pid} (before {oldest_ts})...")
                hist_query = query_base.where("timestamp", "<", oldest_ts) \
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                process_and_batch_save(hist_query.stream(), parser, pid)

        sync_status["state"] = "success"
    except Exception as e:
        sync_status["state"] = "failed"
        sync_status["error"] = str(e)
        print(f"Synchronization failed: {e}")
    finally:
        print("Synchronization process completed.")


def process_and_batch_save(docs, parser, project_id):
    current_chunk = []
    total_processed = 0

    for doc in docs:
        raw_data = doc.to_dict()
        rows = parser.process_raw_sensor_data(raw_data)

        if rows:
            for row in rows:
                row["project_id"] = project_id
            current_chunk.extend(rows)

        if len(current_chunk) >= 5000:
            save_now(current_chunk)
            total_processed += len(current_chunk)
            current_chunk = []

    if current_chunk:
        save_now(current_chunk)
        total_processed += len(current_chunk)

    if total_processed > 0:
        print(f"Successfully synced {total_processed} rows for project {project_id}")


def save_now(rows_to_save):
    print(f"Sorting and saving {len(rows_to_save)} rows...")
    rows_to_save.sort(key=lambda x: x['timestamp'])

    for i in range(0, len(rows_to_save), 5000):
        batch = rows_to_save[i:i + 5000]
        insert_sensor_rows(batch)

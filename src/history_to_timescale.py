import os

from google.cloud import firestore
from src.db import insert_sensor_rows, SensorData, get_oldest_collection_timestamp_from_db
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
            oldest_ts = get_oldest_collection_timestamp_from_db(collection_name)
            if oldest_ts:
                print(f"Fetching documents older than {oldest_ts} from collection: {collection_name}")
                docs = client.collection(collection_name).where("timestamp", "<", oldest_ts).stream()
            else:
                print(f"Fetching latest documents from collection: {collection_name}")
                docs = client.collection(collection_name).stream()

            parser = SensorDataParser(collection_name)
            for doc in docs:
                print(f"Parsing collection: {collection_name}")
                rows = parser.process_raw_sensor_data(doc.to_dict())
                if rows:
                    insert_sensor_rows(SensorData, rows)
                    print(f"Saved ({len(rows)} rows) to document {doc.id}")

        sync_status["state"] = "success"
    except Exception as e:
        sync_status["state"] = "failed"
        sync_status["error"] = str(e)
        print(f"Synchronization failed: {e}")
    finally:
        print("Synchronization process completed.")
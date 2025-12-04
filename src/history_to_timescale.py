from google.cloud import firestore
from src.db import (
    insert_sensor_rows,
    SensorData,
    get_oldest_collection_timestamp_from_db,
)
from src.utils.SensorDataParser import SensorDataParser
from src.utils.sync_status import sync_status


# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections to fetch history from
COLLECTIONS = ["viherpysakki", "ymparistomoduuli", "suvilahti"]


def sync_firestore_to_timescale():
    sync_status["state"] = "running"
    sync_status["error"] = None

    try:
        for collection_name in COLLECTIONS:
            oldest_ts = get_oldest_collection_timestamp_from_db(collection_name)
            if oldest_ts:
                print(
                    f"Fetching documents older than {oldest_ts} from collection: {collection_name}"
                )
                docs = (
                    CLIENT.collection(collection_name)
                    .where("timestamp", "<", oldest_ts)
                    .limit(50)
                    .stream()
                )
            else:
                print(f"Fetching latest documents from collection: {collection_name}")
                docs = CLIENT.collection(collection_name).limit(50).stream()

            parser = SensorDataParser(collection_name)
            for doc in docs:
                print(f"Parsing collection: {collection_name}")
                rows = parser.parse_sensor_data(doc.to_dict())
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

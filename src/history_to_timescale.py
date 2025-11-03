from google.cloud import firestore
import json
from src.db import insert_sensor_rows, get_oldest_timestamp_from_db
from src.utils.normalizer import normalize_sensor_data

# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections
COLLECTIONS = ["ymparistomoduuli"]


def parse_firestore_document(doc_id: str, raw_data: dict):
    json_str = next(iter(raw_data.values()))

    try:
        data_as_dict = json.loads(json_str)
        print(f"Data as a dict in the f-document: {data_as_dict}")
    except json.JSONDecodeError:
        print(f"Error: the document's {doc_id} data was not acceptable JSON.")
        return []

    sensor_data = normalize_sensor_data(data_as_dict)
    return sensor_data


def sync_firestore_to_timescale():
    oldest_ts = get_oldest_timestamp_from_db()

    for collection_name in COLLECTIONS:
        #TODO remove comments when timestamp field gets added to sensor data
        # if oldest_ts:
        #     docs = CLIENT.collection(collection_name).where("timestamp", "<", oldest_ts).stream()
        # else:
        #     docs = CLIENT.collection(collection_name).stream()

        docs = CLIENT.collection(collection_name).limit(20).stream()

        for doc in docs:
            rows = parse_firestore_document(doc.id, doc.to_dict())
            print("No data to insert! The document contained missing values.")
            if rows:
                print(f"sensordata to be inserted: {rows}")
                insert_sensor_rows(rows)
                print(f"Saved ({len(rows)} rows) to document {doc.id}")

    print("\n Synchronization done!")


if __name__ == "__main__":
    sync_firestore_to_timescale()

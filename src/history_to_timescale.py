from google.cloud import firestore
from src.db import insert_sensor_rows, get_oldest_timestamp_from_db, SensorData
from src.utils.normalizer import SensorParser

# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections to fetch history from
COLLECTIONS = ["viherpysakki"]


def sync_firestore_to_timescale():
    # oldest_ts = get_oldest_timestamp_from_db()

    for collection_name in COLLECTIONS:
        # TODO remove comments and limit(n) when timestamp field gets added to sensor data
        # if oldest_ts:
        #     docs = CLIENT.collection(collection_name).where("timestamp", "<", oldest_ts).stream()
        # else:
        #     docs = CLIENT.collection(collection_name).stream()

        docs = CLIENT.collection(collection_name).limit(5).stream()
        parser = SensorParser(collection_name)
        for doc in docs:
            rows = parser.parse_firestore_document(doc.to_dict())
            if rows:
                print(f"sensordata to be inserted: {rows}")
                insert_sensor_rows(SensorData, rows)
                print(f"Saved ({len(rows)} rows) to document {doc.id}")

    print("\n Synchronization done!")


if __name__ == "__main__":
    sync_firestore_to_timescale()

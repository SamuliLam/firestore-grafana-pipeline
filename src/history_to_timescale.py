from google.cloud import firestore
from src.db import insert_sensor_rows, get_oldest_timestamp_from_db, SensorData
from src.utils.SensorDataParser import SensorDataParser

# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections to fetch history from
COLLECTIONS = ["viherpysakki", "ymparistomoduuli"]


def sync_firestore_to_timescale():
    #oldest_ts = get_oldest_timestamp_from_db()

    for collection_name in COLLECTIONS:
        #if oldest_ts:
        #    docs = CLIENT.collection(collection_name).where("timestamp", "<", oldest_ts).limit(5).stream()
        #else:
        #    docs = CLIENT.collection(collection_name).limit(5).stream()

        docs = CLIENT.collection(collection_name).limit(50).stream()
        parser = SensorDataParser(collection_name)
        for doc in docs:
            print(f"Parsing collection: {collection_name}")
            rows = parser.parse_sensor_data(doc.to_dict())
            if rows:
                insert_sensor_rows(SensorData, rows)
                print(f"Saved ({len(rows)} rows) to document {doc.id}")

    print("\n Synchronization done!")


if __name__ == "__main__":
    sync_firestore_to_timescale()

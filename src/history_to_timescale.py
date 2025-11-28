from google.cloud import firestore
from src.db import insert_sensor_rows, SensorData, get_oldest_collection_timestamp_from_db
from src.utils.SensorDataParser import SensorDataParser

# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections to fetch history from
COLLECTIONS = ["viherpysakki", "ymparistomoduuli"]


def sync_firestore_to_timescale():

    for collection_name in COLLECTIONS:
        oldest_ts = get_oldest_collection_timestamp_from_db(collection_name)
        if oldest_ts:
            print(f"Fetching documents older than {oldest_ts} from collection: {collection_name}")
            docs = CLIENT.collection(collection_name).where("timestamp", "<", oldest_ts).limit(50).stream()
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

    print("\n Synchronization done!")


if __name__ == "__main__":
    sync_firestore_to_timescale()

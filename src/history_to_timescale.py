from google.cloud import firestore
from datetime import datetime
import json
from main import SensorData, insert_sensor_rows

# Firestore client
CLIENT = firestore.Client(project="prj-mtp-jaak-leht-ufl")

# Firestore collections
COLLECTIONS = ["ymparistomoduuli"]


def parse_firestore_document(doc_id: str, raw_data: dict):
    json_str = next(iter(raw_data.values()))

    try:
        data_dict = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Error: the document's {doc_id} data was not acceptable JSON.")
        return []

    rows = []
    for sensor_id, values in data_dict.items():
        row = SensorData(
            timestamp=datetime.strptime(doc_id, "%Y-%m-%d-%H:%M:%S"),
            sensor_id=sensor_id,
            zone=None,
            location=None,
            temperature=values.get("temperature", [None])[-1],
            humidity=values.get("humidity", [None])[-1]
        )
        rows.append(row)

    return rows


def sync_firestore_to_timescale():
    for collection_name in COLLECTIONS:
        print(f"\n Fetching data from Firestore-collection: {collection_name}")
        docs = CLIENT.collection(collection_name).limit(10).stream()

        for doc in docs:
            rows = parse_firestore_document(doc.id, doc.to_dict())
            if not rows:
                continue

            insert_sensor_rows(rows)
            print(f"Saved ({len(rows)} rows) to document {doc.id}")

    print("\n Synchronization done!")


if __name__ == "__main__":
    sync_firestore_to_timescale()

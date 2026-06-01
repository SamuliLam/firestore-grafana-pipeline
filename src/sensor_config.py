import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from google.cloud import firestore

TIMEZONE = ZoneInfo("Europe/Helsinki")
CLIENT = firestore.Client(project=os.getenv("GCP_PROJECT_ID"))


def update_sensor_config(sensor_id: str, config: dict):
    try:
        doc_ref = CLIENT.collection("sensor_config").document(sensor_id)
        doc_ref.set(config, merge=True)
        return True
    except Exception as e:
        print(f"Error updating Firestore config: {e}")
        return False


def get_unconfigured_sensor_ids_from_firestore():
    try:
        docs = CLIENT.collection("unconfigured_sensors").list_documents()
        return [doc.id for doc in docs]
    except Exception as e:
        print(f"Error fetching unknown sensors: {e}")
        return []


@firestore.transactional
def _move_reading_transaction(transaction, target_ref, source_ref, data_to_set):
    """
    Atomically sets the new document and deletes the old one.
    This ensures the move operation is all-or-nothing.
    """
    transaction.set(target_ref, data_to_set)
    transaction.delete(source_ref)


def trigger_backfill(sensor_id: str, config: dict):

    project_id = config.get("project_id")
    if not project_id or not isinstance(project_id, str):
        print(f"CRITICAL: Invalid or missing 'project_id' in config for sensor {sensor_id}. Aborting backfill to prevent data loss.")
        return 0

    mapping = config.get("mapping", {})
    ts_field = config.get("ts_field", "ts")

    unknown_readings_ref = CLIENT.collection("unconfigured_sensors") \
        .document(sensor_id) \
        .collection("readings")

    docs = unknown_readings_ref.stream()
    moved_count = 0

    for doc in docs:
        try:
            item = doc.to_dict()
            raw_payload = item.get("raw_data", {})
            received_at = item.get("received_at")

            raw_ts = raw_payload.get(ts_field)
            try:
                if raw_ts:
                    dt_utc = datetime.fromtimestamp(float(raw_ts), tz=timezone.utc)
                else:
                    dt_utc = received_at if received_at else datetime.now(timezone.utc)
            except Exception as e:
                print(f"Backfill timestamp error for doc {doc.id}: {e}")
                dt_utc = received_at if received_at else datetime.now(timezone.utc)

            measurements_map = {}
            processed_keys = {ts_field, "mac", "sensor_id", "id"}

            for raw_key, clean_name in mapping.items():
                if raw_key in raw_payload:
                    measurements_map[clean_name] = raw_payload[raw_key]
                    processed_keys.add(raw_key)

            extra = {k: v for k, v in raw_payload.items() if k not in processed_keys}

            final_data = {
                "sensor_id": sensor_id,
                "project_id": project_id,
                "timestamp": dt_utc,
                "measurements": measurements_map,
                "extra": extra,
                "backfilled": True,
                "original_received_at": received_at
            }

            dt_local = dt_utc.astimezone(TIMEZONE)

            base_id = dt_local.strftime("%Y-%m-%d-%H:%M:%S")
            final_doc_id = f"{base_id}_{doc.id[:5]}"

            target_ref = CLIENT.collection("projects").document(project_id) \
                .collection("sensors").document(sensor_id) \
                .collection("readings").document(final_doc_id)

            transaction = CLIENT.transaction()
            _move_reading_transaction(transaction, target_ref, doc.reference, final_data)
            moved_count += 1
        except Exception as e:
            print(f"CRITICAL: Failed to process and move document {doc.id} for sensor {sensor_id}. Error: {e}. Skipping document to prevent data loss.")

    return moved_count


def get_sensor_config(sensor_id: str):
    try:
        doc = CLIENT.collection("sensor_config").document(sensor_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching config: {e}")
        return None


def delete_sensor_config(sensor_id: str):
    try:
        doc_ref = CLIENT.collection("sensor_config").document(sensor_id)
        doc_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting Firestore config: {e}")
        return False

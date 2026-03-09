import os

from google.cloud import firestore

project_id = os.getenv("GCP_PROJECT_ID")

CLIENT = firestore.Client(project=project_id)


def update_sensor_config(sensor_id: str, config: dict):
    """Update sensor configuration in Firestore."""
    try:
        doc_ref = CLIENT.collection("sensor_configs").document(sensor_id)
        doc_ref.set(config, merge=True)
        return True
    except Exception as e:
        print(f"Failed to update sensor config for {sensor_id}: {e}")
        return False
import time
import random
from datetime import datetime, timedelta
from collections import defaultdict

from src.SensorDataParser import SensorDataParser
from src.history_to_timescale import process_and_batch_save


class MockDoc:
    def __init__(self, data):
        self._data = data
        self.id = f"mock_{random.getrandbits(32)}"

    def to_dict(self):
        return self._data


def generate_test_docs(amount=50000):
    test_docs = []

    interval_minutes = (30 * 24 * 60) / (amount / 9 if amount > 0 else 1)
    interval = timedelta(minutes=max(1, interval_minutes))

    base_time = datetime.now().replace(second=0, microsecond=0)

    print(f"Generating realistic mock documents for multiple projects over 30 days...")

    for i in range(amount):
        timestamp = base_time - (interval * (i // 9))
        sensor_index = i % 9
        sensor_id = f"sensor_{sensor_index}"

        doc_data = {
            "timestamp": timestamp.isoformat(),
            "sensor_id": sensor_id,
        }

        # --- MYYRMÄKI JOKI ---
        if sensor_index == 0:
            doc_data.update({"project_id": "myyrmäki_joki", "water_level_mm": round(random.uniform(500, 1500), 1)})
        elif sensor_index == 1:
            doc_data.update({"project_id": "myyrmäki_joki", "water_temperature": round(random.uniform(4.0, 18.0), 2)})
        elif sensor_index == 2:
            doc_data.update({"project_id": "myyrmäki_joki", "water_flow_m3s": round(random.uniform(0.1, 2.5), 3)})

        # --- MYLLYPURO NURMIKKO ---
        elif sensor_index == 3:
            doc_data.update(
                {"project_id": "myllypuro_nurmikko", "soil_moisture_pct": round(random.uniform(10.0, 40.0), 1)})
        elif sensor_index == 4:
            doc_data.update(
                {"project_id": "myllypuro_nurmikko", "soil_temperature": round(random.uniform(5.0, 15.0), 2)})
        elif sensor_index == 5:
            doc_data.update(
                {"project_id": "myllypuro_nurmikko", "soil_conductivity_mS": round(random.uniform(0.2, 1.5), 3)})

        # --- MYYRMÄKI KATUPUU ---
        elif sensor_index == 6:
            doc_data.update({"project_id": "myyrmäki_katupuu", "air_temperature": round(random.uniform(10.0, 25.0), 2)})
        elif sensor_index == 7:
            doc_data.update(
                {"project_id": "myyrmäki_katupuu", "air_pressure_kPa": round(random.uniform(99.0, 103.0), 2)})
        elif sensor_index == 8:
            doc_data.update(
                {"project_id": "myyrmäki_katupuu", "air_particulates_ppm": round(random.uniform(5.0, 30.0), 1)})

        test_docs.append(MockDoc(doc_data))

    return test_docs


def run_performance_test(amount=50000):
    print(f"\n--- Starting Generation for {amount} docs ---")
    docs = generate_test_docs(amount)

    docs_by_project = defaultdict(list)
    for doc in docs:
        pid = doc.to_dict().get("project_id", "unknown")
        docs_by_project[pid].append(doc)

    print(f"\n--- Starting Performance Test ---")
    start_time = time.time()

    total_synced = 0
    for project_id, project_docs in docs_by_project.items():
        print(f"Processing {len(project_docs)} docs for project: {project_id}")

        parser = SensorDataParser(project_id=project_id)

        process_and_batch_save(project_docs, parser, project_id)
        total_synced += len(project_docs)

    duration = time.time() - start_time
    print(f"\nFinished!")
    print(f"Generated and processed {total_synced} documents total.")
    print(f"Average speed: {total_synced / (duration if duration > 0 else 1):.0f} docs/second")


if __name__ == "__main__":
    run_performance_test(amount=10000)
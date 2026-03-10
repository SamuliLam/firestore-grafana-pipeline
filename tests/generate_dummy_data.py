import time
import random
from datetime import datetime, timedelta

from src.SensorDataParser import SensorDataParser
from src.history_to_timescale import process_and_batch_save


def generate_test_docs(amount=None):
    test_docs = []
    interval = timedelta(hours=12)
    base_time = datetime.now()

    print(f"Generating realistic mock documents (Unique sensors for unique metrics)...")

    for i in range(amount):
        timestamp = base_time - (interval * (i // 9))
        sensor_index = i % 9
        sensor_id = f"sensor_{sensor_index}"

        doc_data = {
            "timestamp": timestamp.isoformat(),
            "sensor_id": sensor_id,
        }


        # --- MYYRMÄKI JOKI (Vesi) ---
        if sensor_index == 0:
            doc_data.update({
                "project_id": "myyrmäki_joki",
                "water_level_mm": round(random.uniform(500, 1500), 1)
            })
        elif sensor_index == 1:
            doc_data.update({
                "project_id": "myyrmäki_joki",
                "water_temperature": round(random.uniform(4.0, 18.0), 2)
            })
        elif sensor_index == 2:
            doc_data.update({
                "project_id": "myyrmäki_joki",
                "water_flow_m3s": round(random.uniform(0.1, 2.5), 3),
                "water_conductivity_mS": round(random.uniform(1.0, 5.0), 3)
            })

        # --- MYLLYPURO NURMIKKO (Maaperä) ---
        elif sensor_index == 3:
            doc_data.update({
                "project_id": "myllypuro_nurmikko",
                "soil_moisture_pct": round(random.uniform(10.0, 40.0), 1)
            })
        elif sensor_index == 4:
            doc_data.update({
                "project_id": "myllypuro_nurmikko",
                "soil_temperature": round(random.uniform(5.0, 15.0), 2)
            })
        elif sensor_index == 5:
            doc_data.update({
                "project_id": "myllypuro_nurmikko",
                "soil_conductivity_mS": round(random.uniform(0.2, 1.5), 3),
                "soil_oxygen_pct": round(random.uniform(18.0, 21.0), 1)
            })

        # --- MYYRMÄKI KATUPUU (Ilma) ---
        elif sensor_index == 6:
            doc_data.update({
                "project_id": "myyrmäki_katupuu",
                "air_temperature": round(random.uniform(10.0, 25.0), 2),
                "air_humidity_pct": round(random.uniform(40.0, 80.0), 2)
            })
        elif sensor_index == 7:
            doc_data.update({
                "project_id": "myyrmäki_katupuu",
                "air_pressure_kPa": round(random.uniform(99.0, 103.0), 2)
            })
        elif sensor_index == 8:
            doc_data.update({
                "project_id": "myyrmäki_katupuu",
                "air_particulates_ppm": round(random.uniform(5.0, 30.0), 1)
            })

        class MockDoc:
            def __init__(self, data): self._data = data

            def to_dict(self): return self._data

        test_docs.append(MockDoc(doc_data))

    return test_docs

def run_performance_test(amount=50000):
    parser = SensorDataParser(project_id="test_collection")
    print(f"\n--- Starting Generation for {amount} docs ---")
    docs = generate_test_docs(amount)

    print(f"\n--- Starting Performance Test ---")
    start_time = time.time()

    process_and_batch_save(docs, parser)

    duration = time.time() - start_time
    print(f"Generated and processed {len(docs)} documents.")
    print(f"Average speed: {len(docs) / (duration if duration > 0 else 1):.0f} docs/second")


if __name__ == "__main__":
    run_performance_test(amount=50000)
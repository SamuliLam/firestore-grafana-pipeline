import time
import random
from datetime import datetime, timedelta

from src.SensorDataParser import SensorDataParser
from src.history_to_timescale import process_and_batch_save


def generate_test_docs(amount=None):
    """
    Luo dokumentteja dedikoiduilla sensoreilla:
    3 x Vesi, 3 x Maaperä, 3 x Ilma.
    """
    test_docs = []
    interval = timedelta(hours=12)
    base_time = datetime.now()

    print(f"Generating specialized mock documents (3 Water, 3 Soil, 3 Air sensors)...")

    for i in range(amount):
        # Lasketaan aikaleima (pysyy samana 9 sensorin ryhmissä)
        timestamp = base_time - (interval * (i // 9))

        # Määritetään sensorin tyyppi indeksin perusteella (0-8)
        sensor_index = i % 9
        sensor_id = f"sensor_{sensor_index}"

        # Pohjadokumentti
        doc_data = {
            "timestamp": timestamp.isoformat(),
            "sensor_id": sensor_id,
        }

        # Datan generointi sensorityypin mukaan
        if 0 <= sensor_index <= 2:
            # VESISENSORIT
            doc_data.update({
                "type": "water",
                "water_level_mm": round(random.uniform(100, 2000), 1),
                "water_temperature": round(random.uniform(4.0, 22.0), 2),
                "water_conductivity_mS": round(random.uniform(0.5, 10.0), 3),
                "water_flow_m3s": round(random.uniform(0.01, 5.0), 3)
            })

        elif 3 <= sensor_index <= 5:
            # MAAPERÄSENSORIT
            doc_data.update({
                "sensor_type": "soil",
                "soil_moisture_pct": round(random.uniform(5.0, 45.0), 1),
                "soil_temperature": round(random.uniform(2.0, 20.0), 2),
                "soil_conductivity_mS": round(random.uniform(0.1, 2.5), 3),
                "soil_oxygen_pct": round(random.uniform(15.0, 21.0), 1)
            })

        else:
            # ILMASENSORIT
            doc_data.update({
                "sensor_type": "air",
                "air_temperature": round(random.uniform(-10.0, 30.0), 2),
                "air_humidity_pct": round(random.uniform(20.0, 95.0), 2),
                "air_pressure_kPa": round(random.uniform(98.0, 104.0), 2),
                "air_particulates_ppm": round(random.uniform(0.0, 50.0), 1)
            })

        class MockDoc:
            def __init__(self, data): self._data = data

            def to_dict(self): return self._data

        test_docs.append(MockDoc(doc_data))

    return test_docs


def run_performance_test(amount=50000):
    # Tähän väliin tulisi Parserin alustus alkuperäisestä koodistasi
    parser = SensorDataParser(collection_name="test_collection")
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
import time
import random
from datetime import datetime, timedelta
from src.SensorDataParser import SensorDataParser
from src.history_to_timescale import process_and_batch_save

def generate_test_docs(amount=None):
    """
    Luo dokumentteja 12h välein 30 päivän ajalta.
    Jos amount annetaan, generointi pysäytetään siinä kohtaa.
    """
    test_docs = []

    interval = timedelta(hours=12)
    days = 30
    total_points = (24 // 12) * days  # = 60 datapistettä

    base_time = datetime.now()

    print(f"Generating time-series mock documents (12h interval, last 30 days)...")

    for i in range(total_points):
        if amount and i >= amount:
            break

        timestamp = base_time - interval * i

        doc_data = {
            "timestamp": timestamp.isoformat(),
            "temperature": str(round(random.uniform(10.0, 30.0), 2)),
            "humidity": str(round(random.uniform(10.0, 30.0), 2)),
            "sensor_id": f"sensor_{i % 3}",
        }

        class MockDoc:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data

        test_docs.append(MockDoc(doc_data))

    return test_docs



def run_performance_test(amount=100000):
    parser = SensorDataParser(collection_name="test_collection")
    docs = generate_test_docs(amount)

    print("\n--- Starting Performance Test ---")
    start_time = time.time()

    process_and_batch_save(docs, parser)

    end_time = time.time()
    duration = end_time - start_time

    print(f"\n--- Test Finished ---")
    print(f"Processed and saved {amount} documents in {duration:.2f} seconds")
    print(f"Average speed: {amount / duration:.0f} docs/second")


if __name__ == "__main__":

    run_performance_test(amount=50000)
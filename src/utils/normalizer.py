import datetime
from src.db import SensorData


def normalize_sensor_data(data_as_dict):
    list_of_sensor_data = []
    for sensor_id, values in data_as_dict.items():

        temperature = values.get("temperature", [])
        humidity = values.get("humidity", [])
        timestamps = values.get("timestamp")
        current_datetime = datetime.now()

        if not temperature or not humidity or not timestamps:
            continue

        row = SensorData(
            timestamp=current_datetime,
            sensor_id=sensor_id,
            zone=None,
            location=None,
            temperature=values.get("temperature", [None])[-1],
            humidity=values.get("humidity", [None])[-1]
        )
        list_of_sensor_data.append(row)

    return list_of_sensor_data

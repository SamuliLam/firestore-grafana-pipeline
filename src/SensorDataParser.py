import datetime
import logging
import json
from typing import List
from zoneinfo import ZoneInfo

from google.api_core.datetime_helpers import DatetimeWithNanoseconds

POSSIBLE_SENSOR_ID_FIELDS = ("sensor_id", "id", "sensorId", "device_id", "deviceId", "sensorID", "SensorID")
POSSIBLE_TIMESTAMP_FIELDS = ("timestamp", "time", "date", "datetime", "SensorReadingTime")

LIST_VALUE_INTERVAL_MINUTES = 5


class SensorDataParser:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.tz_helsinki = ZoneInfo("Europe/Helsinki")
        self.tz_utc = ZoneInfo("UTC")
        self.id_fields = set(POSSIBLE_SENSOR_ID_FIELDS)
        self.ts_fields = set(POSSIBLE_TIMESTAMP_FIELDS)
        self.ignored_fields = self.id_fields | self.ts_fields | {"sensor_type"}

    def process_raw_sensor_data(self, raw_data: dict) -> List[dict]:
        if not raw_data:
            return []

        raw_id = next((raw_data.get(f) for f in POSSIBLE_SENSOR_ID_FIELDS if raw_data.get(f)), None)
        sensor_id = raw_id.replace(":", "") if raw_id else None

        is_nested = any(_value_looks_nested(v) for v in raw_data.values())

        if not is_nested and not sensor_id:
            return []

        first_key_as_timestamp = None

        if not is_nested:
            return self.convert_to_normalized_format(raw_data, sensor_id, None)

        first_key = next(iter(raw_data))
        parsed_time = SensorDataParser.parse_timestamp(first_key, use_default=False)
        if parsed_time:
            first_key_as_timestamp = parsed_time

        extracted_id, data = extract_sensor_and_metrics(raw_data)
        final_id = sensor_id or (extracted_id.replace(":", "") if extracted_id else None)

        if not final_id:
            return []

        return self.convert_to_normalized_format(data, final_id, first_key_as_timestamp)

    def convert_to_normalized_format(self, data: dict, sensor_id: str | None,
                                     first_key_ts: datetime.datetime | None) -> List[dict]:
        """
        Parse incoming JSON data into SensorData objects in EAV format.
        """
        rows = []

        # Handle both single object and array of objects
        sensor_data_as_list = data if isinstance(data, list) else [data]

        for sensor_reading in sensor_data_as_list:

            metrics = {
                k: v for k, v in sensor_reading.items()
                if k not in self.ignored_fields
            }

            try:
                rows.extend(self.parse_sensor_item(sensor_reading, metrics, sensor_id, first_key_ts))
            except ValueError:
                continue

        return rows

    def parse_sensor_item(self, item: dict, metrics: dict, sensor_id: str | None,
                          first_key_ts: datetime.datetime | None) -> List[dict]:

        sensor_type = item.get("sensor_type", self.collection_name)

        item_timestamp = next((item.get(field) for field in POSSIBLE_TIMESTAMP_FIELDS if item.get(field)), None)

        if item_timestamp:
            base_time = self.parse_timestamp(item_timestamp)
        elif first_key_ts:
            base_time = first_key_ts
        else:
            base_time = self.parse_timestamp(None)

        rows = []
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, list):
                rows.extend(
                    self.parse_list_metric(metric_name, metric_value, sensor_id, sensor_type, base_time)
                )
            else:
                row = self.create_sensor_row(metric_name, metric_value, sensor_id, sensor_type, base_time)
                if row:
                    rows.append(row)

        return rows

    def parse_timestamp(self, f_timestamp, use_default: bool = True) -> datetime.datetime | None:

        if not f_timestamp:
            return datetime.datetime.now(tz=self.tz_utc) if use_default else None

        if isinstance(f_timestamp, DatetimeWithNanoseconds):
            if f_timestamp.tzinfo is None:
                f_timestamp = f_timestamp.replace(tzinfo=self.tz_utc)
            return f_timestamp.astimezone(self.tz_utc)

        if isinstance(f_timestamp, str):
            try:
                dt = datetime.datetime.fromisoformat(f_timestamp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self.tz_helsinki)
                return dt.astimezone(self.tz_utc)
            except ValueError:
                pass

        return datetime.datetime.now(tz=self.tz_utc) if use_default else None

    @staticmethod
    def parse_list_metric(
            metric_name: str,
            metric_values: list,
            sensor_id: str,
            sensor_type: str,
            base_time: datetime.datetime
    ) -> List[dict]:
        rows = []
        for i, val in enumerate(reversed(metric_values)):
            ts = base_time - datetime.timedelta(minutes=LIST_VALUE_INTERVAL_MINUTES * i)
            row = SensorDataParser.create_sensor_row(metric_name, val, sensor_id, sensor_type, ts)
            if row:
                rows.append(row)
        return rows

    @staticmethod
    def create_sensor_row(
            metric_name: str,
            metric_value,
            sensor_id: str,
            sensor_type: str,
            timestamp: datetime.datetime
    ) -> dict | None:

        if metric_value is None or metric_value == "" or (isinstance(metric_value, (list, dict)) and not metric_value):
            return None

        if isinstance(metric_value, (int, float)):
            metric_value = round(float(metric_value), 4)

        return {
            "timestamp": timestamp,
            "sensor_id": sensor_id,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "sensor_type": sensor_type,
        }


def extract_sensor_and_metrics(d: dict):
    key = next(iter(d))
    value = d[key]

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return extract_sensor_and_metrics({key: parsed})
        except json.JSONDecodeError:
            return None, {}

    if isinstance(value, dict):
        if all(isinstance(v, list) for v in value.values()):
            return key, value
        else:
            return extract_sensor_and_metrics(value)

    return None, {}


def _value_looks_nested(value):
    if isinstance(value, dict):
        return True

    if isinstance(value, str):
        s = value.strip()
        return s.startswith('{"') and '":' in s

    return False

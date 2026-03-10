import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

POSSIBLE_SENSOR_ID_FIELDS = ("sensor_id", "id", "sensorId", "device_id", "deviceId", "sensorID", "SensorID", "mac")
POSSIBLE_TIMESTAMP_FIELDS = ("timestamp", "time", "date", "datetime", "SensorReadingTime", "ts")


class SensorDataParser:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.tz_helsinki = ZoneInfo("Europe/Helsinki")
        self.tz_utc = ZoneInfo("UTC")
        self.id_fields = set(POSSIBLE_SENSOR_ID_FIELDS)
        self.ts_fields = set(POSSIBLE_TIMESTAMP_FIELDS)
        self.ignored_fields = self.id_fields | self.ts_fields | {"project_id"}
        self.cached_id_field = None
        self.cached_ts_field = None

    def process_raw_sensor_data(self, raw_data: dict) -> List[dict]:
        if not raw_data:
            return []

        if not self.cached_id_field:
            self.cached_id_field = _find_field_name(raw_data, self.id_fields)

        raw_id_val = raw_data.get(self.cached_id_field) if self.cached_id_field else None
        sensor_id = str(raw_id_val).replace(":", "") if raw_id_val else None

        return self._convert_to_normalized_format(raw_data, sensor_id)

    def _convert_to_normalized_format(self, sensor_reading: dict, sensor_id: str | None) -> List[dict]:
        rows = []

        actual_measurements = sensor_reading.get("measurements", {})
        extra_fields = sensor_reading.get("extra", {})

        if not actual_measurements and not extra_fields:
            metrics = {k: v for k, v in sensor_reading.items() if k not in self.ignored_fields}
        else:
            metrics = {**actual_measurements, **extra_fields}

        if not metrics:
            return []

        base_time = self._parse_timestamp(sensor_reading)

        for metric_name, metric_value in metrics.items():
            row = self._create_sensor_row(metric_name, metric_value, sensor_id, self.project_id, base_time)
            if row:
                rows.append(row)

        return rows

    def _parse_timestamp(self, item: dict) -> datetime.datetime:
        if not self.cached_ts_field:
            self.cached_ts_field = _find_field_name(item, self.ts_fields)

        val = item.get(self.cached_ts_field) if self.cached_ts_field else None

        if isinstance(val, DatetimeWithNanoseconds):
            return val.astimezone(self.tz_utc)

        if isinstance(val, (int, float)):
            if val > 1e12: val /= 1000  # ms -> s
            return datetime.datetime.fromtimestamp(val, tz=self.tz_utc)

        if isinstance(val, str):
            try:
                dt = datetime.datetime.fromisoformat(val)
                return dt.astimezone(self.tz_utc) if dt.tzinfo else dt.replace(tzinfo=self.tz_helsinki).astimezone(
                    self.tz_utc)
            except ValueError:
                pass

        return datetime.datetime.now(tz=self.tz_utc)

    @staticmethod
    def _create_sensor_row(metric_name: str, metric_value, sensor_id: str | None, project_id: str,
                           timestamp: datetime.datetime) -> Optional[dict]:
        if metric_value is None or metric_value == "":
            return None

        if isinstance(metric_value, (int, float)):
            metric_value = round(float(metric_value), 4)

        return {
            "timestamp": timestamp,
            "sensor_id": sensor_id,
            "metric_name": metric_name,
            "metric_value": str(metric_value),
            "project_id": project_id,
        }


def _find_field_name(raw_data: dict, possible_fields: set) -> str | None:
    for f in possible_fields:
        if f in raw_data:
            return f
    return None

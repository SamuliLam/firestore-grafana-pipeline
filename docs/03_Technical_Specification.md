# IoT Sensor Data Ingestion and Processing System

## 1. In-Depth Data Ingestion Workflow

This section describes the data ingestion workflow used by the system, from the point where sensor data is produced to the point where it is forwarded for normalization and further processing.

### 1.1 Sensor Data Publishing

IoT sensors produce measurement data such as temperature, humidity, and air pressure.

- Sensors are grouped into predefined sensor categories, where each category represents a specific type of sensor.
- Each sensor category publishes data to its own Google Cloud Pub/Sub topic. The published messages contain measurement data for individual sensors, encoded as JSON payloads.

### 1.2 Pub/Sub Subscription and Event Triggering

- Each Pub/Sub topic has a corresponding subscriber.
- When new data is published to the topic, the subscriber triggers a cloud-based processing service.
- This event acts as the entry point to the data ingestion workflow.

### 1.3 Cloud Run Service per Sensor Category

For each sensor category, a Google Cloud Run service processes the incoming Pub/Sub events.

Each service executes the same type of trigger logic, but is configured using environment variables to handle:
- a specific sensor category
- the corresponding Firestore collection

When an event is received, the Cloud Run service begins processing the payload.

### 1.4 Message Parsing and Data Preparation

The Cloud Run service that subscribes to the Pub/Sub topic performs the following steps for each incoming message:

1. Decode the Pub/Sub message payload (base64).
2. Parse the JSON content into a structured object/dictionary.
3. Extract the sensor identifier (`sensor_id`) and the measurement values (metrics).
4. Attach minimal metadata required for downstream processing.

#### Enrichment rule

The incoming raw data already contains the `sensor_id` field. The enrichment step adds only a `sensor_type` field that identifies the sensor category (for example, `ymparistomoduuli`).

The enriched object (raw data + `sensor_type`) is used for forwarding to the Normalizer API. This enriched object is not written to Firestore.

**Example of the typical data structure after parsing and enrichment:**
```json
{
  "sensor_id": "ABC123",
  "temperature": 21.4,
  "humidity": 55.1,
  "timestamp": "2024-06-15T12:34:56Z",
  "sensor_type": "viherpysakki"
}
```

### 1.5 Writing Data to Firestore

After parsing (and independently of forwarding to the Normalizer API), the service writes the original parsed data into Firestore:

- Each sensor category uses its own Firestore collection (collection name corresponds to `sensor_type`).
- Documents are created using a deterministic document id that includes the sensor identifier and a timestamp (e.g., `{sensor_id}_{YYYY-MM-DD-HH:MM:SS}`).
- Firestore acts as a storage layer for raw and near-real-time sensor events prior to final normalization and long-term analytical storage.

**Important:** The document written to Firestore contains the parsed raw sensor data (including `sensor_id`) but does not include the `sensor_type` enrichment that is forwarded to the Normalizer API. Forwarding and Firestore writes are separate actions performed by the Cloud Run service.

### 1.6 Forwarding Data to the Normalization API

In addition to being stored in Firestore, the Cloud Run service forwards the enriched sensor data to the system's Normalizer REST API. The API endpoint is provided to the Cloud Run service through environment variables. The forwarded payload contains the original parsed measurement values together with the added `sensor_type` metadata, which identifies the sensor category.

#### 1.6.1 Current Forwarding Scope

At the time of writing, forwarding sensor data to the Normalizer REST API is implemented only for the environmental module sensor category (`ymparistomoduuli`). For that Cloud Run deployment, the service is configured with the following environment variable:
```
NORMALIZER_API_URL=<url to the Normalizer API>
```

When `NORMALIZER_API_URL` is set, the Cloud Run service will POST the enriched data object (original parsed fields + `sensor_type`) to the Normalizer API endpoint.

#### 1.6.2 Extending Forwarding to Other Sensor Categories

To enable the same forwarding behavior for additional sensor categories, the corresponding Cloud Run services must be configured in the same way:

1. Add the `NORMALIZER_API_URL` environment variable to the Cloud Run service configuration for the category
2. Set its value to the Normalizer API URL
3. Include the API forwarding logic in the service's source code

**Including the API forwarding logic in the service's source code — example:**

Below is an example of the forwarding snippet that services should include. It assumes the service already has parsed the incoming data into a `data` dictionary and that `COLLECTION` contains the sensor category name. The snippet creates an `enriched_doc` containing the `sensor_type` and posts it to the Normalizer API if `NORMALIZER_API_URL` is configured:
```python
import requests

# enriched_doc: original parsed data (contains sensor_id) plus sensor_type
enriched_doc = dict(data)
enriched_doc.update({"sensor_type": COLLECTION})

if NORMALIZER_API_URL:
    try:
        print(f"Sending data to {NORMALIZER_API_URL}: {enriched_doc}")
        r = requests.post(NORMALIZER_API_URL, json=enriched_doc, timeout=10)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        print("Normalizer API request timed out")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"General request error: {e}")
else:
    print("WARNING: NORMALIZER_API_URL not set")
```

Once the environment variable and the forwarding logic are in place for a Cloud Run service, that service will forward enriched sensor events to the Normalizer API following the same workflow used by the environmental module.

### 1.7 Data Reception in the Normalizer API

When sensor data is forwarded from a Cloud Run service, it is received by the Normalizer REST API via the `/webhook` endpoint.

The API is responsible for validating, normalizing, and transforming incoming sensor data into a consistent internal format before it is persisted to the database. The incoming payload is expected to include both the raw sensor measurements and the `sensor_type` field, which identifies the sensor category from which the data originates.

### 1.8 Sensor Data Normalization

Once the data is received, it is processed by the `SensorDataParser` component. The core normalization logic is implemented in the `process_raw_sensor_data` method.

This method iterates through the incoming payload and applies the following high-level steps:

1. extracts and cleans the sensor identifier
2. resolves the timestamp (either from the payload or a generated default)
3. identifies metric fields dynamically
4. converts the input into an Entity–Attribute–Value (EAV) representation

The output of the normalization process is a list of dictionaries, each representing a single sensor metric observation in a normalized format. Each entry follows the structure:
```python
{
    "timestamp": timestamp,
    "sensor_id": clean_sensor_id,
    "metric_name": metric_name,
    "metric_value": metric_value,
    "sensor_type": sensor_type,
}
```

This EAV-based structure ensures flexibility in handling heterogeneous sensor data while maintaining a consistent database schema.

### 1.9 Data Persistence and Visualization

The normalized sensor data entries are persisted using the `insert_sensor_rows` method, which inserts the generated rows into the `SensorData` table in the TimescaleDB database.

TimescaleDB serves as the primary data source for Grafana. Prebuilt and provisioned Grafana dashboards query the database directly using SQL to visualize sensor metrics over time.

In the frontend application, these Grafana dashboards are embedded using iframes. This allows users to interactively explore sensor data, inspect historical trends, and monitor changes in metric values through a unified user interface.

## 2. Database

This section details the database strategy used to store, manage and retrieve sensor data. The project utilizes TimescaleDB as the primary analytical storage for normalized time-series data.

### 2.1 Database-Application Integration

While the underlying database schema is initialized via SQL scripts, the application logic interacts with the database using an Object-Relational Mapping (ORM) layer written in Python.

The project uses SQLAlchemy to map the relational database tables to Python classes. This allows the backend code to access sensor data as standard Python objects rather than writing raw SQL queries for every operation.

The Database models are defined in `db.py` and mirror the SQL schema:

- **SensorData Class:** Maps to the `sensor_data` table. It defines the structure for timestamped sensor data.
- **SensorMetadata Class:** Maps to the `sensor_metadata` table. It defines the static metadata of the sensors.

### 2.2 TimescaleDB

TimescaleDB was chosen for its features that can reliably handle sizable amounts of time series data while maintaining an SQL standard relational database. The core feature utilized is Hypertable, which automatically partitions data by time across storage, ensuring that queries remain fast even when datasets grow.

### 2.3 Entity-Attribute-Value (EAV) Schema

Due to being unable to predict future sensor data formats, a highly adaptable schema for the database was required. Instead of creating individual tables for each sensor data response, the project team chose to implement an Entity-Attribute-Value (EAV) schema pattern in the `sensor_data` table.

Instead of storing a single row with multiple columns for "temperature", "humidity", "pressure" and whatever metric future sensors may support, the project stores one row per metric measurement of a sensor.

**The `sensor_data` table structure is as follows:**

| timestamp | sensor_id | metric_name | metric_value | sensor_type |
|-----------|-----------|-------------|--------------|-------------|
| 2023-10-27 10:00:00 | env-sensor-01 | temperature | 22.5 | ymparistomoduuli |
| 2023-10-27 10:00:00 | env-sensor-01 | humidity | 60 | ymparistomoduuli |

This structure allows the project to ingest data from entirely new sensor types without requiring any database schema changes.

### 2.4 Sensor Metadata

To avoid data redundancy, static information about sensors is separated from the high-volume measurement data. The `sensor_metadata` table acts as a relational lookup table containing:

- **sensor_id:** Primary key, linking to `sensor_data` table
- **latitude / longitude:** Coordinates for Grafana visualization
- **sensor_type:** category of sensor

The separation of sensor measurement data and sensor metadata ensures that the high-volume time-series table remains devoid of redundancy while metadata is only joined for Grafana-based features and visualizations.

### 2.5 Data Integrity

The database schema enforces integrity through a composite primary key on the `sensor_data` table. The combination of `(timestamp, sensor_id, metric_name)` must be unique.

This composite key prevents duplicate data ingestion if the normalizer-api were to re-process the same message. The error is handled gracefully and does not break the data flow.

What the composite key essentially prevents is a situation where a specific sensor has an identical measurement metric at the exact same millisecond.

### 2.6 Integration with Grafana

The database is exposed to Grafana. This ensures that dashboards can directly be created by accessing the data in the database in real time. This will ensure a smooth and intuitive experience for creating and maintaining Grafana visualizations.

## 3. Backend Workflow (Normalizer API)

The Normalizer API handles receiving raw sensor data, validating, normalizing it into a unified schema, and storing it in TimescaleDB. It supports real-time ingestion, historical data loading from Firestore, and sensor metadata management (e.g., location, category). This component standardizes heterogeneous sensor formats into consistent time-series data for analytics and Grafana dashboards.

### Components:
1. REST API for data ingestion, historical data loading, and metadata management  
2. SensorDataParser for raw data processing and normalization  
3. Historical data loader from Firestore  
4. Database layer for persisting normalized data  

### 3.1 Ingestion Endpoint

All incoming sensor measurements are sent to the Normalizer API through its public endpoint:
```
POST /webhook
```

The request body must contain:
- a valid `sensor_id`
- measurement fields (e.g., temperature, humidity, pressure, etc.)
- a `sensor_type` field provided by the Cloud Run service

The API does not assume a strict schema. Instead, it processes any number of unknown metric fields dynamically.

### 3.2 SensorDataParser — Raw Data Processing Pipeline

The core logic for handling incoming data is implemented in the `SensorDataParser` class. It executes the following sequence:

1. Sensor identifier extraction
2. Timestamp handling and normalization
3. Metric extraction
4. List-based metric expansion (if applicable)
5. Conversion to normalized EAV (Entity–Attribute–Value) rows

The end result of the parsing stage is a list of dictionaries:
```python
{
    "timestamp": "... (UTC)",
    "sensor_id": "...",
    "metric_name": "...",
    "metric_value": "...",
    "sensor_type": "..."
}
```

These rows are then handed off to the database layer.

### 3.3 Sensor Identifier Handling

Incoming data may contain the sensor identifier in various possible field names.

**Supported field names:**
- `sensor_id`
- `id`
- `sensorId`
- `device_id`
- `deviceId`
- `sensorID`
- `SensorID`

At least one of these must be present. If no valid identifier is detected, the payload is rejected.

This approach ensures compatibility with different sensor vendors and formats.

### 3.4 Metric Extraction Rules

All fields that are not identified as sensor identifier fields or timestamp fields are interpreted as metrics. This rule allows the backend to flexibly ingest heterogeneous sensor payloads without requiring predefined schemas.

**Processing rules:**
- The field name becomes `metric_name`.
- The corresponding value becomes `metric_value`.
- Arbitrary and previously unknown metric fields are accepted without any code changes.
- Complex values (such as lists) are handled by specialized logic described later.

This design ensures that the backend can automatically adapt to new sensor types or payload structures.

However, this also means that certain metadata-like fields will intentionally be treated as metrics. For example, a payload such as:
```
SensorReadingTime: "2025-05-31T04:59:26"   (string)
finalvalue: "-26.3"                        (string)
name: "Arkkupakastin (Toimisto)"           (string)
sensorID: "125052"                        (string)
unit: "°C"
```

will produce the following behavior:
- `sensorID` → recognized as a valid sensor identifier (and therefore excluded from metric extraction)
- `SensorReadingTime` → recognized as a timestamp field (and excluded)
- `finalvalue`, `name`, and `unit` → treated as metrics intentionally

This is expected behavior and part of the backend's schema-flexible ingestion model.

### 3.5 Handling List-Based Metric Values

Some sensors publish arrays of values in a single message (batch upload).

**Rules:**
- The latest value in the list receives the Firestore ingestion timestamp.
- Earlier values receive timestamps spaced backwards.
- Spacing is defined by the constant `LIST_VALUE_INTERVAL_MINUTES` (default = 5 min).

**Example:** if a sensor reports 5 measurements, timestamps will be:
```
t, t-5min, t-10min, t-15min, t-20min
```

This preserves chronological order without requiring the sensor to embed timestamps.

### 3.6 Timestamp Handling and Normalization (Always Stored as UTC)

The system supports multiple timestamp field names, such as:
- `timestamp`
- `time`
- `date`
- `datetime`
- `SensorReadingTime`

If no valid timestamp is provided, the ingestion time is used.

**Normalization rule:**

All timestamps stored in TimescaleDB are converted to UTC.

This ensures:
- consistency across all sensor categories
- compatibility with Grafana
- correct aggregation and comparison across time zones

**Implementation Summary:**

The parser applies these steps:

1. If the timestamp is missing → use current time (UTC).
2. If the timestamp is a Firestore `DatetimeWithNanoseconds`, convert it to UTC.
3. If the timestamp is a string:
   - parse as ISO 8601
   - assume Europe/Helsinki if no timezone is provided
   - convert to UTC

This guarantees that all rows inserted into the time-series database use a uniform timezone.

### 3.7 Database Persistence Layer

After parsing and normalization, the API uses the method:

```python
insert_sensor_rows(...)
```

to persist normalized EAV rows into the `SensorData` table inside TimescaleDB.


### 3.8 Historical Sensor Data Loading

In addition to real-time data ingestion, the system supports loading historical sensor data from Firestore into the TimescaleDB database. This functionality is implemented in the `history_to_timescale.py` script.

The script iterates over configured Firestore collections corresponding to sensor categories and fetches older documents to be parsed and inserted into the time-series database.

**Important considerations:**

- The script expects sensor data documents to contain a `timestamp` field that indicates the measurement time.
- If the `timestamp` field is missing or named differently than `timestamp`, the historical data loading may not function correctly, as the query filters and timestamp extraction rely on this standard field name.
- Missing or incorrectly named timestamp fields can lead to incomplete or failed ingestion of historical data.

This implies that for seamless historical data loading, sensor data stored in Firestore should consistently include a valid `timestamp` field following the expected naming convention.

### 3.9 Sensor Metadata Management

The backend also provides endpoints to manage sensor metadata stored in the `sensor_metadata` table. This table holds static information about each sensor, such as sensor identifier, geographic coordinates (latitude and longitude), and sensor category.

Sensor metadata is used primarily for geographic visualization of sensors on maps within the frontend application.
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
NORMALIZER_API_URL=<url to the Normalizer API webhook endpoint>
```


When `NORMALIZER_API_URL` is set, the Cloud Run service will POST the enriched data object (original parsed fields + `sensor_type`) to the Normalizer API endpoint.


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

- **sensor_id:** Primary key of sensor Metadata table
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

# 4. Frontend

This part of the document describes how the frontend interacts with the backend, what technologies the frontend uses, and information about the components the frontend uses. The frontend is responsible for receiving and sending requests to the backend depending on what the user wants to do.
The frontend is built using **React** and **TypeScript**. The project uses **Vite** as the build tool.

---

## 4.1 UI components

A lot of the components that are used are from the **Shadcn UI component library**. We used a component library because we wanted to make the UI consistent and use the same kind of styling for components. The used UI components are imported in the **`src/components/ui`** folder.

---

## 4.2 Components

Our own created components are in the **`src/components`** folder. All of these components are used in the homepage. Only the **Dashboard** component is used on the other pages since the other pages only display dashboards from Grafana.

### Component List:
* `AddSensor`
* `Dashboard`
* `HoverSlideAnimation`
* `LoadHistory`
* `RemoveSensor`

The biggest components are `AddSensor`, `LoadHistory`, and `RemoveSensor`. `Dashboard` and `HoverSlideAnimation` are both under 20 lines of code. The `Dashboard` component is used to show data from Grafana.

The **Homepage** is the main page of the website, but it also has **Individual sensor view** and **Multiple sensor view**. These sensor view pages don’t really use any functions or logic inside React, so the main talking point will be the home page.

Our components use a **`refreshKey`** attribute so the components can be individually refreshed and not the entire webpage. More on that later.

### 4.2.1 Component Structure

This section will detail the structure that is used for the three big components (`AddSensor`, `LoadHistory`, and `DeleteSensor`).

In this example, `AddSensor` is used, but the main structure is the same with the other components.

1.  **Imports:** The components import everything needed at the start, including the Shadcn components.
2.  **Function Definition:** Next, there is `export function` followed by the function name.
3.  **State Management:** Inside the function, there is a lot of **`useState`**, which is a React hook that is very useful for managing different states for the component. `useState` hooks are also phenomenal for checking if the submitted form is valid and generally setting errors.
4.  **Backend Communication:** Then there is an **asynchronous function** that is used to communicate with the backend. Inside the asynchronous function, errors and error messages are set depending on the user input. For communicating with the backend, **`fetch`** requests that send or receive the JSON payloads are used.

#### Example Request Structure:

A typical request starts with **`await`**, which makes the function wait until a promise is resolved or rejected. The endpoint is set as the same as in the backend. `API_BASE_URL` is located inside an `.env` file.

```javascript
await fetch(`${API_BASE_URL}/api/sensors`, {
    method: 'POST', // Example method
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```
In this request, we use **POST** because we want to add a sensor to the map. In the header/body, it tells what kind of content we want to send to the backend.

### Success/Failure Handling:

We wait for the result of the request, and depending on if the request has failed or succeeded, different things are done.

* If it somehow **failed**, we set the appropriate error messages and inform the user.
* If it **succeeds**, we refresh the form and tell the user it succeeded.

There are also some `console.log` statements that help to debug things in the code, like here where it tells if a sensor was successfully added.

### Component Rendering:

After the backend request, there is the actual component that gets rendered on the webpage.
```javascript
    <div className="add-sensor-panel p-4 border rounded-lg shadow-sm bg-white dark:bg-gray-800">
        <FieldLegend className="text-lg font-semibold mb-4">Add New Sensor</FieldLegend>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col">
                <FieldLabel htmlFor="sensor_id" className="mb-1 font-medium">Sensor ID</FieldLabel>
                <Input type="text"
                       id="sensor_id"
                       name="sensorId"
                       value={sensorId}
                       onChange={(e) => setSensorId(e.target.value)}
                       className="border rounded px-3 py-2"
                       placeholder="Enter Sensor ID"/>
            </div>
            {errors.sensorId && <p className="text-red-500 text-sm">{errors.sensorId}</p>}
```
This is where the form starts, and you can see some of the Shadcn components like **`Input`**, **`FieldLegend`**, and **`FieldLabel`**. There is also the **`handleSubmit`** function which is called when submitting the form using a button.

The **`onChange`** attribute sets the `sensorId` using `useState`. This same structure is used for all of the input fields. If there is some kind of error, it is displayed under the input field.

At the end of the form, there is a button. Pressing the button triggers different things depending on the `useStates`. If everything went well, the `sensorAdded` `useState` should be **true** and it displays a **green message**, and if `sensorAddFailed` is true, it displays **red text** with other errors that were encountered.

---

## 4.3 Refresh key

The **`refreshKey`** is a key feature that makes the website more seamless to use. The `refreshKey` is used to refresh the dashboard when making changes to the sensors by adding or removing them. Inside the Dashboard component we give it the following attributes:

```javascript
export const Dashboard = ({ dsb_link, styles, refreshKey = 0 }: DashboardProps) => {
    const defaultClasses = "grow rounded-md shadow-light-shadow-sm"

    return (
        <iframe
            key={String(refreshKey)}
            title="Dashboard"
            src={dsb_link}
            className={ `${defaultClasses} ${styles}`}>
        </iframe>
    )
}
```
Here you can see the key attribute given the refreshkey. Changing the component’s key forces React to unmount and remount the element. So when the key changes the old iframe is discarded and the fresh one is created in its place.

In the homepage we have a function that adds +1 to the previous refreshkey, making the value change thus refreshing the dashboard. Below are the main parts that make the refresh key work on the homepage.

1. Function that changes the value of refreshkey
```javascript
    const refreshEverything = () => {
    setDashboardRefreshKey(prev => prev + 1);

    queryClient.invalidateQueries({
        queryKey: ["sensor_metadata"],
    });
};
```
2. Actions that trigger the refreshkey to change.
```javascript
    <AddSensor refreshKey={dashboardRefreshKey} onSensorAdded={refreshEverything}/>
    <RemoveSensor refreshKey={dashboardRefreshKey} onSensorRemoved={refreshEverything}/>
```
3. Refreshkey changing when refreshEverything called.
```javascript
<Dashboard
    styles="w-full"
    dsb_link={map_dsb}
    refreshKey={dashboardRefreshKey}
/>
```
### 4.4 Search function 
Homepage also includes a search function to find sensors in the dashboard. Inside the project is React context that stores searchValue that has the current text the user typed and a function that updates it using useState. In our home page there is a useSearch() hook that gives the real-time value of the search text.
```javascript
const { searchValue } = useSearch();
```
The search actually becomes functional when the DataTable function gets the search value
```javascript
<DataTable
    columns={columns}
    data={data ?? []}
    searchFilter={searchValue}
    onRowClick={handleRowClick}
/>
```
The DataTable receives the sensor data and the current search value. Every time the searchValue changes the DataTable re-renders, filtering out the values we want and what we don’t want. The DataTable is a component that is made to filter out values based on sensorId. So typing a sensorId you want to search for will pop in the list of values under the map.




## 6. Docker

### 6.1 Overview

Docker is used to containerize key backend components and Grafana to provide consistent, isolated, and portable deployment environments. The frontend application is **not** containerized and is deployed separately.

### 6.2 Containerized Services

The main services containerized with Docker are:

- **TimescaleDB**  
  Runs the time-series database using the official TimescaleDB image (PostgreSQL 17-based). It uses persistent volumes for data durability and initializes the database with a custom SQL script. Health checks ensure the database is ready before dependent services start.

- **Normalizer API**  
  The backend normalization service built from the project source using a Dockerfile. Runs on Uvicorn, exposing port 8080. Configured via environment variables for database connection, Google Cloud credentials, and Firestore collections. The source code is volume-mounted for live reload during development. Depends on TimescaleDB availability.

- **Grafana**  
  Visualization service running from the official Grafana image. It exposes port 3000 and is configured with admin credentials and pre-provisioned dashboards. Persistent volumes store Grafana data and configurations. Depends on TimescaleDB being healthy.

### 6.3 Docker Compose Orchestration

The services are orchestrated using Docker Compose, which manages service dependencies, networking, and volume mounting. This setup ensures services start in the correct order, for example, the Normalizer API and Grafana wait until TimescaleDB is healthy before launching.

### 6.4 Running the Stack

Common Docker Compose commands for managing the environment:
```bash
docker-compose up       # Start all services
docker-compose down     # Stop all services (volumes remain)
```

### 6.5 Environment Configuration

Environment variables are used to configure sensitive information and service parameters such as:

- Database credentials and connection URLs
- Google Cloud service account credentials
- Firestore collection names
- Grafana admin user credentials

These are typically provided via a `.env` file or injected by the deployment platform.

### 6.6 Notes and Development Workflow

- The backend service source code is mounted as a volume in the container to enable live reloading during development.
- Persistent Docker volumes ensure that database and Grafana data survive container restarts and updates.
- The frontend application is deployed separately and is not part of the Docker container ecosystem.

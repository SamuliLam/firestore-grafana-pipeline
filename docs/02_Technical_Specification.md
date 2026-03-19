# IoT Sensor Data Ingestion and Processing System

## Table of Contents
1. [In-Depth Data Ingestion Workflow](#1-in-depth-data-ingestion-workflow)
2. [Database](#2-database)
3. [Backend Workflow (Normalizer API)](#3-backend-workflow-normalizer-api)
4. [Frontend Application](#4-frontend-application)
5. [Grafana](#5-grafana)
6. [Deployment and Docker](#6-deployment-and-docker)

## 1. In-Depth Data Ingestion Workflow

This section describes the data ingestion workflow used by the system, from the point where sensor data is produced to the point where it is forwarded for normalization and further processing.

### 1.1 Sensor Data Publishing

IoT sensors (e.g., TEROS-12, RuuviTag, Generic MQTT nodes) produce various environmental metrics.

- Dynamic Metrics: The system ingests any key-value pairs provided in the payload.

- Unified Ingress: All sensors publish their data to a single Google Cloud Pub/Sub topic.

- Grouping: Sensors are grouped logically by project_id (defined during sensor configuration in the frontend) rather than hardware categories.

### 1.2 Pub/Sub Subscription and Event Triggering

- The unified Pub/Sub topic has a push subscription managed by Google Cloud Eventarc.

- When new data arrives, Eventarc triggers the central Cloud Run processing service.

### 1.3 Unified Cloud Run Processing Service

A single Google Cloud Run service handles all incoming traffic. This service is the "brain" of the ingestion pipeline.

- It is environment-agnostic and relies on a Firestore lookup to determine how to handle each message based on the sensor's id.

- It distinguishes between "Configured" sensors (routed to projects) and "Unknown" sensors (routed to a discovery collection).

### 1.4 Message Parsing and Transformation (Cloud Run Logic)

The Cloud Run service is the central processing unit that transforms raw, heterogeneous JSON data into a standardized format. When an event is received via Eventarc, the service executes the following sequence:

1.  **Decoding and Extraction:**
    * The Pub/Sub message payload is decoded from Base64.
    * The JSON content is parsed, and the unique physical identifier (`sensor_id` or MAC address) is extracted.

2.  **Configuration Lookup:**
    * The service performs a real-time lookup from the `sensor_metadata` (stored in Firestore).
    * It retrieves the assigned `project_id` and the specific **Mapping Schema** defined for that sensor.

3.  **Dynamic Mapping (Measurements vs. Extra):**
    * **Measurements Object:** The service iterates through the raw JSON keys. If a key is found in the sensor's mapping configuration (e.g., raw key `t` maps to `temperature`), it is placed into the `measurements` object with its new standardized name.
    * **Extra Object:** To ensure total data transparency and prevent data loss, any raw fields that are **not** defined in the mapping schema are automatically moved to an `extra` object. This allows researchers to see diagnostic data (like RSSI, battery voltage, or internal counters) even if they aren't explicitly tracked as primary metrics.

4.  **Timestamp Normalization:**
    * The service looks for a timestamp in the payload. If missing, it uses the current arrival time.
    * All timestamps are converted to a standardized ISO 8601 UTC format to ensure consistency across different time zones and sensor types.

**Example of the transformed data structure:**

```json
{
  "sensor_id": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2026-03-19T08:00:00.000Z",
  "project_id": "greenhouse_alpha",
  "measurements": {
    "temperature": 22.5,
    "humidity": 48.2,
    "soil_moisture": 0.35
  },
  "extra": {
    "rssi": -68,
    "battery": 3600
  }
}
```

### 1.5 Writing Data to Firestore

The Cloud Run service routes the transformed data to the following Firestore paths:

- Configured Sensors: Data is written to the project's specific collection: `projects/{project_id}/sensors/{sensor_id}/readings/{doc_id}`

- Unconfigured Sensors: If the sensor is unrecognized, data is stored for discovery: `unconfigured_sensors/{sensor_id}/readings/{doc_id}`

- Deterministic ID: The `doc_id` is generated as a timestamp string (e.g., `2026-03-17-12:34:56`) to prevent duplicate entries for the same second.

### 1.6 Forwarding Data to the Normalization API

> **NOT SUPPORTED IN CURRENT VERSION**
> In addition to being stored in Firestore, the Cloud Run service forwards the enriched sensor data to the system's Normalizer REST API. The API endpoint is provided to the Cloud Run service through environment variables. The forwarded payload contains the original parsed measurement values together with the added `project_id` metadata, which identifies the sensor category.

#### 1.6.1 Current Forwarding Scope

> **NOT SUPPORTED IN CURRENT VERSION**
At the time of writing, forwarding sensor data to the Normalizer REST API is implemented only for the environmental module sensor category (`ymparistomoduuli`). For that Cloud Run deployment, the service is configured with the following environment variable:

```
NORMALIZER_API_URL=<url to the Normalizer API webhook endpoint>
```

> When `NORMALIZER_API_URL` is set, the Cloud Run service will POST the enriched data object (original parsed fields + `project_id`) to the Normalizer API endpoint.

### 1.7 Data Reception in the Normalizer API

> **NOT SUPPORTED IN CURRENT VERSION**
> When sensor data is forwarded from a Cloud Run service, it is received by the Normalizer REST API via the `/webhook` endpoint.

>The API is responsible for validating, normalizing, and transforming incoming sensor data into a consistent internal format before it is persisted to the database. The incoming payload is expected to include both the raw sensor measurements and the `project_id` field, which identifies the sensor category from which the data originates.

### 1.8 Sensor Data Normalization

Once the data is received, it is processed by the `SensorDataParser` component. The core normalization logic is implemented in the `process_raw_sensor_data` method.

This method iterates through the incoming payload and applies the following steps:

1. extracts and cleans the sensor identifier
2. identifies metrics dynamically from the `measurements` object (or directly from the payload if measurements object is not used)
3. resolves the timestamp (either from the payload or a generated default)
4. converts the input into an Entity–Attribute–Value (EAV) representation

The output of the normalization process is a list of dictionaries, each representing a single sensor metric observation in a normalized format. Each entry follows the structure:

```python
{
   "timestamp": timestamp,
   "sensor_id": clean_sensor_id,
   "metric_name": metric_name,
   "metric_value": metric_value,
   "project_id": project_id,
}
```

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

### 2.2 TimescaleDB & Hypertables

TimescaleDB partitions data into Hypertables based on time. This architecture ensures that query performance remains consistent even as the database grows to millions of entries.

### 2.3 Entity-Attribute-Value (EAV) Schema

To support a limitless variety of environmental sensors, the `sensor_data` table uses the EAV pattern:

**The `sensor_data` table structure is as follows:**

| timestamp           | sensor_id     | metric_name | metric_value | project_id       |
| ------------------- | ------------- | ----------- | ------------ |------------------|
| 2023-10-27 10:00:00 | env-sensor-01 | temperature | 22.5         | project_a        |
| 2023-10-27 10:00:00 | env-sensor-01 | humidity    | 60           | project_a |


### 2.4 Sensor Metadata

The `sensor_metadata` table holds static information about each sensor. It is used for visualizing sensor locations on maps in Grafana and displaying each sensor in a table in the frontend.

- **sensor_id:** Primary key of sensor Metadata table
- **description:** Description of the sensor
- **latitude / longitude:** Coordinates for Grafana visualization
- **project_id:** project the sensor belongs to


### 2.5 Data Integrity

The database schema enforces integrity through a composite primary key on the `sensor_data` table. The combination of `(timestamp, sensor_id, metric_name)` must be unique.

This composite key prevents duplicate data ingestion if the normalizer-api were to re-process the same message. The error is handled gracefully and does not break the data flow.

What the composite key essentially prevents is a situation where a specific sensor has an identical measurement metric at the exact same millisecond.

### 2.6 Integration with Grafana

The database is exposed to Grafana. This ensures that dashboards can directly be created by accessing the data in the database in real time.

## 3. Backend Workflow (Normalizer API)

The Backend API, acts as the administrative hub. While real-time ingestion is handled by Cloud Run, the Backend manages metadata, sensor configurations, and the historical synchronization (Backfill) from Firestore to TimescaleDB.

### 3.1 Components
1. **Normalizer API:** Endpoints for sensor registration, metadata updates, sensor configurations and triggering historical loads.
2. **SensorDataParser:** Core logic for converting Firestore documents (with `measurements` and `extra` objects) into normalized EAV rows.
3. **Backfill Engine:** A script that synchronizes data from Firestore to TimescaleDB for both new and updated sensors.

---

### 3.2 Ingestion & Webhook Support
> **NOT SUPPORTED IN CURRENT VERSION**
> The `POST /webhook` endpoint is available for legacy testing but is not used in the production pipeline. Inbound data is processed exclusively via the Cloud Run Ingestion service.

---

### 3.3 SensorDataParser — Transformation Pipeline

The `SensorDataParser` class is used by the Backend to normalize data fetched from Firestore. It ensures that heterogeneous payloads are converted into a consistent format for TimescaleDB.

**Sequence of Operations:**
1. **Identifier Extraction:** Detects the `sensor_id` from supported fields (`id`, `deviceId`, `mac`, etc.).
2. **Dynamic Metric Extraction:** - It primarily looks for the `measurements` object created by Cloud Run.
   - Every key-value pair in the `measurements` object is converted into a separate row.
   - Diagnostic data from the `extra` object can also be extracted if configured.
3**UTC Normalization:** All timestamps are parsed (ISO 8601 or Firestore Nanoseconds) and converted strictly to UTC.

**Output Format (EAV):**
```python
{
    "timestamp": "2026-03-19T08:00:00Z",
    "sensor_id": "AA:BB:CC...",
    "metric_name": "soil_temperature",
    "metric_value": 22.5,
    "project_id": "greenhouse_alpha"
}
```

# 4. Frontend Application

The frontend is a React-based single-page application (SPA) hosted at `envidata.metropolia.fi`. It serves as the primary interface for environmental data monitoring and administrative sensor management.

## 4.1 Technology Stack

- **Framework:** React with TypeScript.
- **Routing:** React Router DOM for structured navigation and layout management.
- **Authentication:** **Auth0 Framework** for secure user identity management and role-based access.
- **State & Data Fetching:** - **TanStack Query (React Query):** Used for managed server-state, such as fetching sensor metadata.
    - **Native Fetch API:** Used in legacy and specific administrative components for direct POST/PUT requests to the Backend API.
- **UI Components:** Shadcn UI (Radix UI + Tailwind CSS) for a professional and consistent look.

## 4.2 Application Architecture

### 4.2.1 Core Routing & Guards
The application uses a centralized routing structure in `App.tsx`. 
- **Authentication Guard:** A custom `AuthenticationGuard` component protects all primary routes (Home, Sensors, SensorData).
- **Access Management:** Users who are authenticated but lack specific permissions are directed to the `AccessRequested` view.
- **Shared Layout:** A `SharedLayout` component ensures consistent navigation and branding across different views.

### 4.2.2 Context Providers
- **SearchProvider:** Manages global search state via `SearchContext`, allowing real-time filtering of sensors across the map and table views.
- **QueryClientProvider:** Orchestrates the TanStack Query lifecycle and caching.

## 4.3 Key Components & Features

### 4.3.1 Dynamic Grafana Integration (Maps & Graphs)
The application relies heavily on **Grafana Iframe Integration** instead of local mapping libraries:
- **Geomap View:** The main environmental map is an embedded Grafana **Geomap** panel. This ensures that the map markers, layers, and status indicators are always synchronized with the latest data in TimescaleDB.
- **Dynamic Dashboards:** Sensor-specific views (`SensorData`) render dashboards dynamically. The `refreshKey` pattern is used to force-refresh these iframes when administrative changes (like mapping updates) are performed.

### 4.3.2 Administrative Tools (RBAC)
Management panels (Add/Update/Remove Sensor) are integrated into the main dashboard but are functionally restricted.
- **Admin Actions:** These components communicate with the Backend API using asynchronous functions. While the project transition towards TanStack Query is ongoing, many administrative actions still utilize the native **Fetch API** for direct interaction with the Python backend.
- **Unknown Sensors Discovery:** Admins can view a list of sensors currently in the "unconfigured" state and promote them to active projects through the UI.

### 4.3.3 Real-time Search and Synchronization
The `DataTable` responds to the `searchValue` from the global `SearchProvider`. This allows users to quickly find specific sensors by ID or project id.

## 5. Grafana

Provisioning was implemented by keeping YAML configuration files “datasource.yaml” and “dashboards.yaml” in the datasources and dashboards directories. These files define the required data sources and dashboards for the environment. The docker-compose.yaml file mounts these directories into the Grafana container at startup. When the stack is started with Docker Compose, Grafana reads the provisioning files, configures the TimescaleDB data source, user credentials and loads the predefined dashboards.

At the time of writing, the following dashboards are in use on the frontend:
- Overview.json: Dynamic dashboard that shows all measurements based on different variables such as project_id and selected sensors.
- Sensor.json: Sensor-specific dashboard that shows all measurements for a specific sensor. The dashboard is rendered dynamically based on the sensor_id passed as a variable in the URL.

# 6. Deployment and Docker

This section describes the containerization strategy and the distinct workflows for local development versus production deployment.

## 6.1 Development Workflow

In the local development environment, the system uses a hybrid approach to allow for rapid iteration and live reloading.

- **Backend & Infrastructure:** Containerized using Docker to provide a consistent environment for the database and core services.
- **Frontend:** Not containerized during development. It is run directly on the host machine using `npm run dev` from the frontend project root. This ensures the fastest possible Hot Module Replacement (HMR) and debugging experience.

## 6.2 Containerized Services (Development)

The local `docker-compose.yaml` orchestrates the following services:

* **TimescaleDB:** A PostgreSQL 17-based time-series database. It uses persistent volumes for data durability and is initialized with custom SQL scripts.
* **Backend API (Normalizer/Management):** Built from the backend source code. The source code is volume-mounted into the container to enable live reloading (Uvicorn) as changes are made.
* **Grafana:** The visualization suite, pre-configured with admin credentials and provisioned dashboards/datasources. It depends on TimescaleDB being healthy before starting.

## 6.3 Production Deployment (`envidata-deployment`)

For production environments at **envidata.metropolia.fi**, the project uses a centralized deployment repository: **`envidata-deployment`**.

- **Structure:** Both the frontend and backend repositories are linked as **Git Submodules** within this deployment repo.
- **Unified Orchestration:** In the production repository, the `docker-compose.yaml` containerizes **both** the frontend and the backend for a single cohesive deployment.

## 6.4 Environment Configuration (.env)

The system requires specific environment variables to function. These must be defined in a `.env` file at the root of the respective service or the deployment repository. In addition, make sure that your /docker/secrets directory contains the GCP service account key file named 'normalizer-sa.json' for the backend to access Firestore.

### 6.4.1 Authentication (Auth0)
These variables enable secure login and role-based access control via Auth0:
(*Some are named with the `VITE_` prefix because the same variables are used in the frontend application, which requires the prefix for environment variable exposure.*)
- `VITE_AUTH0_DOMAIN`: The Auth0 tenant domain (e.g., `dev-xxxx.auth0.com`).
- `VITE_AUTH0_AUDIENCE`: The API identifier for backend authorization.

### 6.4.2 Database (TimescaleDB)
Used by the Backend API and Grafana to connect to the time-series storage:
- `POSTGRES_USER`: The administrative username for the database.
- `POSTGRES_PASSWORD`: The password for the database user.
- `POSTGRES_DB`: The name of the database (default: `sensor_data`). (Keep this unchanged to avoid connection issues with Grafana provisioning.)
- `POSTGRES_URL`: Full connection string (e.g., `postgresql://user:pass@db:5432/sensor_data`).

### 6.4.3 Cloud Integration (Google Cloud)
Required for the Backend API to interact with Firestore:
- `GCP_PROJECT_ID`: The ID of the Google Cloud project.

### 6.4.4 Grafana Configuration
- `GRAFANA_ADMIN_USER`: Username for the Grafana administrative interface.
- `GRAFANA_ADMIN_PASSWORD`: Credentials for the Grafana administrative interface.

## 6.5 Running the Stack

### Local Development
```bash
# Start backend infrastructure
docker-compose up -d

# In a separate terminal, start the frontend
cd frontend
npm install
npm run dev
```
### Production Deployment
Refer to the `envidata-deployment` repository for detailed deployment instructions.
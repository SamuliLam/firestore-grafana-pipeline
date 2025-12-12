# Normalizer API Project Summary

---

## 🧭 Table of Contents

1.  [Introduction](#1-introduction)
2.  [Project Documentation Overview](#2-project-documentation-overview)
3.  [Implemented Features / Out of Scope / Not Implemented](#3-implemented-features--out-of-scope--not-implemented)
4.  [Instructions for Future Development](#4-instructions-for-future-development)
    * [Local installation](#local-installation)
    * [Extending live data forwarding to other sensor categories](#-extending-live-data-forwarding-to-other-sensor-categories)
    * [Changing supported sensor_id or timestamp fields](#changing-supported-sensor_id-or-timestamp-fields)
    * [API Documentation](#api-documentation)

---

## 1. Introduction

This project implements a data ingestion pipeline and a frontend visualization system for IoT sensor data. The system ingests both historical and live sensor measurements from Google Cloud Firestore collections into a local TimescaleDB instance. Live data is received through a REST API, while historical data can be synchronized on demand.

The TimescaleDB database is configured as a data source in Grafana and is used to visualize common sensor metrics such as temperature, humidity, and air pressure. The frontend application embeds prebuilt Grafana dashboards to present these metrics to the user. Additional dashboards can be created directly in Grafana by defining new SQL queries on the sensor data. This allows developers and advanced users to explore new metrics without modifying the backend or frontend code.

The system is designed to be extensible, allowing new sensors, metrics, and visualizations to be added with minimal changes to the existing architecture.

## 2. Project Documentation Overview

* **Installation and User Guide**
    * Instructions for setting up and running the system.
    * **Location:** [**README.md**](../README.md)

* **Functional Specification**
    * Describes user stories, acceptance criteria, and non-functional requirements.
    * **Location:** [**docs/01_Functional_Specification.md**](01_Functional_Specification.md)

* **Technical Implementation Documentation**
    * Detailed descriptions of system architecture, components, database design, and APIs.
    * **Location:** [**docs/02_Technical_Specification.md**](02_Technical_Specification.md)

* **Testing Report**
    * Details test cases, results, and coverage analysis.
    * **Location:** [**docs/03_Testing_Report.md**](03_Testing_Report.md)

## 3. Implemented Features / Out of Scope / Not Implemented

### ✅ Implemented:

* Live sensor data ingestion via REST API
* On-demand historical data synchronization from Firestore
* Sensor metadata management via frontend UI
* Visualization of sensor metrics using embedded Grafana dashboards
* Visualization of sensor metadata using geo-mapping features in Grafana

### 🚫 Out of Scope / Not Implemented:

* User authentication and role-based access control for both frontend and Grafana
* Alerting and notifications in Grafana
* Historical data synchronization for nested firestore collections (example: `sensor_category/zone1/sensorA`)

## 4. Instructions for Future Development

### Local installation:
For instructions on setting up the project locally, please refer to the Installation and User Guide located at: [README.md](../README.md)

### ⚙️ Extending live data forwarding to other sensor categories:

To enable forwarding behavior for additional sensor categories, the corresponding Cloud Run services must be configured in the following way:

1.  **Add Environment Variable:** Add the `NORMALIZER_API_URL` environment variable to the Cloud Run service configuration for the category.
2.  **Set Value:** Set its value to the Normalizer API URL (e.g., `https://normalizer-api-xxxxxxx.run.app/webhook`).
3.  **Implement Logic:** Include the API forwarding logic in the service's source code.

> ℹ️ **Gcloud Reference:** For instructions on how to deploy or update an existing Run Service, refer to the official documentation: [https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy)

#### Including the API forwarding logic in the service's source code — example:

Below is an example of the forwarding snippet that services should include. It assumes the service already has parsed the incoming data into a `data` dictionary and that `COLLECTION` contains the sensor category name. The snippet creates an `enriched_doc` containing the `sensor_type` and posts it to the Normalizer API if `NORMALIZER_API_URL` is configured:

```python
import requests
import os

# Load API URL from environment variables
NORMALIZER_API_URL = os.environ.get("NORMALIZER_API_URL")

# enriched_doc: original parsed data (contains sensor_id) plus sensor_type
enriched_doc = dict(data)
enriched_doc.update({"sensor_type": COLLECTION})


if NORMALIZER_API_URL:
   try:
       print(f"Sending data to {NORMALIZER_API_URL}: {enriched_doc}")
       
       # Post to the Normalizer API webhook endpoint
       r = requests.post(NORMALIZER_API_URL + "/webhook", json=enriched_doc, timeout=10)
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
   print("WARNING: NORMALIZER_API_URL not set. Skipping forwarding.")
```
Once the environment variable and the forwarding logic are in place for a Cloud Run service, that service will forward enriched sensor events to the Normalizer API.

### Changing supported sensor_id or timestamp fields:
To change the supported `sensor_id` or `timestamp` fields for incoming data, modify the `POSSIBLE_SENSOR_ID_FIELDS` and `POSSIBLE_TIMESTAMP_FIELDS` tuples in the `SensorDataParser.py` file.

### API Documentation:
The project's API documentation is automatically generated using Swagger and is available at the `/docs` endpoint of the running Normalizer API instance. For example, if the Normalizer API is hosted at `https://normalizer-api-xxxxxxx.run.app`, the API documentation can be accessed at `https://normalizer-api-xxxxxxx.run.app/docs`.


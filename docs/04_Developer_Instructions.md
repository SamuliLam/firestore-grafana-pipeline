# Normalizer API Project Summary

---

## Table of Contents

1.  [Introduction](#1-introduction)
2.  [Project Documentation Overview](#2-project-documentation-overview)
3.  [Implemented Features / Out of Scope / Not Implemented](#3-implemented-features--out-of-scope--not-implemented)
4.  [Instructions for Future Development](#4-instructions-for-future-development)
    * [Local installation](#local-installation)
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
* Responsive frontend that is supported by differenct screen sizes

## 4. Instructions for Future Development

### Local installation:
For instructions on setting up the project locally, please refer to the Installation and User Guide located at: [README.md](../README.md)

### API Documentation:
The project's API documentation is automatically generated using Swagger and is available at the `/docs` endpoint of the running Normalizer API instance. For example, if the Normalizer API is hosted at `https://normalizer-api-xxxxxxx.run.app`, the API documentation can be accessed at `https://normalizer-api-xxxxxxx.run.app/docs`.


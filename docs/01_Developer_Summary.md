## Summary Report and Instructions for future Development
### 1. Introduction

This project implements a data ingestion pipeline and a frontend visualization system for IoT sensor data. The system ingests both historical and live sensor measurements from Google Cloud Firestore collections into a local TimescaleDB instance. Live data is received through a REST API, while historical data can be synchronized on demand.

The TimescaleDB database is configured as a data source in Grafana and is used to visualize common sensor metrics such as temperature, humidity, and air pressure. The frontend application embeds prebuilt Grafana dashboards to present these metrics to the user. Additional dashboards can be created directly in Grafana by defining new SQL queries on the sensor data. This allows developers and advanced users to explore new metrics without modifying the backend or frontend code.

The system is designed to be extensible, allowing new sensors, metrics, and visualizations to be added with minimal changes to the existing architecture.

### 2. Project Documentation Overview

- Functional Specification  
  Describes user stories, acceptance criteria, and non-functional requirements.  
  Location: docs/[02_Functional_Specification.md](02_Functional_Specification.md)

- Technical Implementation Documentation  
  Describes system architecture, components, database design, and APIs.  
  Location: docs/[03_Technical_Architecture.md](03_Technical_Architecture.md)

- Testing Report  
  Details test cases, results, and coverage analysis.  
  Location: docs/[04_Testing_Report.md](04_Testing_Report.md)

- Installation and User Guide  
  Instructions for setting up and running the system.  
  Location: README.md

### 3. Implemented Features / Out of Scope / Not Implemented
Implemented:
- Live sensor data ingestion via REST API
- On-demand historical data synchronization from Firestore
- Sensor metadata management via frontend UI
- Visualization of sensor metrics using embedded Grafana dashboards
- Visualization of sensor metadata using geo-mapping features in Grafana

Out of Scope / Not Implemented:
- User authentication and role-based access control (planned but not implemented)
- Alerting and notifications in Grafana

### 4. 
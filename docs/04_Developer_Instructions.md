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

This project implements a hybrid cloud data ingestion pipeline and a frontend visualization system for IoT sensor data. The system ingests dynamic sensor measurements via a Google Cloud Run service, which processes and routes data to Firestore. The Backend API then synchronizes this data into a local TimescaleDB instance for Grafana visualization.

The system utilizes Grafana as its primary visualization engine, embedding dynamic dashboards and Geomaps directly into a React-based frontend. The architecture is designed to be highly extensible, supporting any new sensor metrics through a dynamic EAV (Entity-Attribute-Value) database schema and user-defined mapping logic.

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
* **Dynamic Metric Mapping:** Administrators can define how raw sensor JSON keys map to human-readable metrics through the UI.
* **Discovery Mode:** Automatic capture of "Unknown Sensors" into a dedicated discovery list for easy onboarding.
* **Historical Data Backfill:** On-demand synchronization and re-processing of historical data from Firestore to TimescaleDB after sensor configuration.
* **Secure Authentication:** Integrated **Auth0** framework with role-based access control (RBAC) and an "Authentication Guard" for protected routes.
* **Advanced Visualization:** Dynamic Grafana Dashboards and Geomaps embedded via iframes with automatic refresh logic.

### 🚫 Out of Scope / Not Implemented:
* **Automated CI/CD:** Deployment currently requires manual submodule updates on the Metropolia VM (see Future Development).
* **Sensor Config Profiles:** No predefined profiles for common sensor types(Ruuvitag, Teros.); all mapping configurations are manual.
* **Real-time Alerts:** No alerting or notification system based on sensor thresholds or anomalies.

## 4. Instructions for Future Development

### Local installation:
For instructions on setting up the project locally, please refer to the Installation and User Guide located at: [README.md](../README.md)

### API Documentation:
The project's API documentation is automatically generated using Swagger and is available at the `/docs` endpoint of the running Normalizer API instance. For example, if the Normalizer API is hosted at `https://normalizer-api-xxxxxxx.run.app`, the API documentation can be accessed at `https://normalizer-api-xxxxxxx.run.app/docs`.

### Grafana:
To modify or create new Grafana dashboards, access grafana at `http://localhost:3000` (or the appropriate URL if hosted elsewhere). Use the admin credentials defined in .env file to log in. Also make sure that GF_AUTH_DISABLE_LOGIN_FORM is not set to true in the docker compose file, otherwise you will not be able to log in to grafana.
Once modified, export the dashboard JSON and update the corresponding files in the `grafana/dashboards` directory of the project. This will ensure that the new or modified dashboards are included in the deployment process and available in the production environment.

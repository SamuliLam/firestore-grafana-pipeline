## 6. System Requirements

### 6.1 Functional Requirements

The system allows users to add sensors with coordinates, as well as search for, delete, and edit existing sensors. It provides comprehensive visualization of sensor data through dashboards, gauges, and graphs, enabling users to easily interpret and monitor sensor readings. Additionally, the system supports exporting data to CSV files, making it convenient to analyze the information further in tools such as Excel.

### 6.2 Non-Functional Requirements

The system was implemented with a clear and user-friendly interface, ensuring that even new users can navigate it easily. Navigation is logical, and essential features can be found without difficulty. The map view and the sensor table beneath it refresh quickly, and sensor visualizations are presented clearly on dashboards without requiring technical expertise.

The system was designed to be reliable by properly handling error situations and displaying clear error messages to the user. Data stored in TimescaleDB remains consistent and intact even in the event of errors.

Security was ensured by requiring the backend to use a Google Cloud Run API key, and access to the system is restricted to VPN connections using Metropolia credentials. Invalid API calls are rejected to prevent misuse.

Maintainability was achieved by keeping the frontend and backend as separate components, allowing them to be updated independently. Key parts of the codebase are documented.

The system was implemented as a browser-based application so it can be used without local installations. The application is compatible with major browsers such as Chrome and Firefox, and functions consistently across different workstation environments.





### 7. Flowchart

```mermaid
graph TD
    A[IoT Sensors] -->|Publish JSON data| B[Google Cloud Pub/Sub Topics]
    B -->|Trigger events| C[Cloud Run Services]
    C -->|Parse & enrich| D[Firestore Collections]
    C -->|Forward enriched data| E[Normalizer REST API]
    D -->|Forward history data| E[Normalizer REST API]
    E -->|Process & normalize| F[SensorDataParser]
    F -->|EAV format| G[TimescaleDB]
    G -->|SQL queries| H[Grafana Dashboards]
    H -->|Embedded iframes| I[Frontend Application]
    
    style A fill:#4FC3F7,stroke:#0288D1,stroke-width:2px,color:#fff
style B fill:#FFD54F,stroke:#FFA000,stroke-width:2px,color:#333
style C fill:#F06292,stroke:#C2185B,stroke-width:2px,color:#fff
style D fill:#81C784,stroke:#388E3C,stroke-width:2px,color:#fff
style E fill:#BA68C8,stroke:#6A1B9A,stroke-width:2px,color:#fff
style F fill:#E57373,stroke:#B71C1C,stroke-width:2px,color:#fff
style G fill:#AED581,stroke:#689F38,stroke-width:2px,color:#333
style H fill:#FFF176,stroke:#FBC02D,stroke-width:2px,color:#333
style I fill:#7986CB,stroke:#283593,stroke-width:2px,color:#fff
```
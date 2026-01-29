CREATE TABLE IF NOT EXISTS sensor_metadata (
    sensor_id VARCHAR(50) PRIMARY KEY NOT NULL,
    description TEXT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    sensor_type VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_data (
    timestamp TIMESTAMPTZ NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value TEXT NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    PRIMARY KEY (timestamp, sensor_id, metric_name)
);

-- Luodaan hypertable TimescaleDB:ssä
SELECT create_hypertable('sensor_data', 'timestamp', if_not_exists => TRUE);

CREATE USER grafana_ro WITH PASSWORD 'secure_password';

-- grant connection to the database
GRANT CONNECT ON DATABASE sensor_data TO grafana_ro;

-- grant usage and select on public schema (replace public with your schema if needed)
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO grafana_ro;

-- ensure future tables are readable
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;


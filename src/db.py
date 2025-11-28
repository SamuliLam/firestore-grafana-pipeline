import time
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, text, Column, String, Float, DateTime, Text, func
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import OperationalError

DB_HOST = "timescaledb"
DB_PORT = "5432"
DB_USER = "admin"
DB_PASSWORD = "admin"
DB_NAME = "sensor_data"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()
ENGINE: Optional[create_engine] = None


class SensorMetadata(Base):
    """Sensor metadata table"""
    __tablename__ = "sensor_metadata"
    sensor_id = Column(String(50), primary_key=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sensor_type = Column(String(50), nullable=False)


class SensorData(Base):
    """EAV-style sensor data table"""
    __tablename__ = "sensor_data"
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    sensor_id = Column(String(50), primary_key=True, nullable=False)
    metric_name = Column(String(100), primary_key=True, nullable=False)
    metric_value = Column(Text, nullable=False)
    sensor_type = Column(String(50), nullable=False)


# Database Functions
def get_engine(max_retries=10, delay=5):
    """Create or reuse DB engine with retry logic."""
    global ENGINE
    if ENGINE is not None:
        return ENGINE
    for attempt in range(max_retries):
        try:
            ENGINE = create_engine(DATABASE_URL)
            ENGINE.connect()
            print("Connected to TimescaleDB.")
            return ENGINE
        except OperationalError as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise ConnectionError("Failed to connect to TimescaleDB after multiple attempts.")


def init_db():
    """Initialize tables and hypertable."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(f"""
            SELECT create_hypertable('{SensorData.__tablename__}', 'timestamp',
                                     chunk_time_interval => interval '1 week',
                                     if_not_exists => TRUE,
                                     migrate_data => TRUE);
        """))
        conn.commit()
    print("Database initialized with sensor_metadata and sensor_data tables.")


def sensor_exists_in_data(sensor_id: str) -> bool:
    """Check if a sensor_id exists in the sensor_data table."""
    engine = get_engine()
    with Session(engine) as session:
        result = session.query(SensorData).filter(
            SensorData.sensor_id == sensor_id
        ).first()
        return result is not None


def insert_sensor_metadata(metadata_rows: list[dict]):
    """Insert sensor metadata rows. Validates that sensor_id exists in sensor_data table."""
    engine = get_engine()
    with Session(engine) as session:
        for row in metadata_rows:
            #sensor_id = row.get("sensor_id") if isinstance(row, dict) else row.sensor_id

            # Check if sensor_id exists in sensor_data table
            #if not sensor_exists_in_data(sensor_id):
            #    raise ValueError(f"Sensor {sensor_id} does not exist in sensor_data table")

            if isinstance(row, dict):
                row = SensorMetadata(**row)
            session.merge(row)

        session.commit()
        print(f"Saved {len(metadata_rows)} rows to sensor_metadata.")


def insert_sensor_rows(model, dict_rows: list[dict]):
    """Insert sensor data rows directly into the database."""
    engine = get_engine()
    with Session(engine) as session:
        for row in dict_rows:
            if isinstance(row, dict):
                row = model(**row)
            elif not isinstance(row, model):
                raise TypeError(
                    f"Row must be a dict or {model.__tablename__} instance, got {type(row)}"
                )
            session.merge(row)

        session.commit()
        print(f"Saved {len(dict_rows)} rows to table {model.__tablename__}.")


def delete_sensor(sensor_id: str):
    engine = get_engine()
    with Session(engine) as session:
        deleted = session.query(SensorMetadata).filter(
            SensorMetadata.sensor_id == sensor_id
        ).delete()

        session.commit()

        return deleted


def get_oldest_collection_timestamp_from_db(collection_name: str) -> Optional[datetime]:
    engine = get_engine()
    with Session(engine) as session:
        oldest = (
            session.query(func.min(SensorData.timestamp))
            .filter(SensorData.sensor_type == collection_name)
            .scalar()
        )
        return oldest

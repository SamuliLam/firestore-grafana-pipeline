import os
import time
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, String, Float, DateTime, Text, func, insert
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert

DATABASE_URL = os.getenv("POSTGRES_URL")

Base = declarative_base()
ENGINE: Optional[create_engine] = None


class SensorMetadata(Base):
    """Sensor metadata table"""
    __tablename__ = "sensor_metadata"
    sensor_id = Column(String(50), primary_key=True, nullable=False)
    description = Column(Text, nullable=True)
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
    """Initialize database connection."""
    engine = get_engine()
    with engine.connect() as conn:
        print("Database connection verified.")


def sensor_exists_in_data(sensor_id: str) -> bool:
    """Check if a sensor_id exists in the sensor_data table."""
    engine = get_engine()
    with Session(engine) as session:
        result = session.query(SensorData).filter(
            SensorData.sensor_id == sensor_id
        ).first()
        return result is not None


def get_all_sensor_metadata() -> list[dict]:
    """Retrieve all sensor metadata as a list of dictionaries."""
    engine = get_engine()
    with Session(engine) as session:
        results = session.query(SensorMetadata).all()
        return [
            {
                "sensor_id": row.sensor_id,
                "description": row.description,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "sensor_type": row.sensor_type,
            }
            for row in results
        ]


def insert_sensor_metadata(metadata_rows: list[dict]):
    """Insert sensor metadata rows. Validates that sensor_id exists in sensor_data table."""
    engine = get_engine()
    with Session(engine) as session:
        for row in metadata_rows:
            if isinstance(row, dict):
                row = SensorMetadata(**row)
            session.merge(row)

        session.commit()
        print(f"Saved {len(metadata_rows)} rows to sensor_metadata.")


def insert_sensor_rows(dict_rows: list[dict]):
    """Insert sensor data rows directly into the database."""
    engine = get_engine()
    with engine.begin() as connection:
        stmt = insert(SensorData).values(dict_rows)

        on_conflict_stmt = stmt.on_conflict_do_nothing(
            index_elements=['timestamp', 'sensor_id', 'metric_name']
        )

        connection.execute(on_conflict_stmt)
        print(f"Saved {len(dict_rows)} rows to table {SensorData.__tablename__}.")


def delete_sensor(sensor_id: str):
    engine = get_engine()
    with Session(engine) as session:
        deleted = session.query(SensorMetadata).filter(
            SensorMetadata.sensor_id == sensor_id
        ).delete()

        session.commit()

        return deleted


def get_oldest_timestamp_from_db(collection_name: str) -> Optional[datetime]:
    engine = get_engine()
    with Session(engine) as session:
        oldest = (
            session.query(func.min(SensorData.timestamp))
            .filter(SensorData.sensor_type == collection_name)
            .scalar()
        )
        return oldest


def get_newest_timestamp_from_db(collection_name: str) -> Optional[datetime]:
    engine = get_engine()
    with Session(engine) as session:
        newest = (
            session.query(func.max(SensorData.timestamp))
            .filter(SensorData.sensor_type == collection_name)
            .scalar()
        )
        return newest

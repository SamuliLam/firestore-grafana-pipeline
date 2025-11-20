# src/db.py
import time
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    create_engine, text, Column, String, Float, DateTime, Text
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert

DB_HOST = "timescaledb"
DB_PORT = "5432"
DB_USER = "admin"
DB_PASSWORD = "admin"
DB_NAME = "sensor_data"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
Base = declarative_base()
ENGINE: Optional[create_engine] = None


class SensorData(Base):
    """EAV-style sensor data table"""
    __tablename__ = "sensor_data"

    timestamp = Column(DateTime, primary_key=True, nullable=False)
    sensor_id = Column(String(50), primary_key=True, nullable=False)
    metric_name = Column(String(100), primary_key=True, nullable=False)
    metric_value = Column(Text, nullable=False)
    source = Column(String(50)) # esim viherpysäkki tai ympäristömoduuli

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
    """Initialize table and hypertable."""
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

    print("Database initialized with sensor_data.")


def insert_sensor_rows(model, dict_rows: list[dict]):
    """Insert sensor data rows directly into the database."""
    engine = get_engine()

    with Session(engine) as session:

        for row in dict_rows:

            if isinstance(row, dict):
                row = model(**row)
            elif not isinstance(row, model):
                raise TypeError(
                    f"Row must be a dict or {model.__tablename__} instace, got {type(row)}"
                )

            session.merge(row)
        
        session.commit()
        print(f"Saved {len(dict_rows)} rows to table {model.__tablename__}.")

def get_oldest_timestamp_from_db() -> Optional[datetime]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT MIN(timestamp) FROM {SensorData.__tablename__}"))
        return result.scalar()

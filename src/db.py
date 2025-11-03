import pandas as pd
import io
from sqlalchemy import create_engine, Column, String, text, Float, DateTime, select
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import OperationalError
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert  # Key for ON CONFLICT
import time
from typing import Optional

DB_HOST = "timescaledb"
DB_PORT = "5432"
DB_USER = "admin"
DB_PASSWORD = "admin"
DB_NAME = "sensor_data"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Base class for declarative table mapping
Base = declarative_base()


class SensorData(Base):
    """
    SQLAlchemy ORM Model representing the 'sensor_data' table.
    """
    __tablename__ = 'sensor_data'

    # TimescaleDB requires a timestamp column which acts as the PRIMARY KEY
    timestamp = Column(DateTime, primary_key=True, nullable=False)

    # Sensor ID acts as the space dimension in a TimescaleDB hypertable
    sensor_id = Column(String(50), primary_key=True, nullable=False)

    # Geographical data usually "Zone 2" or "Bottom"
    zone = Column(String(20))
    location = Column(String(20))

    temperature = Column(Float)  # eg. 24.34
    humidity = Column(Float)  # eg. 67 %


# Singleton engine
ENGINE: Optional[create_engine] = None


def get_engine(max_retries=10, delay=5):
    global ENGINE
    if ENGINE is not None:
        return ENGINE

    for attempt in range(max_retries):
        try:
            ENGINE = create_engine(DATABASE_URL)
            ENGINE.connect()
            print("Successfully connected to TimescaleDB.")
            return ENGINE
        except OperationalError as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise ConnectionError("Failed to connect to TimescaleDB after multiple attempts.")


def init_db():
    """
    Kutsutaan sovelluksen startupissa.
    Luo tarvittavat taulut ja hypertablen.
    """
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
    print("Database initialized and hypertable created (if not exists).")


def insert_sensor_rows(rows: list):
    engine = get_engine()
    with Session(engine) as session:
        for row in rows:
            session.merge(row)  # Upsert
        session.commit()
        print(f"Saved {len(rows)} rows to database.")


def get_oldest_timestamp_from_db() -> Optional[datetime]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT MIN(timestamp) FROM {SensorData.__tablename__}"))
        return result.scalar()
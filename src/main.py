import pandas as pd
import io
from sqlalchemy import create_engine, Column, String, text, Float, DateTime, select
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert # Key for ON CONFLICT
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
    
    temperature = Column(Float) # eg. 24.34
    humidity = Column(Float) # eg. 67 %

# Helper function to clean the sensor ID string from the CSV
def clean_sensor_id(sensor_value: str) -> str:
    """Removes curly braces and single quotes from the sensor string."""
    return str(sensor_value).replace("{", "").replace("}", "").replace("'", "").strip()


def create_hypertable(engine):
    """Converts the 'sensor_data' table into a TimescaleDB hypertable."""
    # This SQL command tells TimescaleDB to manage the table as a time-series hypertable.
    sql = text(f"""
    SELECT create_hypertable('{SensorData.__tablename__}', 'timestamp', 
                             chunk_time_interval => interval '1 week', 
                             if_not_exists => TRUE,
                             migrate_data => TRUE);
    """)
    with engine.connect() as connection:
        connection.execute(sql)
        connection.commit()
    print("Successfully converted 'sensor_data' to a TimescaleDB hypertable.")


def get_db_engine(max_retries=10, delay=5) -> Optional[create_engine]:
    """Tries to create a database engine with a retry mechanism."""
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to TimescaleDB... (Attempt {attempt + 1}/{max_retries})")
            # The 'postgresql' dialect requires the 'psycopg2' library
            engine = create_engine(DATABASE_URL)
            engine.connect() # Try to connect to raise an exception if it fails
            print("Successfully connected to TimescaleDB.")
            return engine
        except Exception as e:
            print(f"Connection failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Failed to connect to TimescaleDB after multiple retries.")
                return None


def insert_sensor_rows(rows):

    engine = get_db_engine()
    if engine is None:
        return

    Base.metadata.create_all(engine)
    create_hypertable(engine)

    with Session(engine) as session:
        for row in rows:
            session.merge(row)
        session.commit()
        print(f"Tallennettu {len(rows)} riviä tietokantaan.")

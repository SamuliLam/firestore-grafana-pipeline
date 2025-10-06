import pandas as pd
import io
from sqlalchemy import create_engine, Column, String, Float, DateTime, select
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
    sql = f"""
    SELECT create_hypertable('{SensorData.__tablename__}', 'timestamp', 
                             chunk_time_interval => interval '1 week', 
                             if_not_exists => TRUE,
                             migrate_data => TRUE);
    """
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


def load_csv_to_orm():
    """Reads the CSV, cleans the data, and loads them into the database using ON CONFLICT DO NOTHING."""

    # 1. Connect to DB
    engine = get_db_engine()
    if engine is None:
        return

    # 2. Setup Schema (Table and Hypertable)
    # NOTE: It's important to run this every time in case the table was dropped/volume cleared.
    Base.metadata.create_all(engine)
    create_hypertable(engine)

    # 3. Load Data
    try:
        # Use the file name from your project environment, not the analysis file name
        df = pd.read_csv('kerabit_sensor_data.csv') 
    except FileNotFoundError:
        print("ERROR: 'kerabit_sensor_data.csv' not found. Ensure it's mounted correctly.")
        return

    # --- Data Preparation for Bulk Insert ---
    # Apply cleaning to the 'sensor' column and rename it to 'sensor_id' to match the ORM model
    df['sensor_id'] = df['sensor'].apply(clean_sensor_id)
    
    # Ensure timestamp is a datetime object
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Select only the columns corresponding to the ORM model for insertion
    data_to_insert = df[['timestamp', 'sensor_id', 'zone', 'location', 'temperature', 'humidity']]
    
    # Convert DataFrame to a list of dictionaries for efficient bulk insertion
    records = data_to_insert.to_dict(orient='records')
    
    print(f"Preparing to insert {len(records)} records into the database...")

    # 4. Perform Insert with Conflict Handling
    
    # Create the INSERT statement
    insert_stmt = insert(SensorData.__table__).values(records)
    
    # Add the ON CONFLICT DO NOTHING clause using the primary key columns
    on_conflict_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements=['timestamp', 'sensor_id']
    )
    
    # Execute the statement
    with engine.connect() as connection:
        # Execute the bulk insert statement
        connection.execute(on_conflict_stmt)
        connection.commit()
        print("Data loading complete. Duplicate records were skipped (ON CONFLICT DO NOTHING).")
            

if __name__ == "__main__":
    load_csv_to_orm()
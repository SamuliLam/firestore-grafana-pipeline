import pytest
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import (
    create_engine, text, Column, String, Float, DateTime, Text, func
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.exc import OperationalError

from src.db import (
    Base,
    SensorMetadata,
    SensorData,
    get_engine,
    insert_sensor_rows,
    insert_sensor_metadata,
    delete_sensor,
    sensor_exists_in_data,
    get_oldest_collection_timestamp_from_db,
)

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_engine():
    """Creates an in-memory SQLite engine for all tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(autouse=True)
def patch_engine(test_engine):
    """Patch get_engine() so it always returns our in-memory DB."""
    with patch("src.db.get_engine", return_value=test_engine):
        yield


@pytest.fixture
def session(test_engine):
    """Creates a fresh DB session per test."""
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    yield s
    s.close()

    # Clean up all tables using SQLAlchemy 2.x style
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())



# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------

def test_insert_sensor_rows(session):
    ts = datetime.utcnow()

    insert_sensor_rows(
        SensorData,
        [
            {
                "timestamp": ts,
                "sensor_id": "S1",
                "metric_name": "temp",
                "metric_value": "22.5",
                "sensor_type": "climate",
            }
        ],
    )

    result = session.query(SensorData).filter_by(sensor_id="S1").first()
    assert result is not None
    assert result.metric_value == "22.5"


def test_sensor_exists_in_data(session):
    ts = datetime.utcnow()
    row = SensorData(
        timestamp=ts,
        sensor_id="S2",
        metric_name="humidity",
        metric_value="44",
        sensor_type="climate",
    )
    session.add(row)
    session.commit()

    assert sensor_exists_in_data("S2") is True
    assert sensor_exists_in_data("UNKNOWN") is False


def test_insert_sensor_metadata(session):
    # Insert sensor_data first so metadata refers to existing sensor
    ts = datetime.utcnow()
    session.add(
        SensorData(
            timestamp=ts,
            sensor_id="S3",
            metric_name="temp",
            metric_value="20",
            sensor_type="climate",
        )
    )
    session.commit()

    insert_sensor_metadata(
        [
            {
                "sensor_id": "S3",
                "latitude": 10.0,
                "longitude": 20.0,
                "sensor_type": "climate",
            }
        ]
    )

    result = session.query(SensorMetadata).filter_by(sensor_id="S3").first()
    assert result is not None
    assert result.latitude == 10.0


def test_insert_sensor_rows_invalid_type():
    # Should raise TypeError for non-dict, non-SensorData objects
    with pytest.raises(TypeError):
        insert_sensor_rows(SensorData, [123])


def test_delete_sensor(session):
    # Insert metadata
    row = SensorMetadata(
        sensor_id="S4", latitude=50, longitude=60, sensor_type="climate"
    )
    session.add(row)
    session.commit()

    deleted_count = delete_sensor("S4")
    assert deleted_count == 1

    assert session.query(SensorMetadata).filter_by(sensor_id="S4").first() is None


def test_get_oldest_collection_timestamp_from_db(session):
    t1 = datetime(2020, 1, 1)
    t2 = datetime(2021, 1, 1)

    session.add_all(
        [
            SensorData(
                timestamp=t2,
                sensor_id="A",
                metric_name="temp",
                metric_value="33",
                sensor_type="climate",
            ),
            SensorData(
                timestamp=t1,
                sensor_id="B",
                metric_name="temp",
                metric_value="30",
                sensor_type="climate",
            ),
        ]
    )
    session.commit()

    result = get_oldest_collection_timestamp_from_db("climate")
    assert result == t1


def test_get_oldest_collection_timestamp_empty(session):
    assert get_oldest_collection_timestamp_from_db("nothing") is None

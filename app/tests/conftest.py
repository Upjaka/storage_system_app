import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.object_model import Base
from services.object_service import get_object


def object_payload(**overrides) -> dict:
    data = {
        'number_in_db': 1,
        'inv_number': 'INV-001',
        'address': 'ул. Тестовая, 1',
        'region_id': None,
        'object_type': 'Склад',
        'ownership': 'Собственность',
        'cost': 1000.0,
        'responsible_id': None,
        'maintenance_mode': 'ежемесячное',
        'system_type': 'АПС',
    }
    data.update(overrides)
    return data


def assert_object_matches_input(db, obj_id: int, expected: dict) -> None:
    obj = get_object(db, obj_id)
    assert obj is not None

    scalar_fields = (
        'number_in_db', 'inv_number', 'address', 'object_type',
        'ownership', 'cost', 'maintenance_mode', 'system_type',
    )
    for field in scalar_fields:
        if field in expected:
            assert getattr(obj, field) == expected[field], field

    if 'region_id' in expected:
        expected_region = expected['region_id']
        if expected_region in (None, ''):
            assert obj.region is None
        elif isinstance(expected_region, str):
            assert obj.region is not None
            assert obj.region.name == expected_region.strip()
        else:
            assert obj.region_id == expected_region

    if 'responsible_id' in expected:
        expected_responsible = expected['responsible_id']
        if expected_responsible in (None, ''):
            assert obj.responsible is None
        elif isinstance(expected_responsible, str):
            assert obj.responsible is not None
            assert obj.responsible.name == expected_responsible.strip()
        else:
            assert obj.responsible_id == expected_responsible


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()

from models.object_model import Region, Responsible
from services.reference_service import (
    get_or_create_region,
    get_or_create_responsible,
    resolve_reference_ids,
)
from services.object_service import create_object
from conftest import assert_object_matches_input, object_payload


def test_get_or_create_region_creates_new_row(db):
    region_id = get_or_create_region(db, 'Новый регион')
    db.commit()

    region = db.query(Region).filter(Region.id == region_id).one()
    assert region.name == 'Новый регион'
    assert db.query(Region).count() == 1


def test_get_or_create_region_reuses_existing(db):
    first_id = get_or_create_region(db, 'Москва')
    db.commit()
    second_id = get_or_create_region(db, 'Москва')
    db.commit()

    assert first_id == second_id
    assert db.query(Region).count() == 1


def test_get_or_create_responsible_creates_new_row(db):
    responsible_id = get_or_create_responsible(db, 'Иванов')
    db.commit()

    responsible = db.query(Responsible).filter(Responsible.id == responsible_id).one()
    assert responsible.name == 'Иванов'
    assert db.query(Responsible).count() == 1


def test_get_or_create_responsible_reuses_existing(db):
    first_id = get_or_create_responsible(db, 'Петров')
    db.commit()
    second_id = get_or_create_responsible(db, 'Петров')
    db.commit()

    assert first_id == second_id
    assert db.query(Responsible).count() == 1


def test_resolve_reference_ids_with_region_name_string(db):
    resolved = resolve_reference_ids(db, {'region_id': 'Санкт-Петербург'})

    assert 'region' not in resolved
    assert isinstance(resolved['region_id'], int)
    assert db.query(Region).filter(Region.name == 'Санкт-Петербург').one().id == resolved['region_id']


def test_resolve_reference_ids_empty_string_becomes_none(db):
    resolved = resolve_reference_ids(db, {'region_id': '', 'responsible_id': ''})

    assert resolved['region_id'] is None
    assert resolved['responsible_id'] is None


def test_resolve_reference_ids_with_integer_id(db):
    region_id = get_or_create_region(db, 'Казань')
    db.commit()

    resolved = resolve_reference_ids(db, {'region_id': region_id})

    assert resolved['region_id'] == region_id


def test_new_region_name_persisted_not_replaced_by_existing(db):
    get_or_create_region(db, 'Москва')
    db.commit()

    payload = object_payload(
        region_id='Новый регион XYZ',
        responsible_id='Новый ответственный ABC',
    )
    obj = create_object(db, payload)

    assert_object_matches_input(db, obj.id, payload)
    assert db.query(Region).count() == 2
    assert db.query(Responsible).count() == 1
    assert db.query(Region).filter(Region.name == 'Новый регион XYZ').count() == 1

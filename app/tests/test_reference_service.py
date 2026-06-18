from models.object_model import Region, Responsible
from services.reference_service import (
    create_region,
    create_responsible,
    delete_region,
    delete_responsible,
    get_or_create_region,
    get_or_create_responsible,
    resolve_reference_ids,
    update_region,
    update_responsible,
)
from services.object_service import create_object
from conftest import assert_object_matches_input, object_payload
import pytest


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


def test_create_region_persists_row(db):
    region = create_region(db, 'Тула')
    db.commit()

    assert region.id is not None
    assert region.name == 'Тула'
    assert db.query(Region).count() == 1


def test_create_region_rejects_blank_name(db):
    with pytest.raises(ValueError, match='пустым'):
        create_region(db, '   ')


def test_update_region_renames_row(db):
    region = create_region(db, 'Старый')
    db.commit()

    updated = update_region(db, region.id, 'Новый')
    db.commit()

    assert updated.name == 'Новый'
    assert db.query(Region).filter(Region.id == region.id).one().name == 'Новый'


def test_delete_region_removes_unused_row(db):
    region = create_region(db, 'Удаляемый')
    db.commit()

    delete_region(db, region.id)
    db.commit()

    assert db.query(Region).count() == 0


def test_delete_region_blocked_when_referenced(db):
    region = create_region(db, 'Москва')
    db.commit()
    create_object(db, object_payload(region_id=region.id))
    db.commit()

    with pytest.raises(ValueError, match='привязаны объекты'):
        delete_region(db, region.id)


def test_create_responsible_persists_row(db):
    responsible = create_responsible(db, 'Сидоров')
    db.commit()

    assert responsible.id is not None
    assert responsible.name == 'Сидоров'
    assert db.query(Responsible).count() == 1


def test_update_responsible_renames_row(db):
    responsible = create_responsible(db, 'Иванов')
    db.commit()

    updated = update_responsible(db, responsible.id, 'Петров')
    db.commit()

    assert updated.name == 'Петров'
    assert db.query(Responsible).filter(Responsible.id == responsible.id).one().name == 'Петров'


def test_delete_responsible_removes_unused_row(db):
    responsible = create_responsible(db, 'Удаляемый')
    db.commit()

    delete_responsible(db, responsible.id)
    db.commit()

    assert db.query(Responsible).count() == 0


def test_delete_responsible_blocked_when_referenced(db):
    responsible = create_responsible(db, 'Иванов')
    db.commit()
    create_object(db, object_payload(responsible_id=responsible.id))
    db.commit()

    with pytest.raises(ValueError, match='привязаны объекты'):
        delete_responsible(db, responsible.id)

import pytest
from sqlalchemy.exc import IntegrityError

from models.object_model import Region, Responsible
from services.object_service import (
    create_object,
    update_object,
    get_object,
    get_next_number_in_db,
    get_objects_filtered,
)
from services.reference_service import get_or_create_region, get_or_create_responsible
from services.system_flag_service import set_system_codes
from conftest import assert_object_matches_input, object_payload


def test_create_persists_scalar_fields(db):
    payload = object_payload(
        number_in_db=5,
        inv_number='INV-100',
        address='ул. Примерная, 10',
        object_type='Офис',
        ownership='Аренда',
        cost=2500.50,
        maintenance_mode='квартальное',
        system_type='СОУЭ',
    )
    obj = create_object(db, payload)

    assert_object_matches_input(db, obj.id, payload)


def test_create_with_new_region_and_responsible_names(db):
    payload = object_payload(
        region_id='Екатеринбург',
        responsible_id='Сидоров',
    )
    obj = create_object(db, payload)

    assert_object_matches_input(db, obj.id, payload)
    assert db.query(Region).filter(Region.name == 'Екатеринбург').count() == 1
    assert db.query(Responsible).filter(Responsible.name == 'Сидоров').count() == 1


def test_create_links_existing_region_and_responsible(db):
    region_id = get_or_create_region(db, 'Москва')
    responsible_id = get_or_create_responsible(db, 'Иванов')
    db.commit()

    payload = object_payload(
        inv_number='INV-002',
        number_in_db=2,
        region_id='Москва',
        responsible_id='Иванов',
    )
    create_object(db, payload)

    assert db.query(Region).count() == 1
    assert db.query(Responsible).count() == 1
    assert db.query(Region).filter(Region.id == region_id).count() == 1
    assert db.query(Responsible).filter(Responsible.id == responsible_id).count() == 1


def test_get_next_number_in_db_empty_then_increment(db):
    assert get_next_number_in_db(db) == 1

    create_object(db, object_payload(number_in_db=1, inv_number='INV-A'))
    assert get_next_number_in_db(db) == 2

    create_object(db, object_payload(number_in_db=7, inv_number='INV-B'))
    assert get_next_number_in_db(db) == 8


def test_create_duplicate_number_in_db_raises(db):
    create_object(db, object_payload(number_in_db=1, inv_number='INV-001'))

    with pytest.raises(IntegrityError):
        create_object(db, object_payload(number_in_db=1, inv_number='INV-002'))


def test_create_duplicate_inv_number_raises(db):
    create_object(db, object_payload(number_in_db=1, inv_number='INV-001'))

    with pytest.raises(IntegrityError):
        create_object(db, object_payload(number_in_db=2, inv_number='INV-001'))


def test_update_scalar_fields(db):
    obj = create_object(db, object_payload())
    payload = object_payload(
        address='ул. Обновлённая, 2',
        cost=5000.0,
        object_type='Здание',
    )
    update_object(db, obj.id, payload)

    assert_object_matches_input(db, obj.id, payload)


def test_update_region_to_new_name_creates_region_row(db):
    obj = create_object(db, object_payload(region_id='Регион A'))
    update_object(db, obj.id, object_payload(region_id='Регион B'))

    loaded = get_object(db, obj.id)
    assert loaded.region.name == 'Регион B'
    assert db.query(Region).count() == 2


def test_update_responsible_to_existing_person(db):
    get_or_create_responsible(db, 'Старый')
    get_or_create_responsible(db, 'Новый')
    db.commit()

    obj = create_object(db, object_payload(responsible_id='Старый'))
    update_object(db, obj.id, object_payload(responsible_id='Новый'))

    loaded = get_object(db, obj.id)
    assert loaded.responsible.name == 'Новый'
    assert db.query(Responsible).count() == 2


def test_update_clears_region_and_responsible_with_empty_string(db):
    obj = create_object(db, object_payload(
        region_id='Регион',
        responsible_id='Ответственный',
    ))

    update_object(db, obj.id, object_payload(region_id='', responsible_id=''))

    loaded = get_object(db, obj.id)
    assert loaded.region is None
    assert loaded.responsible is None
    assert loaded.region_id is None
    assert loaded.responsible_id is None


def test_create_round_trip_input_fidelity(db):
    payload = object_payload(
        number_in_db=3,
        inv_number='INV-ROUNDTRIP',
        address='ул. Круговая, 3',
        region_id='Новосибирск',
        responsible_id='Кузнецов',
        object_type='Склад',
        ownership='Собственность',
        cost=1234.56,
        maintenance_mode='ежемесячное',
        system_type='ВПВ',
    )
    obj = create_object(db, payload)

    assert_object_matches_input(db, obj.id, payload)


def test_get_objects_filtered_by_text_fields(db):
    create_object(db, object_payload(
        number_in_db=101,
        inv_number='INV-ALPHA',
        address='ул. Ленина, 1',
        region_id='Москва',
        responsible_id='Иванов',
        object_type='Офис',
        system_type='АПС',
    ))
    create_object(db, object_payload(
        number_in_db=202,
        inv_number='INV-BETA',
        address='ул. Мира, 2',
        region_id='Казань',
        responsible_id='Петров',
        object_type='Склад',
        system_type='СОУЭ',
    ))

    assert len(get_objects_filtered(db, {'number_in_db': '10'})) == 1
    assert get_objects_filtered(db, {'number_in_db': '10'})[0].number_in_db == 101
    assert len(get_objects_filtered(db, {'inv_number': 'BETA'})) == 1
    assert len(get_objects_filtered(db, {'address': 'Мира'})) == 1
    assert len(get_objects_filtered(db, {'region': 'Моск'})) == 1
    assert len(get_objects_filtered(db, {'responsible': 'Петр'})) == 1
    assert len(get_objects_filtered(db, {'object_type': 'Склад'})) == 1
    assert len(get_objects_filtered(db, {'system_type': 'СОУЭ'})) == 1


def test_get_objects_filtered_by_region_and_responsible_ids(db):
    obj = create_object(db, object_payload(region_id='Самара', responsible_id='Сидоров'))
    db.commit()

    assert len(get_objects_filtered(db, {'region_id': obj.region_id})) == 1
    assert len(get_objects_filtered(db, {'responsible_id': obj.responsible_id})) == 1


def test_get_objects_filtered_matches_secondary_system_flag(db):
    obj = create_object(db, object_payload(system_type='АПС'))
    set_system_codes(db, obj.id, ['АПС', 'ВПВ'])
    db.commit()

    assert len(get_objects_filtered(db, {'system_type': 'ВПВ'})) == 1

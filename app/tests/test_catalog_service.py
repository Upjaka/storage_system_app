import pytest

from models.catalog_model import Material, Unit, WorkType
from services.catalog_service import (
    create_material,
    create_unit,
    create_work_type,
    delete_material,
    delete_unit,
)


def test_create_unit_and_material_with_fk(db):
    unit = create_unit(db, 'шт.')
    material = create_material(db, name='Кабель', unit_id=unit.id, cost=120.5)
    db.commit()

    loaded = db.query(Material).filter(Material.id == material.id).one()
    assert loaded.unit.name == 'шт.'
    assert loaded.cost == 120.5


def test_delete_unit_blocked_when_materials_exist(db):
    unit = create_unit(db, 'м.')
    create_material(db, name='Труба', unit_id=unit.id)
    db.commit()

    with pytest.raises(ValueError, match='привязаны материалы'):
        delete_unit(db, unit.id)


def test_delete_material_blocked_when_work_types_exist(db):
    material = create_material(db, name='Датчик')
    create_work_type(db, name='Замена датчика', material_id=material.id)
    db.commit()

    with pytest.raises(ValueError, match='привязаны виды работ'):
        delete_material(db, material.id)


def test_delete_unit_allowed_when_unused(db):
    unit = create_unit(db, 'компл.')
    db.commit()

    delete_unit(db, unit.id)
    db.commit()

    assert db.query(Unit).count() == 0

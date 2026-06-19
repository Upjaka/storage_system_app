import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.object_model import Base, Object, ObjectSystemFlag
from services.database import _migrate_phase1_schema
from services.object_service import create_object
from services.system_flag_service import (
    get_system_codes,
    primary_system_code,
    set_system_codes,
    sync_flags_from_system_type,
)
from conftest import object_payload


def test_primary_system_code_prefers_first_in_canonical_order():
    assert primary_system_code(['ВПВ', 'АПС', 'СОУЭ']) == 'АПС'
    assert primary_system_code([]) == 'АПС'


def test_set_system_codes_creates_flags(db):
    obj = create_object(db, object_payload(system_type='АПС'))
    set_system_codes(db, obj.id, ['СОУЭ', 'ВПВ', 'АПС'])
    db.commit()

    assert get_system_codes(db, obj.id) == ['АПС', 'СОУЭ', 'ВПВ']


def test_set_system_codes_syncs_legacy_system_type(db):
    obj = create_object(db, object_payload(system_type='АПС'))

    set_system_codes(db, obj.id, ['ВПВ', 'АУГПТ'])
    db.commit()
    db.refresh(obj)

    assert obj.system_type == 'АУГПТ'
    assert get_system_codes(db, obj.id) == ['АУГПТ', 'ВПВ']


def test_invalid_system_code_raises(db):
    obj = create_object(db, object_payload())

    with pytest.raises(ValueError, match='Недопустимый тип системы'):
        set_system_codes(db, obj.id, ['АПС', 'UNKNOWN'])


def test_create_object_creates_flag_from_system_type(db):
    obj = create_object(db, object_payload(system_type='СОУЭ'))

    assert get_system_codes(db, obj.id) == ['СОУЭ']


def test_create_object_with_system_codes(db):
    obj = create_object(db, object_payload(
        system_type='АПС',
        system_codes=['АПС', 'СОУЭ'],
    ))

    assert get_system_codes(db, obj.id) == ['АПС', 'СОУЭ']
    assert obj.system_type == 'АПС'


def test_sync_flags_from_system_type_skips_when_flags_exist(db):
    obj = create_object(db, object_payload(system_type='ВПВ'))
    assert get_system_codes(db, obj.id) == ['ВПВ']

    obj.system_type = 'СОУЭ'
    sync_flags_from_system_type(db, obj.id)
    db.commit()

    assert get_system_codes(db, obj.id) == ['ВПВ']


def test_migration_backfills_flags_from_system_type():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / 'phase1.db'
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)

        session = sessionmaker(bind=engine)()
        session.add(Object(
            number_in_db=1,
            inv_number='INV-MIG',
            address='ул. Миграции, 1',
            ownership='Собственность',
            maintenance_mode='ежемесячное',
            system_type='АУГПТ',
        ))
        session.commit()
        session.close()

        _migrate_phase1_schema(engine)

        verify_session = sessionmaker(bind=engine)()
        obj = verify_session.query(Object).one()
        flags = verify_session.query(ObjectSystemFlag).filter_by(object_id=obj.id).all()
        verify_session.close()
        engine.dispose()

        assert [flag.system_code for flag in flags] == ['АУГПТ']


def test_migration_adds_access_code_column():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / 'phase1_cols.db'
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)

        _migrate_phase1_schema(engine)

        with engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text('PRAGMA table_info(objects)')).fetchall()
            }
        engine.dispose()

        assert 'access_code' in columns

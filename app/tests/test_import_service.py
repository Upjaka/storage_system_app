from pathlib import Path

import pandas as pd
import pyodbc
import pytest

from models.object_model import Object, Region, Responsible
from services.import_service import (
    FIELD_MAPPING,
    IMPORT_DEFAULTS,
    OWNERSHIP_ALIASES,
    import_from_access,
    read_access_table,
)

FIXTURE_DIR = Path(__file__).parent / 'fixtures' / 'access'
FIXTURE_PATH = FIXTURE_DIR / 'РТК.accdb'
TABLE_NAME = 'Объекты'


def _require_access_driver() -> None:
    drivers = [driver for driver in pyodbc.drivers() if 'Access' in driver]
    if not drivers:
        pytest.skip('Microsoft Access ODBC driver is not installed')
    if not FIXTURE_PATH.exists() and not list(FIXTURE_DIR.glob('*.accdb')):
        pytest.skip(f'Access fixture not found in {FIXTURE_DIR}')


def _fixture_path() -> Path:
    if FIXTURE_PATH.exists():
        return FIXTURE_PATH
    return next(FIXTURE_DIR.glob('*.accdb'))


def _expected_ownership(value) -> str:
    if value in OWNERSHIP_ALIASES:
        return OWNERSHIP_ALIASES[value]
    return value


@pytest.fixture
def access_fixture_path() -> Path:
    _require_access_driver()
    return _fixture_path()


def test_import_row_count_matches_access_table(db, access_fixture_path):
    source = read_access_table(str(access_fixture_path), TABLE_NAME)

    count = import_from_access(db, str(access_fixture_path), TABLE_NAME)

    assert count == len(source)
    assert db.query(Object).count() == len(source)


def test_import_creates_all_regions_from_access(db, access_fixture_path):
    source = read_access_table(str(access_fixture_path), TABLE_NAME)
    expected_regions = {str(name).strip() for name in source['region'].dropna()}

    import_from_access(db, str(access_fixture_path), TABLE_NAME)

    actual_regions = {region.name for region in db.query(Region).all()}
    assert actual_regions == expected_regions


def test_import_creates_responsibles_from_lookup_table(db, access_fixture_path):
    source = read_access_table(str(access_fixture_path), TABLE_NAME)
    expected_responsibles = {
        str(name).strip() for name in source['responsible'].dropna()
    }

    import_from_access(db, str(access_fixture_path), TABLE_NAME)

    actual_responsibles = {
        responsible.name for responsible in db.query(Responsible).all()
    }
    assert actual_responsibles == expected_responsibles
    assert actual_responsibles
    assert not any(name.endswith('.0') and name[:-2].isdigit() for name in actual_responsibles)


def test_imported_objects_match_access_source_data(db, access_fixture_path):
    source = read_access_table(str(access_fixture_path), TABLE_NAME)
    import_from_access(db, str(access_fixture_path), TABLE_NAME)

    for _, row in source.iterrows():
        number_in_db = int(row['number_in_db'])
        obj = db.query(Object).filter(Object.number_in_db == number_in_db).one()

        assert obj.inv_number == str(row['inv_number']).strip()
        assert obj.address == row['address']
        assert obj.object_type == row['object_type']
        assert obj.ownership == _expected_ownership(row['ownership'])
        assert obj.cost == float(row['cost'])

        if row['region'] is None or (isinstance(row['region'], float) and pd.isna(row['region'])):
            assert obj.region is None
        else:
            assert obj.region.name == str(row['region']).strip()

        responsible = row['responsible']
        if responsible is None or (isinstance(responsible, float) and pd.isna(responsible)):
            assert obj.responsible is None
        else:
            assert obj.responsible.name == str(responsible).strip()

        assert obj.maintenance_mode == IMPORT_DEFAULTS['maintenance_mode']
        assert obj.system_type == IMPORT_DEFAULTS['system_type']


def test_import_maps_access_columns_using_field_mapping(access_fixture_path):
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={access_fixture_path.resolve()};'
    )
    conn = pyodbc.connect(conn_str)
    try:
        source = pd.read_sql(f'SELECT * FROM [{TABLE_NAME}]', conn)
    finally:
        conn.close()

    mapped_columns = {col for col in source.columns if col in FIELD_MAPPING}
    assert mapped_columns == {
        'Номер в базе',
        'Инвентарный номер',
        'Адрес',
        'Регион',
        'Тип объекта',
        'Собственность',
        'Стоимость',
        'Ответственный',
    }


def test_reimport_updates_without_duplicates(db, access_fixture_path):
    first_count = import_from_access(db, str(access_fixture_path), TABLE_NAME)
    second_count = import_from_access(db, str(access_fixture_path), TABLE_NAME)

    assert first_count == second_count
    assert db.query(Object).count() == first_count

from pathlib import Path

import pandas as pd
import pyodbc
import pytest

from models.catalog_model import MaintenancePrice, Material, Unit, WorkType
from models.object_model import Object, ObjectComposition, Region, Responsible
from models.operations_model import ExtraWork, MaintenanceRecord, ObjectDocuments
from services.import_service import (
    FIELD_MAPPING,
    IMPORT_DEFAULTS,
    OWNERSHIP_ALIASES,
    TABLE_COMPOSITION,
    TABLE_EXTRA_WORKS,
    TABLE_MAINTENANCE,
    TABLE_MAINTENANCE_PRICES,
    TABLE_MATERIALS,
    TABLE_RESPONSIBLES,
    TABLE_SYSTEM_TYPES,
    TABLE_UNITS,
    TABLE_WORK_TYPES,
    import_from_access,
    import_full_access,
    read_access_table,
)
from services.composition_service import get_composition_counts
from services.system_flag_service import get_system_codes

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
        'Код',
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


def _read_access_table_raw(access_fixture_path: Path, table_name: str) -> pd.DataFrame:
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={access_fixture_path.resolve()};'
    )
    conn = pyodbc.connect(conn_str)
    try:
        return pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
    finally:
        conn.close()


def test_import_full_access_sets_access_code(db, access_fixture_path):
    source = _read_access_table_raw(access_fixture_path, TABLE_NAME)

    report = import_full_access(db, str(access_fixture_path))

    assert report.objects == len(source)
    for _, row in source.iterrows():
        obj = db.query(Object).filter(Object.access_code == int(row['Код'])).one()
        assert obj.number_in_db == int(row['Номер в базе'])


def test_import_full_access_system_flags_match_access_table(db, access_fixture_path):
    system_types = _read_access_table_raw(access_fixture_path, TABLE_SYSTEM_TYPES)
    objects = _read_access_table_raw(access_fixture_path, TABLE_NAME)
    inv_to_number = {
        str(row['Инвентарный номер']).strip().lower(): int(row['Номер в базе'])
        for _, row in objects.iterrows()
    }

    import_full_access(db, str(access_fixture_path))

    from services.import_normalization import system_codes_from_type_row

    for _, row in system_types.iterrows():
        inv = str(row['Инвентарный номер']).strip().lower()
        number_in_db = inv_to_number.get(inv)
        if number_in_db is None:
            continue
        obj = db.query(Object).filter(Object.number_in_db == number_in_db).one()
        assert get_system_codes(db, obj.id) == system_codes_from_type_row(row)


def test_import_full_access_responsibles_include_extended_fields(db, access_fixture_path):
    source = _read_access_table_raw(access_fixture_path, TABLE_RESPONSIBLES)
    valid_rows = source.dropna(subset=['ФИО'])
    sample = valid_rows.dropna(subset=['Подразделение']).iloc[0]

    report = import_full_access(db, str(access_fixture_path))

    assert report.responsibles == len(valid_rows)
    responsible = db.query(Responsible).filter(
        Responsible.access_code == int(sample['Код']),
    ).one()
    assert responsible.name == str(sample['ФИО']).strip()[:50]
    assert responsible.department == str(sample['Подразделение']).strip()


def test_import_full_access_region_catalog_loaded(db, access_fixture_path):
    regions_source = _read_access_table_raw(access_fixture_path, 'Справочник Регионов')
    expected = {
        str(name).strip()
        for name in regions_source['Регион'].dropna()
    }

    report = import_full_access(db, str(access_fixture_path))

    assert report.regions == len(expected)
    actual = {region.name for region in db.query(Region).all()}
    assert expected.issubset(actual)


def test_import_full_access_reports_orphan_system_type_rows(db, access_fixture_path):
    report = import_full_access(db, str(access_fixture_path))

    assert report.orphan_system_type_inv_numbers
    assert report.system_flag_objects > 0


def test_import_full_access_reimport_is_idempotent(db, access_fixture_path):
    first = import_full_access(db, str(access_fixture_path))
    second = import_full_access(db, str(access_fixture_path))

    assert first.objects == second.objects
    assert db.query(Object).count() == first.objects
    assert db.query(Region).count() >= first.regions


def test_import_full_access_reimport_is_idempotent_all_tables(db, access_fixture_path):
    first = import_full_access(db, str(access_fixture_path))
    second = import_full_access(db, str(access_fixture_path))

    assert first == second
    assert db.query(Object).count() == first.objects
    assert db.query(Region).count() >= first.regions
    assert db.query(Responsible).count() == first.responsibles
    assert db.query(ObjectComposition).count() == first.compositions
    assert db.query(Unit).count() == first.units
    assert db.query(Material).count() == first.materials
    assert db.query(WorkType).count() == first.work_types
    assert db.query(MaintenancePrice).count() == first.maintenance_prices
    assert db.query(MaintenanceRecord).count() == first.maintenance_records
    assert db.query(ExtraWork).count() == first.extra_works
    assert db.query(ObjectDocuments).count() == first.documents


def test_import_full_access_rolls_back_on_failure(db, access_fixture_path, monkeypatch):
    import services.import_service as import_service

    def fail_documents(*args, **kwargs):
        raise RuntimeError('simulated import failure')

    monkeypatch.setattr(import_service, '_import_documents', fail_documents)

    with pytest.raises(RuntimeError, match='simulated import failure'):
        import_full_access(db, str(access_fixture_path))

    assert db.query(Object).count() == 0
    assert db.query(Region).count() == 0
    assert db.query(MaintenanceRecord).count() == 0


def test_import_full_access_reports_progress_steps(db, access_fixture_path):
    steps: list[tuple[str, int, int]] = []

    import_full_access(
        db,
        str(access_fixture_path),
        on_progress=lambda label, step, total: steps.append((label, step, total)),
    )

    assert steps
    assert steps[-1][1] == steps[-1][2]
    assert steps[-1][0] == 'Готово'


def test_import_report_warning_lines_include_orphans(db, access_fixture_path):
    report = import_full_access(db, str(access_fixture_path))

    assert report.has_warnings
    warning_text = '\n'.join(report.warning_lines())
    assert 'Тип системы' in warning_text
    assert report.missing_composition_inv_numbers == []


def test_import_full_access_composition_row_count(db, access_fixture_path):
    composition_source = _read_access_table_raw(access_fixture_path, TABLE_COMPOSITION)

    report = import_full_access(db, str(access_fixture_path))

    assert report.compositions == len(composition_source)
    assert db.query(ObjectComposition).count() == len(composition_source)


def test_import_full_access_composition_values_match_access(db, access_fixture_path):
    from services.composition_service import counts_from_access_row

    composition_source = _read_access_table_raw(access_fixture_path, TABLE_COMPOSITION)
    objects_source = _read_access_table_raw(access_fixture_path, TABLE_NAME)
    inv_to_number = {
        str(row['Инвентарный номер']).strip().lower(): int(row['Номер в базе'])
        for _, row in objects_source.iterrows()
    }

    import_full_access(db, str(access_fixture_path))

    for _, row in composition_source.head(10).iterrows():
        inv = str(row['Инвентарный номер']).strip().lower()
        number_in_db = inv_to_number.get(inv)
        if number_in_db is None:
            continue
        obj = db.query(Object).filter(Object.number_in_db == number_in_db).one()
        expected = counts_from_access_row(row)
        actual = get_composition_counts(db, obj.id)
        for field, value in expected.items():
            assert actual[field] == value, field


def test_import_full_access_catalog_row_counts(db, access_fixture_path):
    units_source = _read_access_table_raw(access_fixture_path, TABLE_UNITS)
    materials_source = _read_access_table_raw(access_fixture_path, TABLE_MATERIALS)
    work_types_source = _read_access_table_raw(access_fixture_path, TABLE_WORK_TYPES)
    prices_source = _read_access_table_raw(access_fixture_path, TABLE_MAINTENANCE_PRICES)

    valid_units = units_source.dropna(subset=['Ед изм'])
    valid_materials = materials_source.dropna(subset=['Материал'])
    valid_work_types = work_types_source.dropna(subset=['Вид работ'])
    valid_prices = prices_source.dropna(subset=['Наименование оборудования'])

    report = import_full_access(db, str(access_fixture_path))

    assert report.units == len(valid_units)
    assert report.materials == len(valid_materials)
    assert report.work_types == len(valid_work_types)
    assert report.maintenance_prices == len(valid_prices)
    assert db.query(Unit).count() == len(valid_units)
    assert db.query(Material).count() == len(valid_materials)
    assert db.query(WorkType).count() == len(valid_work_types)
    assert db.query(MaintenancePrice).count() == len(valid_prices)


def test_import_full_access_maintenance_and_extra_works(db, access_fixture_path):
    maintenance_source = _read_access_table_raw(access_fixture_path, TABLE_MAINTENANCE)
    extra_works_source = _read_access_table_raw(access_fixture_path, TABLE_EXTRA_WORKS)

    report = import_full_access(db, str(access_fixture_path))

    assert report.maintenance_records == len(maintenance_source)
    assert report.extra_works == len(extra_works_source)
    assert db.query(MaintenanceRecord).count() == len(maintenance_source)
    assert db.query(ExtraWork).count() == len(extra_works_source)
    assert not report.orphan_maintenance_object_codes
    assert not report.orphan_extra_work_object_codes

    sample = db.query(MaintenanceRecord).first()
    assert sample.object.access_code is not None
    assert sample.object_id == sample.object.id

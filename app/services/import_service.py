from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
import pyodbc
from sqlalchemy.orm import Session

from models.catalog_model import MaintenancePrice, Material, Unit, WorkType
from models.object_model import Object, ObjectComposition, Region, Responsible
from models.operations_model import ExtraWork, MaintenanceRecord, ObjectDocuments
from services.composition_service import counts_from_access_row, upsert_composition
from services.import_normalization import (
    is_blank,
    normalize_ownership,
    normalize_region_name,
    system_codes_from_type_row,
)
from services.reference_service import get_or_create_region
from services.system_flag_service import set_system_codes, sync_flags_from_system_type

FIELD_MAPPING = {
    'Номер в базе': 'number_in_db',
    'Инвентарный номер': 'inv_number',
    'Адрес': 'address',
    'Регион': 'region',
    'Тип объекта': 'object_type',
    'Собственность': 'ownership',
    'Стоимость': 'cost',
    'Ответственный': 'responsible',
    'Режим проведения ТО': 'maintenance_mode',
    'Тип системы': 'system_type',
    'Код': 'access_code',
}

IMPORT_DEFAULTS = {
    'maintenance_mode': 'ежемесячное',
    'system_type': 'АПС',
}

OWNERSHIP_ALIASES = {
    'н\\д': 'н/д',
}

TABLE_OBJECTS = 'Объекты'
TABLE_REGIONS = 'Справочник Регионов'
TABLE_RESPONSIBLES = 'Справочник Ответственные'
TABLE_SYSTEM_TYPES = 'Тип системы'
TABLE_OWNERSHIP = 'Справочник Собственность'
TABLE_COMPOSITION = 'Состав объекта'
TABLE_UNITS = 'Справочник Еденицы измерения'
TABLE_MATERIALS = 'Справочник Материалы'
TABLE_WORK_TYPES = 'Справочник Виды работ'
TABLE_MAINTENANCE_PRICES = 'Справочник Стоимость ТО'
TABLE_MAINTENANCE = 'Журнал ТО'
TABLE_EXTRA_WORKS = 'Допработы_2'
TABLE_DOCUMENTS = 'Документы'

DOCUMENT_ACCESS_TO_FIELD = {
    'Паспорт': 'passport',
    'Акт приемки': 'acceptance_act',
    'Акт проверки работоспособности': 'performance_check_act',
    'Дефектная ведомость': 'defect_list',
    'КП': 'commercial_proposal',
    'Акт по установке оборудования': 'installation_act',
    'Журнал': 'journal',
    'Фотобанк': 'photo_bank',
}


ImportProgressCallback = Callable[[str, int, int], None]

_PREVIEW_LIMIT = 5


@dataclass
class ImportReport:
    regions: int = 0
    responsibles: int = 0
    objects: int = 0
    system_flag_objects: int = 0
    compositions: int = 0
    units: int = 0
    materials: int = 0
    work_types: int = 0
    maintenance_prices: int = 0
    maintenance_records: int = 0
    extra_works: int = 0
    documents: int = 0
    unmatched_regions: list[str] = field(default_factory=list)
    orphan_system_type_inv_numbers: list[str] = field(default_factory=list)
    orphan_composition_inv_numbers: list[str] = field(default_factory=list)
    missing_composition_inv_numbers: list[str] = field(default_factory=list)
    orphan_maintenance_object_codes: list[int] = field(default_factory=list)
    orphan_extra_work_object_codes: list[int] = field(default_factory=list)
    orphan_document_inv_numbers: list[str] = field(default_factory=list)

    @property
    def objects_imported(self) -> int:
        return self.objects

    @property
    def has_warnings(self) -> bool:
        return bool(
            self.unmatched_regions
            or self.orphan_system_type_inv_numbers
            or self.orphan_composition_inv_numbers
            or self.missing_composition_inv_numbers
            or self.orphan_maintenance_object_codes
            or self.orphan_extra_work_object_codes
            or self.orphan_document_inv_numbers
        )

    def count_lines(self) -> list[str]:
        return [
            f'Регионов: {self.regions}',
            f'Ответственных: {self.responsibles}',
            f'Объектов: {self.objects}',
            f'Объектов с типами систем: {self.system_flag_objects}',
            f'Составов оборудования: {self.compositions}',
            f'Единиц измерения: {self.units}',
            f'Материалов: {self.materials}',
            f'Видов работ: {self.work_types}',
            f'Стоимостей ТО: {self.maintenance_prices}',
            f'Записей журнала ТО: {self.maintenance_records}',
            f'Допработ: {self.extra_works}',
            f'Документов: {self.documents}',
        ]

    def warning_lines(self) -> list[str]:
        lines: list[str] = []

        def _append(label: str, values: list) -> None:
            if not values:
                return
            preview = ', '.join(str(value) for value in values[:_PREVIEW_LIMIT])
            suffix = f' и ещё {len(values) - _PREVIEW_LIMIT}' if len(values) > _PREVIEW_LIMIT else ''
            lines.append(f'{label} ({len(values)}): {preview}{suffix}')

        _append('Несопоставленные регионы', self.unmatched_regions)
        _append('Строк «Тип системы» без объекта', self.orphan_system_type_inv_numbers)
        _append('Строк «Состав объекта» без объекта', self.orphan_composition_inv_numbers)
        _append('Объекты без состава (есть в Access)', self.missing_composition_inv_numbers)
        _append('Записи ТО без объекта', self.orphan_maintenance_object_codes)
        _append('Допработы без объекта', self.orphan_extra_work_object_codes)
        _append('Строки «Документы» без объекта', self.orphan_document_inv_numbers)
        return lines

    def summary_message(self) -> str:
        message = 'Импорт завершён. ' + ', '.join(
            line.lower() for line in self.count_lines() if line.startswith('Объект')
        )
        if self.has_warnings:
            message += f'. Предупреждений: {len(self.warning_lines())}'
        return message


def _connect_access(mdb_file_path: str):
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        fr'DBQ={mdb_file_path};'
    )
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        raise ConnectionError(f'Не удалось подключиться к Access: {e}') from e


def _read_raw_table(conn, table_name: str) -> pd.DataFrame:
    try:
        return pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
    except Exception as e:
        raise ValueError(f"Ошибка чтения таблицы '{table_name}': {e}") from e


def _find_responsible_lookup_table(conn) -> str | None:
    candidates = [
        row.table_name
        for row in conn.cursor().tables(tableType='TABLE')
        if 'ответствен' in row.table_name.lower()
    ]
    best_name = None
    best_rows = -1
    for name in candidates:
        try:
            lookup_df = pd.read_sql(f'SELECT * FROM [{name}]', conn)
        except Exception:
            continue
        if len(lookup_df.columns) < 2 or len(lookup_df) <= best_rows:
            continue
        best_rows = len(lookup_df)
        best_name = name
    return best_name


def _load_responsible_lookup(conn) -> dict[int, str]:
    lookup_table = _find_responsible_lookup_table(conn)
    if lookup_table is None:
        return {}
    try:
        lookup_df = pd.read_sql(f'SELECT * FROM [{lookup_table}]', conn)
    except Exception:
        return {}
    if lookup_df.empty or len(lookup_df.columns) < 2:
        return {}
    code_col, name_col = lookup_df.columns[0], lookup_df.columns[1]
    lookup: dict[int, str] = {}
    for _, row in lookup_df.iterrows():
        code, name = row[code_col], row[name_col]
        if pd.notna(code) and pd.notna(name):
            lookup[int(code)] = str(name).strip()
    return lookup


def _resolve_responsible_value(value, lookup: dict[int, str]):
    if is_blank(value):
        return None
    if isinstance(value, (int, float)) and not (isinstance(value, float) and pd.isna(value)):
        return lookup.get(int(value))
    text = str(value).strip()
    try:
        as_float = float(text)
        if as_float == int(as_float):
            return lookup.get(int(as_float), text)
    except ValueError:
        pass
    return text


def _normalize_import_row(data: dict, *, valid_ownership: set[str] | None = None) -> dict:
    data = dict(data)
    if data.get('inv_number') is not None:
        data['inv_number'] = str(data['inv_number']).strip()
    if data.get('number_in_db') is not None:
        data['number_in_db'] = int(data['number_in_db'])
    if data.get('access_code') is not None and not pd.isna(data['access_code']):
        data['access_code'] = int(data['access_code'])

    ownership = normalize_ownership(data.get('ownership'), valid_ownership)
    if ownership in OWNERSHIP_ALIASES:
        ownership = OWNERSHIP_ALIASES[ownership]
    if ownership is not None:
        data['ownership'] = ownership

    for field_name, default in IMPORT_DEFAULTS.items():
        if not data.get(field_name):
            data[field_name] = default
    return data


def _prepare_object_data(
    db: Session,
    data: dict,
    *,
    responsible_by_code: dict[int, int] | None = None,
    canonical_regions: list[str] | None = None,
    unmatched_regions: list[str] | None = None,
) -> dict:
    region_name = data.pop('region', None)
    responsible_value = data.pop('responsible', None)

    if canonical_regions is not None:
        resolved_region, matched = normalize_region_name(region_name, canonical_regions)
        if not matched and not is_blank(region_name):
            unmatched_regions.append(str(region_name).strip())
        region_name = resolved_region

    data['region_id'] = get_or_create_region(db, region_name)

    responsible_id = None
    if responsible_by_code is not None and not is_blank(responsible_value):
        try:
            code = int(float(responsible_value))
            responsible_id = responsible_by_code.get(code)
        except (TypeError, ValueError):
            responsible_id = None
    elif not is_blank(responsible_value) and isinstance(responsible_value, str):
        from services.reference_service import get_or_create_responsible
        responsible_id = get_or_create_responsible(db, responsible_value)

    data['responsible_id'] = responsible_id
    return data


def _upsert_object(db: Session, data: dict) -> Object:
    existing = None
    access_code = data.get('access_code')
    if access_code is not None:
        existing = db.query(Object).filter(Object.access_code == access_code).first()
    if existing is None:
        existing = db.query(Object).filter(
            (Object.number_in_db == data['number_in_db']) |
            (Object.inv_number == data['inv_number'])
        ).first()
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return existing
    obj = Object(**data)
    db.add(obj)
    db.flush()
    return obj


def _dataframe_to_objects_df(
    df: pd.DataFrame,
    *,
    responsible_lookup: dict[int, str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.rename(columns={col: FIELD_MAPPING.get(col, col) for col in df.columns})

    model_columns = {c.name for c in Object.__table__.columns}
    reference_columns = {'region', 'responsible'}
    keep_columns = [
        col for col in df.columns
        if col in model_columns or col in reference_columns
    ]
    df = df[keep_columns].copy()

    if responsible_lookup and 'responsible' in df.columns:
        df['responsible'] = df['responsible'].apply(
            lambda value: _resolve_responsible_value(value, responsible_lookup),
        )

    df = df.where(pd.notnull(df), None)

    if 'cost' in df.columns:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)

    df = df.dropna(subset=['number_in_db', 'inv_number'])
    return df


def read_access_table(mdb_file_path: str, table_name: str) -> pd.DataFrame:
    """Read an Access table with the same normalization applied during import."""
    conn = _connect_access(mdb_file_path)
    try:
        df = _read_raw_table(conn, table_name)
        responsible_lookup = _load_responsible_lookup(conn)
    finally:
        conn.close()

    return _dataframe_to_objects_df(df, responsible_lookup=responsible_lookup)


def _load_ownership_values(conn) -> set[str]:
    try:
        df = _read_raw_table(conn, TABLE_OWNERSHIP)
    except ValueError:
        return set()
    if df.empty or 'Тип собственности' not in df.columns:
        return set()
    values = {
        normalize_ownership(value)
        for value in df['Тип собственности'].tolist()
        if not is_blank(value)
    }
    return {value for value in values if value}


def _import_regions_catalog(db: Session, df: pd.DataFrame) -> list[str]:
    if df.empty or 'Регион' not in df.columns:
        return []

    canonical: list[str] = []
    for _, row in df.iterrows():
        name = str(row['Регион']).strip() if not is_blank(row['Регион']) else ''
        if not name:
            continue
        get_or_create_region(db, name)
        if name not in canonical:
            canonical.append(name)
    return canonical


def _import_responsibles_catalog(db: Session, df: pd.DataFrame) -> dict[int, int]:
    if df.empty:
        return {}

    by_code: dict[int, int] = {}
    for _, row in df.iterrows():
        if is_blank(row.get('Код')) or is_blank(row.get('ФИО')):
            continue
        code = int(row['Код'])
        name = str(row['ФИО']).strip()[:50]
        responsible = db.query(Responsible).filter(Responsible.access_code == code).first()
        if responsible is None:
            responsible = db.query(Responsible).filter(Responsible.name == name).first()

        fields = {
            'access_code': code,
            'name': name,
            'department': _optional_str(row.get('Подразделение'), 100),
            'position': _optional_str(row.get('Должность'), 100),
            'email': _optional_str(row.get('Электронная почта'), 100),
            'phone': _optional_str(row.get('Телефон'), 50),
        }
        if responsible is None:
            responsible = Responsible(**fields)
            db.add(responsible)
        else:
            for key, value in fields.items():
                setattr(responsible, key, value)
        db.flush()
        by_code[code] = responsible.id
    return by_code


def _optional_str(value, max_length: int | None) -> str | None:
    if is_blank(value):
        return None
    text = str(value).strip()
    if max_length is None:
        return text
    return text[:max_length]


def _import_objects(
    db: Session,
    df: pd.DataFrame,
    *,
    responsible_by_code: dict[int, int],
    canonical_regions: list[str],
    valid_ownership: set[str],
    unmatched_regions: list[str],
) -> int:
    objects_df = _dataframe_to_objects_df(df)
    if objects_df.empty:
        return 0

    count = 0
    for _, row in objects_df.iterrows():
        data = _normalize_import_row(row.to_dict(), valid_ownership=valid_ownership)
        data = _prepare_object_data(
            db,
            data,
            responsible_by_code=responsible_by_code,
            canonical_regions=canonical_regions,
            unmatched_regions=unmatched_regions,
        )
        obj = _upsert_object(db, data)
        sync_flags_from_system_type(db, obj.id)
        count += 1
    return count


def _import_system_type_flags(db: Session, df: pd.DataFrame) -> tuple[int, list[str]]:
    if df.empty or 'Инвентарный номер' not in df.columns:
        return 0, []

    objects_by_inv = {
        obj.inv_number.strip().lower(): obj
        for obj in db.query(Object).all()
    }
    orphans: list[str] = []
    updated_objects = 0

    for _, row in df.iterrows():
        if is_blank(row.get('Инвентарный номер')):
            continue
        inv_number = str(row['Инвентарный номер']).strip()
        obj = objects_by_inv.get(inv_number.lower())
        if obj is None:
            orphans.append(inv_number)
            continue
        codes = system_codes_from_type_row(row)
        if codes:
            set_system_codes(db, obj.id, codes)
            updated_objects += 1
    return updated_objects, orphans


def _import_compositions(db: Session, df: pd.DataFrame) -> tuple[int, list[str]]:
    if df.empty or 'Инвентарный номер' not in df.columns:
        return 0, []

    objects_by_inv = {
        obj.inv_number.strip().lower(): obj
        for obj in db.query(Object).all()
    }
    orphans: list[str] = []
    imported = 0

    for _, row in df.iterrows():
        if is_blank(row.get('Инвентарный номер')):
            continue
        inv_number = str(row['Инвентарный номер']).strip()
        obj = objects_by_inv.get(inv_number.lower())
        if obj is None:
            orphans.append(inv_number)
            continue
        upsert_composition(db, obj.id, counts_from_access_row(row))
        imported += 1
    return imported, orphans


def _missing_composition_inv_numbers(db: Session, df: pd.DataFrame) -> list[str]:
    if df.empty or 'Инвентарный номер' not in df.columns:
        return []

    composition_invs = {
        str(row['Инвентарный номер']).strip().lower()
        for _, row in df.iterrows()
        if not is_blank(row.get('Инвентарный номер'))
    }
    if not composition_invs:
        return []

    objects_by_inv = {
        obj.inv_number.strip().lower(): obj
        for obj in db.query(Object).all()
        if obj.inv_number and obj.inv_number.strip()
    }
    objects_with_composition = {
        obj.inv_number.strip().lower()
        for obj in db.query(Object).join(ObjectComposition).all()
        if obj.inv_number and obj.inv_number.strip()
    }

    missing: list[str] = []
    for inv in composition_invs:
        if inv in objects_by_inv and inv not in objects_with_composition:
            missing.append(objects_by_inv[inv].inv_number)
    return missing


def _notify_progress(
    on_progress: ImportProgressCallback | None,
    label: str,
    step: int,
    total_steps: int,
) -> None:
    if on_progress is not None:
        on_progress(label, step, total_steps)


def _import_units_catalog(db: Session, df: pd.DataFrame) -> dict[int, int]:
    if df.empty:
        return {}
    by_code: dict[int, int] = {}
    for _, row in df.iterrows():
        if is_blank(row.get('Код')) or is_blank(row.get('Ед изм')):
            continue
        code = int(row['Код'])
        name = str(row['Ед изм']).strip()[:20]
        unit = db.query(Unit).filter(Unit.access_code == code).first()
        if unit is None:
            unit = db.query(Unit).filter(Unit.name == name).first()
        if unit is None:
            unit = Unit(access_code=code, name=name)
            db.add(unit)
        else:
            unit.access_code = code
            unit.name = name
        db.flush()
        by_code[code] = unit.id
    return by_code


def _import_materials_catalog(
    db: Session,
    df: pd.DataFrame,
    units_by_code: dict[int, int],
) -> dict[int, int]:
    if df.empty:
        return {}
    by_code: dict[int, int] = {}
    for _, row in df.iterrows():
        if is_blank(row.get('Код')) or is_blank(row.get('Материал')):
            continue
        code = int(row['Код'])
        name = str(row['Материал']).strip()[:255]
        unit_id = None
        if not is_blank(row.get('Ед изм')):
            unit_id = units_by_code.get(int(row['Ед изм']))
        cost = pd.to_numeric(row.get('Стоимость'), errors='coerce')
        cost = float(cost) if pd.notna(cost) else 0.0
        material = db.query(Material).filter(Material.access_code == code).first()
        fields = {
            'access_code': code,
            'name': name,
            'unit_id': unit_id,
            'cost': cost,
            'defect': _optional_str(row.get('Дефект'), 255),
            'link': _optional_str(row.get('Ссылка'), None),
        }
        if material is None:
            material = Material(**fields)
            db.add(material)
        else:
            for key, value in fields.items():
                setattr(material, key, value)
        db.flush()
        by_code[code] = material.id
    return by_code


def _import_work_types_catalog(
    db: Session,
    df: pd.DataFrame,
    materials_by_code: dict[int, int],
) -> int:
    if df.empty:
        return 0
    imported = 0
    for _, row in df.iterrows():
        if is_blank(row.get('Код')) or is_blank(row.get('Вид работ')):
            continue
        code = int(row['Код'])
        name = str(row['Вид работ']).strip()[:255]
        cost = pd.to_numeric(row.get('Стоимость'), errors='coerce')
        cost = float(cost) if pd.notna(cost) else 0.0
        material_id = None
        if not is_blank(row.get('Материал_1')):
            material_id = materials_by_code.get(int(row['Материал_1']))
        work_type = db.query(WorkType).filter(WorkType.access_code == code).first()
        fields = {
            'access_code': code,
            'name': name,
            'cost': cost,
            'section': _optional_str(row.get('Раздел'), 50),
            'output_text': _optional_str(row.get('Вывод'), 255),
            'material_id': material_id,
        }
        if work_type is None:
            work_type = WorkType(**fields)
            db.add(work_type)
        else:
            for key, value in fields.items():
                setattr(work_type, key, value)
        db.flush()
        imported += 1
    return imported


def _import_maintenance_prices_catalog(db: Session, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    imported = 0
    for _, row in df.iterrows():
        if is_blank(row.get('Код')) or is_blank(row.get('Наименование оборудования')):
            continue
        code = int(row['Код'])
        name = str(row['Наименование оборудования']).strip()[:255]
        unit_price = pd.to_numeric(row.get('Цена за еденицу'), errors='coerce')
        unit_price = float(unit_price) if pd.notna(unit_price) else 0.0
        price = db.query(MaintenancePrice).filter(MaintenancePrice.access_code == code).first()
        fields = {
            'access_code': code,
            'equipment_name': name,
            'unit_price': unit_price,
        }
        if price is None:
            price = MaintenancePrice(**fields)
            db.add(price)
        else:
            for key, value in fields.items():
                setattr(price, key, value)
        db.flush()
        imported += 1
    return imported


def _to_datetime(value):
    if is_blank(value):
        return None
    parsed = pd.to_datetime(value, errors='coerce')
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not (isinstance(value, float) and pd.isna(value)):
        return int(value) != 0
    text = str(value).strip().lower()
    return text in {'1', 'true', 'yes', '-1'}


def _to_number(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors='coerce')
    if pd.isna(parsed):
        return default
    return float(parsed)


def _to_int(value) -> int | None:
    if is_blank(value):
        return None
    parsed = pd.to_numeric(value, errors='coerce')
    if pd.isna(parsed):
        return None
    return int(parsed)


def _objects_by_access_code(db: Session) -> dict[int, Object]:
    return {
        obj.access_code: obj
        for obj in db.query(Object).all()
        if obj.access_code is not None
    }


def _objects_by_inv_number(db: Session) -> dict[str, Object]:
    return {
        obj.inv_number.strip().lower(): obj
        for obj in db.query(Object).all()
    }


def _import_maintenance_records(
    db: Session,
    df: pd.DataFrame,
    objects_by_access_code: dict[int, Object],
) -> tuple[int, list[int]]:
    if df.empty:
        return 0, []
    imported = 0
    orphans: list[int] = []
    for _, row in df.iterrows():
        if is_blank(row.get('Код')):
            continue
        code = int(row['Код'])
        object_code = _to_int(row.get('Объект'))
        obj = objects_by_access_code.get(object_code) if object_code is not None else None
        if obj is None:
            if object_code is not None:
                orphans.append(object_code)
            continue
        record = db.query(MaintenanceRecord).filter(MaintenanceRecord.access_code == code).first()
        fields = {
            'access_code': code,
            'object_id': obj.id,
            'date': _to_datetime(row.get('Дата')),
            'act_to': _to_bool(row.get('Акт ТО')),
            'extra_works_flag': _to_bool(row.get('Допработы')),
        }
        if record is None:
            record = MaintenanceRecord(**fields)
            db.add(record)
        else:
            for key, value in fields.items():
                setattr(record, key, value)
        db.flush()
        imported += 1
    return imported, orphans


def _import_extra_works(
    db: Session,
    df: pd.DataFrame,
    objects_by_access_code: dict[int, Object],
    work_types_by_code: dict[int, int],
    materials_by_code: dict[int, int],
    units_by_code: dict[int, int],
) -> tuple[int, list[int]]:
    if df.empty:
        return 0, []
    imported = 0
    orphans: list[int] = []
    for _, row in df.iterrows():
        if is_blank(row.get('Код')):
            continue
        code = int(row['Код'])
        object_code = _to_int(row.get('Объект'))
        obj = objects_by_access_code.get(object_code) if object_code is not None else None
        if obj is None:
            if object_code is not None:
                orphans.append(object_code)
            continue
        work_type_id = None
        if not is_blank(row.get('Виды работ')):
            work_type_id = work_types_by_code.get(int(row['Виды работ']))
        material_id = None
        if not is_blank(row.get('Материалы')):
            material_id = materials_by_code.get(int(row['Материалы']))
        unit_id = None
        if not is_blank(row.get('ед изм')):
            unit_id = units_by_code.get(int(row['ед изм']))
        work = db.query(ExtraWork).filter(ExtraWork.access_code == code).first()
        fields = {
            'access_code': code,
            'object_id': obj.id,
            'date': _to_datetime(row.get('Дата')),
            'document_number': _to_int(row.get('Номер документа')),
            'work_type_id': work_type_id,
            'quantity': _to_int(row.get('Количество')),
            'unit_cost': _to_number(row.get('Стоимость ед')),
            'unit_vat': _to_number(row.get('в том числе НДС')),
            'price': _to_number(row.get('Цена')),
            'price_vat': _to_number(row.get('Цв том числе НДС')),
            'material_id': material_id,
            'unit_id': unit_id,
            'material_quantity': _to_int(row.get('МКоличество')),
            'material_unit_cost': _to_number(row.get('МСтоимость ед')),
            'material_unit_vat': _to_number(row.get('Мв том числе НДС')),
            'material_price': _to_number(row.get('МЦена')),
            'material_price_vat': _to_number(row.get('МЦв том числе НДС')),
            'material_system': _optional_str(row.get('МСистема'), 10),
        }
        if work is None:
            work = ExtraWork(**fields)
            db.add(work)
        else:
            for key, value in fields.items():
                setattr(work, key, value)
        db.flush()
        imported += 1
    return imported, orphans


def _import_documents(
    db: Session,
    df: pd.DataFrame,
    objects_by_inv: dict[str, Object],
) -> tuple[int, list[str]]:
    if df.empty or 'Инвентарный номер' not in df.columns:
        return 0, []
    imported = 0
    orphans: list[str] = []
    for _, row in df.iterrows():
        if is_blank(row.get('Инвентарный номер')):
            continue
        inv_number = str(row['Инвентарный номер']).strip()
        obj = objects_by_inv.get(inv_number.lower())
        if obj is None:
            orphans.append(inv_number)
            continue
        payload = {
            model_field: _optional_str(row.get(access_col), None)
            for access_col, model_field in DOCUMENT_ACCESS_TO_FIELD.items()
        }
        doc = db.query(ObjectDocuments).filter(ObjectDocuments.object_id == obj.id).first()
        if doc is None:
            doc = ObjectDocuments(object_id=obj.id, **payload)
            db.add(doc)
        else:
            for key, value in payload.items():
                setattr(doc, key, value)
        db.flush()
        imported += 1
    return imported, orphans


def import_from_access(db: Session, mdb_file_path: str, table_name: str) -> int:
    """Import a single Access table (typically Объекты)."""
    df = read_access_table(mdb_file_path, table_name)
    if df.empty:
        return 0

    count = 0
    for _, row in df.iterrows():
        data = _normalize_import_row(row.to_dict())
        data = _prepare_object_data(db, data)
        obj = _upsert_object(db, data)
        sync_flags_from_system_type(db, obj.id)
        count += 1
    db.commit()
    return count


def import_full_access(
    db: Session,
    mdb_file_path: str,
    *,
    on_progress: ImportProgressCallback | None = None,
) -> ImportReport:
    """Import references, objects, and operational data from a full Access database."""
    total_steps = 8
    conn = _connect_access(mdb_file_path)
    report = ImportReport()
    try:
        _notify_progress(on_progress, 'Подключение к Access…', 0, total_steps)

        valid_ownership = _load_ownership_values(conn)
        regions_df = _read_raw_table(conn, TABLE_REGIONS)
        responsibles_df = _read_raw_table(conn, TABLE_RESPONSIBLES)
        objects_df = _read_raw_table(conn, TABLE_OBJECTS)
        system_types_df = _read_raw_table(conn, TABLE_SYSTEM_TYPES)
        composition_df = _read_raw_table(conn, TABLE_COMPOSITION)
        units_df = _read_raw_table(conn, TABLE_UNITS)
        materials_df = _read_raw_table(conn, TABLE_MATERIALS)
        work_types_df = _read_raw_table(conn, TABLE_WORK_TYPES)
        maintenance_prices_df = _read_raw_table(conn, TABLE_MAINTENANCE_PRICES)
        maintenance_df = _read_raw_table(conn, TABLE_MAINTENANCE)
        extra_works_df = _read_raw_table(conn, TABLE_EXTRA_WORKS)
        documents_df = _read_raw_table(conn, TABLE_DOCUMENTS)

        _notify_progress(on_progress, 'Справочники: регионы и ответственные…', 1, total_steps)
        canonical_regions = _import_regions_catalog(db, regions_df)
        report.regions = len(canonical_regions)
        responsible_by_code = _import_responsibles_catalog(db, responsibles_df)
        report.responsibles = len(responsible_by_code)

        _notify_progress(on_progress, 'Справочники: единицы, материалы, работы…', 2, total_steps)
        units_by_code = _import_units_catalog(db, units_df)
        report.units = len(units_by_code)
        materials_by_code = _import_materials_catalog(db, materials_df, units_by_code)
        report.materials = len(materials_by_code)
        report.work_types = _import_work_types_catalog(db, work_types_df, materials_by_code)
        report.maintenance_prices = _import_maintenance_prices_catalog(db, maintenance_prices_df)

        _notify_progress(on_progress, 'Объекты…', 3, total_steps)
        report.objects = _import_objects(
            db,
            objects_df,
            responsible_by_code=responsible_by_code,
            canonical_regions=canonical_regions,
            valid_ownership=valid_ownership,
            unmatched_regions=report.unmatched_regions,
        )

        _notify_progress(on_progress, 'Типы систем…', 4, total_steps)
        report.system_flag_objects, report.orphan_system_type_inv_numbers = (
            _import_system_type_flags(db, system_types_df)
        )

        _notify_progress(on_progress, 'Состав оборудования…', 5, total_steps)
        report.compositions, report.orphan_composition_inv_numbers = (
            _import_compositions(db, composition_df)
        )
        report.missing_composition_inv_numbers = _missing_composition_inv_numbers(db, composition_df)

        objects_by_access_code = _objects_by_access_code(db)
        objects_by_inv = _objects_by_inv_number(db)

        _notify_progress(on_progress, 'Журнал ТО и допработы…', 6, total_steps)
        report.maintenance_records, report.orphan_maintenance_object_codes = (
            _import_maintenance_records(db, maintenance_df, objects_by_access_code)
        )
        report.extra_works, report.orphan_extra_work_object_codes = _import_extra_works(
            db,
            extra_works_df,
            objects_by_access_code,
            {wt.access_code: wt.id for wt in db.query(WorkType).all() if wt.access_code},
            {item.access_code: item.id for item in db.query(Material).all() if item.access_code},
            {unit.access_code: unit.id for unit in db.query(Unit).all() if unit.access_code},
        )

        _notify_progress(on_progress, 'Документы…', 7, total_steps)
        report.documents, report.orphan_document_inv_numbers = (
            _import_documents(db, documents_df, objects_by_inv)
        )

        db.commit()
        _notify_progress(on_progress, 'Готово', total_steps, total_steps)
    except Exception:
        db.rollback()
        raise
    finally:
        conn.close()
    return report

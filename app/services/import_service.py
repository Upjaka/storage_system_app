import pyodbc
import pandas as pd
from sqlalchemy.orm import Session
from models.object_model import Object
from services.reference_service import get_or_create_region, get_or_create_responsible

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
}

IMPORT_DEFAULTS = {
    'maintenance_mode': 'ежемесячное',
    'system_type': 'АПС',
}

OWNERSHIP_ALIASES = {
    'н\\д': 'н/д',
}

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
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not (isinstance(value, float) and pd.isna(value)):
        return lookup.get(int(value))
    text = str(value).strip()
    if not text or text.lower() == 'nan':
        return None
    try:
        as_float = float(text)
        if as_float == int(as_float):
            return lookup.get(int(as_float), text)
    except ValueError:
        pass
    return text


def _normalize_import_row(data: dict) -> dict:
    data = dict(data)
    if data.get('inv_number') is not None:
        data['inv_number'] = str(data['inv_number']).strip()
    if data.get('number_in_db') is not None:
        data['number_in_db'] = int(data['number_in_db'])
    ownership = data.get('ownership')
    if ownership in OWNERSHIP_ALIASES:
        data['ownership'] = OWNERSHIP_ALIASES[ownership]
    for field, default in IMPORT_DEFAULTS.items():
        if not data.get(field):
            data[field] = default
    return data


def _prepare_object_data(db: Session, data: dict) -> dict:
    region_name = data.pop('region', None)
    responsible_name = data.pop('responsible', None)
    data['region_id'] = get_or_create_region(db, region_name)
    data['responsible_id'] = get_or_create_responsible(db, responsible_name)
    return data


def read_access_table(mdb_file_path: str, table_name: str) -> pd.DataFrame:
    """Read an Access table with the same normalization applied during import."""
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        fr'DBQ={mdb_file_path};'
    )
    try:
        conn = pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        raise ConnectionError(f"Не удалось подключиться к Access: {e}")

    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
        responsible_lookup = _load_responsible_lookup(conn)
    except Exception as e:
        conn.close()
        raise ValueError(f"Ошибка чтения таблицы '{table_name}': {e}")
    conn.close()

    if df.empty:
        return df

    df.rename(columns={col: FIELD_MAPPING.get(col, col) for col in df.columns}, inplace=True)

    model_columns = {c.name for c in Object.__table__.columns}
    reference_columns = {'region', 'responsible'}
    df = df[[col for col in df.columns if col in model_columns or col in reference_columns]]

    if responsible_lookup and 'responsible' in df.columns:
        df['responsible'] = df['responsible'].apply(
            lambda value: _resolve_responsible_value(value, responsible_lookup)
        )

    df = df.where(pd.notnull(df), None)

    if 'cost' in df.columns:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)

    df.dropna(subset=['number_in_db', 'inv_number'], inplace=True)
    return df


def import_from_access(db: Session, mdb_file_path: str, table_name: str) -> int:
    """
    Импортирует данные из указанной таблицы Access в БД SQLite.
    Возвращает количество импортированных записей.
    """
    df = read_access_table(mdb_file_path, table_name)
    if df.empty:
        return 0

    count = 0
    for _, row in df.iterrows():
        data = _normalize_import_row(row.to_dict())
        data = _prepare_object_data(db, data)
        existing = db.query(Object).filter(
            (Object.number_in_db == data['number_in_db']) |
            (Object.inv_number == data['inv_number'])
        ).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            db.add(Object(**data))
        count += 1
    db.commit()
    return count

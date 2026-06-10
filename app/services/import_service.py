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


def _prepare_object_data(db: Session, data: dict) -> dict:
    region_name = data.pop('region', None)
    responsible_name = data.pop('responsible', None)
    data['region_id'] = get_or_create_region(db, region_name)
    data['responsible_id'] = get_or_create_responsible(db, responsible_name)
    return data


def import_from_access(db: Session, mdb_file_path: str, table_name: str) -> int:
    """
    Импортирует данные из указанной таблицы Access в БД SQLite.
    Возвращает количество импортированных записей.
    """
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
    except Exception as e:
        conn.close()
        raise ValueError(f"Ошибка чтения таблицы '{table_name}': {e}")
    conn.close()

    if df.empty:
        return 0

    df.rename(columns={col: FIELD_MAPPING.get(col, col) for col in df.columns}, inplace=True)

    model_columns = {c.name for c in Object.__table__.columns}
    reference_columns = {'region', 'responsible'}
    df = df[[col for col in df.columns if col in model_columns or col in reference_columns]]

    df = df.where(pd.notnull(df), None)

    if 'cost' in df.columns:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)

    df.dropna(subset=['number_in_db', 'inv_number'], inplace=True)

    count = 0
    for _, row in df.iterrows():
        data = _prepare_object_data(db, row.to_dict())
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

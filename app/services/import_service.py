import pyodbc
import pandas as pd
from sqlalchemy.orm import Session
from models.object_model import Object
from typing import Dict, Any

# Словарь соответствия полей Access -> поля модели
# Измените названия колонок в левой части под реальные имена в вашей таблице Access
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

def import_from_access(db: Session, mdb_file_path: str, table_name: str) -> int:
    """
    Импортирует данные из указанной таблицы Access в БД SQLite.
    Возвращает количество импортированных записей.
    """
    # Строка подключения к Access (для .accdb и .mdb)
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        fr'DBQ={mdb_file_path};'
    )
    try:
        conn = pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        raise ConnectionError(f"Не удалось подключиться к Access: {e}")

    # Читаем таблицу в DataFrame
    try:
        df = pd.read_sql(f'SELECT * FROM [{table_name}]', conn)
    except Exception as e:
        conn.close()
        raise ValueError(f"Ошибка чтения таблицы '{table_name}': {e}")
    conn.close()

    if df.empty:
        return 0

    # Переименовываем колонки согласно маппингу
    df.rename(columns={col: FIELD_MAPPING.get(col, col) for col in df.columns}, inplace=True)

    # Оставляем только те колонки, которые есть в модели Object
    model_columns = {c.name for c in Object.__table__.columns}
    df = df[[col for col in df.columns if col in model_columns]]

    # Предобработка: заменяем NaN на None
    df = df.where(pd.notnull(df), None)

    # Конвертируем типы: стоимость из строки в число при необходимости
    if 'cost' in df.columns:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)

    # Удаляем строки с пустыми обязательными полями (number_in_db и inv_number должны быть уникальны)
    df.dropna(subset=['number_in_db', 'inv_number'], inplace=True)

    count = 0
    for _, row in df.iterrows():
        data = row.to_dict()
        # Проверяем уникальность number_in_db и inv_number (merge с проверкой)
        existing = db.query(Object).filter(
            (Object.number_in_db == data['number_in_db']) |
            (Object.inv_number == data['inv_number'])
        ).first()
        if existing:
            # Обновляем существующий объект
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            existing = Object(**data)
            db.add(existing)
        count += 1
    db.commit()
    return count
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.object_model import Object
from typing import Optional, List, Dict, Any

def create_object(db: Session, data: Dict[str, Any]) -> Object:
    obj = Object(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_object(db: Session, obj_id: int, data: Dict[str, Any]) -> Object:
    obj = db.query(Object).filter(Object.id == obj_id).first()
    for key, value in data.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_object(db: Session, obj_id: int):
    obj = db.query(Object).filter(Object.id == obj_id).first()
    db.delete(obj)
    db.commit()

def get_object(db: Session, obj_id: int) -> Object:
    return db.query(Object).filter(Object.id == obj_id).first()

def get_objects_filtered(db: Session, filters: Dict[str, Any]) -> List[Object]:
    query = db.query(Object)
    # Динамическая фильтрация (равенство или частичное совпадение для строк)
    for field, value in filters.items():
        if value is None or value == '':
            continue
        column = getattr(Object, field, None)
        if column is None:
            continue
        if isinstance(column.type.python_type, str):
            query = query.filter(column.contains(value))
        else:
            query = query.filter(column == value)
    return query.all()
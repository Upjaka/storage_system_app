from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from models.object_model import Object
from services.reference_service import resolve_reference_ids
from typing import List, Dict, Any


def create_object(db: Session, data: Dict[str, Any]) -> Object:
    data = resolve_reference_ids(db, data)
    obj = Object(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_object(db: Session, obj_id: int, data: Dict[str, Any]) -> Object:
    data = resolve_reference_ids(db, data)
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


def get_next_number_in_db(db: Session) -> int:
    max_number = db.query(func.max(Object.number_in_db)).scalar()
    return (max_number or 0) + 1


def get_object(db: Session, obj_id: int) -> Object:
    return (
        db.query(Object)
        .options(joinedload(Object.region), joinedload(Object.responsible))
        .filter(Object.id == obj_id)
        .first()
    )


def get_objects_filtered(db: Session, filters: Dict[str, Any]) -> List[Object]:
    query = (
        db.query(Object)
        .options(joinedload(Object.region), joinedload(Object.responsible))
    )
    for field, value in filters.items():
        if value is None or value == '':
            continue
        if field == 'region_id':
            query = query.filter(Object.region_id == int(value))
            continue
        if field == 'responsible_id':
            query = query.filter(Object.responsible_id == int(value))
            continue
        column = getattr(Object, field, None)
        if column is None:
            continue
        if isinstance(column.type.python_type, str):
            query = query.filter(column.contains(value))
        else:
            query = query.filter(column == value)
    return query.all()

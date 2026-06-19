from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload
from models.object_model import SYSTEM_CODES, Object, ObjectSystemFlag, Region, Responsible
from services.reference_service import get_regions, get_responsibles, resolve_reference_ids
from services.system_flag_service import set_system_codes, sync_flags_from_system_type
from typing import List, Dict, Any


def _pop_system_codes(data: Dict[str, Any]) -> list[str] | None:
    if 'system_codes' not in data:
        return None
    codes = data.pop('system_codes')
    if codes is None:
        return None
    return list(codes)


def create_object(db: Session, data: Dict[str, Any]) -> Object:
    data = dict(data)
    system_codes = _pop_system_codes(data)
    data = resolve_reference_ids(db, data)
    obj = Object(**data)
    db.add(obj)
    db.flush()
    if system_codes is not None:
        set_system_codes(db, obj.id, system_codes)
    else:
        sync_flags_from_system_type(db, obj.id)
    db.commit()
    db.refresh(obj)
    return obj


def update_object(db: Session, obj_id: int, data: Dict[str, Any]) -> Object:
    data = dict(data)
    system_codes = _pop_system_codes(data)
    data = resolve_reference_ids(db, data)
    obj = db.query(Object).filter(Object.id == obj_id).first()
    for key, value in data.items():
        setattr(obj, key, value)
    if system_codes is not None:
        set_system_codes(db, obj_id, system_codes)
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


def _object_query(db: Session):
    return (
        db.query(Object)
        .options(
            joinedload(Object.region),
            joinedload(Object.responsible),
            joinedload(Object.system_flags),
            joinedload(Object.composition),
        )
    )


def get_object(db: Session, obj_id: int) -> Object:
    return _object_query(db).filter(Object.id == obj_id).first()


def get_objects_filtered(db: Session, filters: Dict[str, Any]) -> List[Object]:
    query = _object_query(db)
    needs_distinct = False

    for field, value in filters.items():
        if value is None or value == '':
            continue
        value_str = str(value).strip()
        if not value_str:
            continue

        if field in ('region', 'region_id'):
            if isinstance(value, int):
                query = query.filter(Object.region_id == value)
            else:
                query = query.join(Object.region).filter(Region.name.contains(value_str))
            continue
        if field in ('responsible', 'responsible_id'):
            if isinstance(value, int):
                query = query.filter(Object.responsible_id == value)
            else:
                query = query.join(Object.responsible).filter(Responsible.name.contains(value_str))
            continue
        if field == 'system_type':
            query = (
                query
                .outerjoin(Object.system_flags)
                .filter(or_(
                    cast(Object.system_type, String).contains(value_str),
                    ObjectSystemFlag.system_code.contains(value_str),
                ))
            )
            needs_distinct = True
            continue
        if field == 'number_in_db':
            query = query.filter(cast(Object.number_in_db, String).contains(value_str))
            continue

        column = getattr(Object, field, None)
        if column is None:
            continue
        if isinstance(column.type.python_type, str):
            query = query.filter(column.contains(value_str))
        else:
            query = query.filter(cast(column, String).contains(value_str))

    if needs_distinct:
        query = query.distinct()
    return query.all()


def get_object_filter_autocomplete(db: Session) -> dict[str, list[str]]:
    rows = db.query(
        Object.number_in_db,
        Object.inv_number,
        Object.address,
        Object.object_type,
    ).all()
    return {
        'number_in_db': sorted(
            {str(number) for number, _, _, _ in rows if number is not None},
            key=lambda value: int(value),
        ),
        'inv_number': sorted({inv for _, inv, _, _ in rows if inv}),
        'address': sorted({addr for _, _, addr, _ in rows if addr}),
        'object_type': sorted({obj_type for _, _, _, obj_type in rows if obj_type}),
        'system_type': list(SYSTEM_CODES),
        'region': [region.name for region in get_regions(db)],
        'responsible': [responsible.name for responsible in get_responsibles(db)],
    }

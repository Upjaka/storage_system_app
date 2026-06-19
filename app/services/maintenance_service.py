from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from models.object_model import Object
from models.operations_model import MaintenanceRecord


def get_maintenance_records(db: Session, *, object_id: int | None = None) -> list[MaintenanceRecord]:
    query = (
        db.query(MaintenanceRecord)
        .options(joinedload(MaintenanceRecord.object))
        .order_by(MaintenanceRecord.date.desc(), MaintenanceRecord.id.desc())
    )
    if object_id is not None:
        query = query.filter(MaintenanceRecord.object_id == object_id)
    return query.all()


def create_maintenance_record(
    db: Session,
    *,
    object_id: int,
    date: datetime | None,
    act_to: bool = False,
    extra_works_flag: bool = False,
) -> MaintenanceRecord:
    record = MaintenanceRecord(
        object_id=object_id,
        date=date,
        act_to=bool(act_to),
        extra_works_flag=bool(extra_works_flag),
    )
    db.add(record)
    db.flush()
    return record


def update_maintenance_record(db: Session, record_id: int, data: dict) -> MaintenanceRecord:
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if record is None:
        raise ValueError('Запись журнала ТО не найдена')
    for field in ('object_id', 'date', 'act_to', 'extra_works_flag'):
        if field in data:
            setattr(record, field, data[field])
    db.flush()
    return record


def delete_maintenance_record(db: Session, record_id: int) -> None:
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if record is None:
        raise ValueError('Запись журнала ТО не найдена')
    db.delete(record)
    db.flush()


def get_objects_for_select(db: Session) -> list[Object]:
    return db.query(Object).order_by(Object.number_in_db).all()

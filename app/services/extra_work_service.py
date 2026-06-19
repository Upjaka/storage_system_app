from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from models.operations_model import ExtraWork
from services import catalog_service as cat


def get_extra_works(db: Session, *, object_id: int | None = None) -> list[ExtraWork]:
    query = (
        db.query(ExtraWork)
        .options(
            joinedload(ExtraWork.object),
            joinedload(ExtraWork.work_type),
            joinedload(ExtraWork.material),
            joinedload(ExtraWork.unit),
        )
        .order_by(ExtraWork.date.desc(), ExtraWork.id.desc())
    )
    if object_id is not None:
        query = query.filter(ExtraWork.object_id == object_id)
    return query.all()


def create_extra_work(db: Session, data: dict) -> ExtraWork:
    work = ExtraWork(**_prepare_payload(data))
    db.add(work)
    db.flush()
    return work


def update_extra_work(db: Session, work_id: int, data: dict) -> ExtraWork:
    work = db.query(ExtraWork).filter(ExtraWork.id == work_id).first()
    if work is None:
        raise ValueError('Запись допработ не найдена')
    for key, value in _prepare_payload(data).items():
        setattr(work, key, value)
    db.flush()
    return work


def delete_extra_work(db: Session, work_id: int) -> None:
    work = db.query(ExtraWork).filter(ExtraWork.id == work_id).first()
    if work is None:
        raise ValueError('Запись допработ не найдена')
    db.delete(work)
    db.flush()


def _prepare_payload(data: dict) -> dict:
    payload = dict(data)
    for key in (
        'document_number', 'quantity', 'material_quantity',
        'work_type_id', 'material_id', 'unit_id', 'object_id',
    ):
        if key in payload and payload[key] in ('', None):
            payload[key] = None
        elif key in payload and payload[key] is not None:
            payload[key] = int(payload[key])
    for key in (
        'unit_cost', 'unit_vat', 'price', 'price_vat',
        'material_unit_cost', 'material_unit_vat', 'material_price', 'material_price_vat',
    ):
        if key in payload and payload[key] is not None:
            payload[key] = float(payload[key] or 0)
    if 'date' in payload and payload['date'] in ('', None):
        payload['date'] = None
    elif 'date' in payload and isinstance(payload['date'], str):
        payload['date'] = datetime.fromisoformat(payload['date'])
    if 'material_system' in payload and payload['material_system'] == '':
        payload['material_system'] = None
    return payload


def get_reference_options(db: Session) -> dict:
    return {
        'work_types': {None: '—', **{item.id: item.name for item in cat.get_work_types(db)}},
        'materials': {None: '—', **{item.id: item.name for item in cat.get_materials(db)}},
        'units': {None: '—', **{item.id: item.name for item in cat.get_units(db)}},
    }

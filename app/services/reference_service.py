from sqlalchemy.orm import Session
from models.object_model import Object, Region, Responsible


def _is_blank_name(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    name = str(value).strip()
    return not name or name.lower() == 'nan'


def _normalize_name(name: str | None) -> str:
    if _is_blank_name(name):
        raise ValueError('Наименование не может быть пустым')
    return str(name).strip()


def get_regions(db: Session) -> list[Region]:
    return db.query(Region).order_by(Region.name).all()


def get_responsibles(db: Session) -> list[Responsible]:
    return db.query(Responsible).order_by(Responsible.name).all()


def count_objects_for_region(db: Session, region_id: int) -> int:
    return db.query(Object).filter(Object.region_id == region_id).count()


def count_objects_for_responsible(db: Session, responsible_id: int) -> int:
    return db.query(Object).filter(Object.responsible_id == responsible_id).count()


def create_region(db: Session, name: str) -> Region:
    region = Region(name=_normalize_name(name))
    db.add(region)
    db.flush()
    return region


def create_responsible(db: Session, name: str) -> Responsible:
    responsible = Responsible(name=_normalize_name(name))
    db.add(responsible)
    db.flush()
    return responsible


def update_region(db: Session, region_id: int, name: str) -> Region:
    region = db.query(Region).filter(Region.id == region_id).first()
    if region is None:
        raise ValueError('Регион не найден')
    region.name = _normalize_name(name)
    db.flush()
    return region


def update_responsible(db: Session, responsible_id: int, name: str) -> Responsible:
    responsible = db.query(Responsible).filter(Responsible.id == responsible_id).first()
    if responsible is None:
        raise ValueError('Ответственный не найден')
    responsible.name = _normalize_name(name)
    db.flush()
    return responsible


def delete_region(db: Session, region_id: int) -> None:
    region = db.query(Region).filter(Region.id == region_id).first()
    if region is None:
        raise ValueError('Регион не найден')
    if count_objects_for_region(db, region_id) > 0:
        raise ValueError('Нельзя удалить регион: к нему привязаны объекты')
    db.delete(region)
    db.flush()


def delete_responsible(db: Session, responsible_id: int) -> None:
    responsible = db.query(Responsible).filter(Responsible.id == responsible_id).first()
    if responsible is None:
        raise ValueError('Ответственный не найден')
    if count_objects_for_responsible(db, responsible_id) > 0:
        raise ValueError('Нельзя удалить ответственного: к нему привязаны объекты')
    db.delete(responsible)
    db.flush()


def get_or_create_region(db: Session, name: str | None) -> int | None:
    if _is_blank_name(name):
        return None
    name = str(name).strip()
    region = db.query(Region).filter(Region.name == name).first()
    if region is None:
        region = Region(name=name)
        db.add(region)
        db.flush()
    return region.id


def get_or_create_responsible(db: Session, name: str | None) -> int | None:
    if _is_blank_name(name):
        return None
    name = str(name).strip()
    responsible = db.query(Responsible).filter(Responsible.name == name).first()
    if responsible is None:
        responsible = Responsible(name=name)
        db.add(responsible)
        db.flush()
    return responsible.id


def _resolve_fk_value(db: Session, value, get_or_create) -> int | None:
    if value is None or value == '':
        return None
    if isinstance(value, int):
        return value
    return get_or_create(db, value)


def resolve_reference_ids(db: Session, data: dict) -> dict:
    """Map legacy text fields or empty FK values before persisting an object."""
    data = dict(data)
    if 'region' in data:
        data['region_id'] = get_or_create_region(db, data.pop('region'))
    if 'responsible' in data:
        data['responsible_id'] = get_or_create_responsible(db, data.pop('responsible'))
    data['region_id'] = _resolve_fk_value(db, data.get('region_id'), get_or_create_region)
    data['responsible_id'] = _resolve_fk_value(db, data.get('responsible_id'), get_or_create_responsible)
    return data

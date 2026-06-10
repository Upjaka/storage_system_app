from sqlalchemy.orm import Session
from models.object_model import Region, Responsible


def get_regions(db: Session) -> list[Region]:
    return db.query(Region).order_by(Region.name).all()


def get_responsibles(db: Session) -> list[Responsible]:
    return db.query(Responsible).order_by(Responsible.name).all()


def get_or_create_region(db: Session, name: str | None) -> int | None:
    if name is None:
        return None
    name = str(name).strip()
    if not name:
        return None
    region = db.query(Region).filter(Region.name == name).first()
    if region is None:
        region = Region(name=name)
        db.add(region)
        db.flush()
    return region.id


def get_or_create_responsible(db: Session, name: str | None) -> int | None:
    if name is None:
        return None
    name = str(name).strip()
    if not name:
        return None
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

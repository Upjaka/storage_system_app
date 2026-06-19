from sqlalchemy.orm import Session

from models.object_model import SYSTEM_CODES, Object, ObjectSystemFlag


def primary_system_code(codes: list[str]) -> str:
    for code in SYSTEM_CODES:
        if code in codes:
            return code
    return 'АПС'


def _normalize_codes(codes: list[str]) -> list[str]:
    if not codes:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code not in SYSTEM_CODES:
            raise ValueError(f'Недопустимый тип системы: {code}')
        if code not in seen:
            seen.add(code)
            normalized.append(code)
    return sorted(normalized, key=SYSTEM_CODES.index)


def get_system_codes(db: Session, object_id: int) -> list[str]:
    flags = (
        db.query(ObjectSystemFlag)
        .filter(ObjectSystemFlag.object_id == object_id)
        .all()
    )
    return sorted((flag.system_code for flag in flags), key=SYSTEM_CODES.index)


def set_system_codes(db: Session, object_id: int, codes: list[str]) -> None:
    normalized = _normalize_codes(codes)
    if not normalized:
        normalized = ['АПС']

    obj = db.query(Object).filter(Object.id == object_id).first()
    if obj is None:
        raise ValueError('Объект не найден')

    db.query(ObjectSystemFlag).filter(ObjectSystemFlag.object_id == object_id).delete()
    for code in normalized:
        db.add(ObjectSystemFlag(object_id=object_id, system_code=code))
    obj.system_type = primary_system_code(normalized)
    db.flush()


def sync_flags_from_system_type(db: Session, object_id: int) -> None:
    obj = db.query(Object).filter(Object.id == object_id).first()
    if obj is None:
        return
    existing = (
        db.query(ObjectSystemFlag)
        .filter(ObjectSystemFlag.object_id == object_id)
        .count()
    )
    if existing > 0:
        return
    if obj.system_type:
        db.add(ObjectSystemFlag(object_id=object_id, system_code=obj.system_type))
        db.flush()

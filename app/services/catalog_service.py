from sqlalchemy.orm import Session

from models.catalog_model import MaintenancePrice, Material, Unit, WorkType


def _normalize_name(value: str, *, field_label: str = 'Наименование') -> str:
    name = str(value or '').strip()
    if not name or name.lower() == 'nan':
        raise ValueError(f'{field_label} не может быть пустым')
    return name


def get_units(db: Session) -> list[Unit]:
    return db.query(Unit).order_by(Unit.name).all()


def get_materials(db: Session) -> list[Material]:
    return db.query(Material).order_by(Material.name).all()


def get_work_types(db: Session) -> list[WorkType]:
    return db.query(WorkType).order_by(WorkType.name).all()


def get_maintenance_prices(db: Session) -> list[MaintenancePrice]:
    return db.query(MaintenancePrice).order_by(MaintenancePrice.equipment_name).all()


def count_materials_for_unit(db: Session, unit_id: int) -> int:
    return db.query(Material).filter(Material.unit_id == unit_id).count()


def count_work_types_for_material(db: Session, material_id: int) -> int:
    return db.query(WorkType).filter(WorkType.material_id == material_id).count()


def create_unit(db: Session, name: str) -> Unit:
    unit = Unit(name=_normalize_name(name, field_label='Единица измерения')[:20])
    db.add(unit)
    db.flush()
    return unit


def update_unit(db: Session, unit_id: int, name: str) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        raise ValueError('Единица измерения не найдена')
    unit.name = _normalize_name(name, field_label='Единица измерения')[:20]
    db.flush()
    return unit


def delete_unit(db: Session, unit_id: int) -> None:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        raise ValueError('Единица измерения не найдена')
    if count_materials_for_unit(db, unit_id) > 0:
        raise ValueError('Нельзя удалить единицу: к ней привязаны материалы')
    db.delete(unit)
    db.flush()


def create_material(
    db: Session,
    *,
    name: str,
    unit_id: int | None = None,
    cost: float = 0.0,
    defect: str | None = None,
    link: str | None = None,
) -> Material:
    material = Material(
        name=_normalize_name(name, field_label='Материал')[:255],
        unit_id=unit_id,
        cost=float(cost or 0),
        defect=(str(defect).strip()[:255] if defect else None),
        link=(str(link).strip() if link else None),
    )
    db.add(material)
    db.flush()
    return material


def update_material(db: Session, material_id: int, data: dict) -> Material:
    material = db.query(Material).filter(Material.id == material_id).first()
    if material is None:
        raise ValueError('Материал не найден')
    if 'name' in data:
        material.name = _normalize_name(data['name'], field_label='Материал')[:255]
    if 'unit_id' in data:
        material.unit_id = data['unit_id'] or None
    if 'cost' in data:
        material.cost = float(data['cost'] or 0)
    if 'defect' in data:
        defect = data['defect']
        material.defect = str(defect).strip()[:255] if defect else None
    if 'link' in data:
        link = data['link']
        material.link = str(link).strip() if link else None
    db.flush()
    return material


def delete_material(db: Session, material_id: int) -> None:
    material = db.query(Material).filter(Material.id == material_id).first()
    if material is None:
        raise ValueError('Материал не найден')
    if count_work_types_for_material(db, material_id) > 0:
        raise ValueError('Нельзя удалить материал: к нему привязаны виды работ')
    db.delete(material)
    db.flush()


def create_work_type(
    db: Session,
    *,
    name: str,
    cost: float = 0.0,
    section: str | None = None,
    output_text: str | None = None,
    material_id: int | None = None,
) -> WorkType:
    work_type = WorkType(
        name=_normalize_name(name, field_label='Вид работ')[:255],
        cost=float(cost or 0),
        section=(str(section).strip()[:50] if section else None),
        output_text=(str(output_text).strip()[:255] if output_text else None),
        material_id=material_id,
    )
    db.add(work_type)
    db.flush()
    return work_type


def update_work_type(db: Session, work_type_id: int, data: dict) -> WorkType:
    work_type = db.query(WorkType).filter(WorkType.id == work_type_id).first()
    if work_type is None:
        raise ValueError('Вид работ не найден')
    if 'name' in data:
        work_type.name = _normalize_name(data['name'], field_label='Вид работ')[:255]
    if 'cost' in data:
        work_type.cost = float(data['cost'] or 0)
    if 'section' in data:
        section = data['section']
        work_type.section = str(section).strip()[:50] if section else None
    if 'output_text' in data:
        output = data['output_text']
        work_type.output_text = str(output).strip()[:255] if output else None
    if 'material_id' in data:
        work_type.material_id = data['material_id'] or None
    db.flush()
    return work_type


def delete_work_type(db: Session, work_type_id: int) -> None:
    work_type = db.query(WorkType).filter(WorkType.id == work_type_id).first()
    if work_type is None:
        raise ValueError('Вид работ не найден')
    db.delete(work_type)
    db.flush()


def create_maintenance_price(
    db: Session,
    *,
    equipment_name: str,
    unit_price: float = 0.0,
) -> MaintenancePrice:
    price = MaintenancePrice(
        equipment_name=_normalize_name(equipment_name, field_label='Наименование')[:255],
        unit_price=float(unit_price or 0),
    )
    db.add(price)
    db.flush()
    return price


def update_maintenance_price(db: Session, price_id: int, data: dict) -> MaintenancePrice:
    price = db.query(MaintenancePrice).filter(MaintenancePrice.id == price_id).first()
    if price is None:
        raise ValueError('Стоимость ТО не найдена')
    if 'equipment_name' in data:
        price.equipment_name = _normalize_name(
            data['equipment_name'],
            field_label='Наименование',
        )[:255]
    if 'unit_price' in data:
        price.unit_price = float(data['unit_price'] or 0)
    db.flush()
    return price


def delete_maintenance_price(db: Session, price_id: int) -> None:
    price = db.query(MaintenancePrice).filter(MaintenancePrice.id == price_id).first()
    if price is None:
        raise ValueError('Стоимость ТО не найдена')
    db.delete(price)
    db.flush()

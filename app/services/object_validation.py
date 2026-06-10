FIELD_LABELS = {
    'number_in_db': 'Номер в БД',
    'inv_number': 'Инвентарный номер',
    'address': 'Адрес',
    'region_id': 'Регион',
    'object_type': 'Тип объекта',
    'ownership': 'Собственность',
    'cost': 'Стоимость',
    'responsible_id': 'Ответственный',
    'maintenance_mode': 'Режим ТО',
    'system_type': 'Тип системы',
}

REQUIRED_CREATE_FIELDS = ('number_in_db', 'inv_number', 'address')


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def validate_create_data(data: dict, *, error_mode: str = 'simple') -> str | None:
    missing = [field for field in REQUIRED_CREATE_FIELDS if _is_blank(data.get(field))]
    if not missing:
        return None
    labels = [FIELD_LABELS[field] for field in missing]
    if error_mode == 'verbose':
        details = ', '.join(f'{field} ({FIELD_LABELS[field]})' for field in missing)
        return f'Не заполнены обязательные поля: {details}'
    return f'Заполните обязательные поля: {", ".join(labels)}'

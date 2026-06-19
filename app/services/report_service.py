from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.composition_fields import COMPOSITION_FIELD_GROUPS, COMPOSITION_FIELD_LABELS
from models.object_model import SYSTEM_CODES
from services.composition_service import get_composition_counts
from services.extra_work_service import get_extra_works
from services.maintenance_service import get_maintenance_records
from services.object_service import get_object
from services.system_flag_service import get_system_codes


@dataclass(frozen=True)
class PrintPage:
    title: str
    subtitle: str
    sections: list[dict[str, Any]]


def _format_date(value) -> str:
    if value is None:
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%d.%m.%Y')
    return str(value)


def _format_money(value) -> str:
    if value is None:
        return '—'
    return f'{float(value):,.2f}'.replace(',', ' ')


def _yes_no(flag: bool) -> str:
    return 'Да' if flag else 'Нет'


def _system_codes_label(db: Session, object_id: int, obj) -> str:
    codes = get_system_codes(db, object_id)
    if codes:
        return ', '.join(sorted(codes, key=SYSTEM_CODES.index))
    return obj.system_type or '—'


def _object_header_rows(db: Session, obj) -> list[list[str]]:
    return [
        ['Номер в БД', str(obj.number_in_db)],
        ['Инвентарный номер', obj.inv_number or '—'],
        ['Адрес', obj.address or '—'],
        ['Регион', obj.region.name if obj.region else '—'],
        ['Тип объекта', obj.object_type or '—'],
        ['Собственность', obj.ownership or '—'],
        ['Стоимость', _format_money(obj.cost)],
        ['Ответственный', obj.responsible.name if obj.responsible else '—'],
        ['Режим ТО', obj.maintenance_mode or '—'],
        ['Типы систем', _system_codes_label(db, obj.id, obj)],
    ]


def _composition_table_rows(counts: dict[str, float | int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for group_name, fields in COMPOSITION_FIELD_GROUPS:
        group_rows: list[list[str]] = []
        for field in fields:
            value = counts.get(field, 0) or 0
            if value:
                group_rows.append([COMPOSITION_FIELD_LABELS[field], str(value)])
        if group_rows:
            rows.append([group_name, ''])
            rows.extend(group_rows)
    if not rows:
        rows.append(['—', '0'])
    return rows


def object_passport_page(db: Session, object_id: int) -> PrintPage:
    obj = get_object(db, object_id)
    if obj is None:
        raise ValueError('Объект не найден')

    counts = get_composition_counts(db, object_id)
    maintenance = get_maintenance_records(db, object_id=object_id)
    extra_works = get_extra_works(db, object_id=object_id)

    sections: list[dict[str, Any]] = [
        {
            'title': 'Основные сведения',
            'kind': 'kv',
            'rows': _object_header_rows(db, obj),
        },
        {
            'title': 'Состав оборудования',
            'kind': 'table',
            'headers': ['Позиция', 'Количество'],
            'rows': _composition_table_rows(counts),
        },
        {
            'title': 'Журнал ТО',
            'kind': 'table',
            'headers': ['Дата', 'Акт ТО', 'Допработы'],
            'rows': [
                [_format_date(record.date), _yes_no(record.act_to), _yes_no(record.extra_works_flag)]
                for record in maintenance
            ] or [['—', '—', '—']],
        },
        {
            'title': 'Допработы',
            'kind': 'table',
            'headers': ['Дата', 'Вид работ', 'Кол-во', 'Цена'],
            'rows': [
                [
                    _format_date(work.date),
                    work.work_type.name if work.work_type else '—',
                    str(work.quantity or 0),
                    _format_money(work.price),
                ]
                for work in extra_works
            ] or [['—', '—', '0', '—']],
        },
    ]

    return PrintPage(
        title='Паспорт объекта',
        subtitle=f'№ {obj.number_in_db} — {obj.inv_number}',
        sections=sections,
    )


def maintenance_act_page(db: Session, record_id: int) -> PrintPage:
    records = get_maintenance_records(db)
    record = next((item for item in records if item.id == record_id), None)
    if record is None:
        raise ValueError('Запись ТО не найдена')

    obj = record.object
    sections = [
        {
            'title': 'Объект',
            'kind': 'kv',
            'rows': _object_header_rows(db, obj),
        },
        {
            'title': 'Сведения о техническом обслуживании',
            'kind': 'kv',
            'rows': [
                ['Дата ТО', _format_date(record.date)],
                ['Акт ТО', _yes_no(record.act_to)],
                ['Допработы', _yes_no(record.extra_works_flag)],
            ],
        },
    ]

    return PrintPage(
        title='Акт технического обслуживания',
        subtitle=f'Объект № {obj.number_in_db} — {obj.inv_number}',
        sections=sections,
    )


def extra_work_page(db: Session, work_id: int) -> PrintPage:
    works = get_extra_works(db)
    work = next((item for item in works if item.id == work_id), None)
    if work is None:
        raise ValueError('Запись допработ не найдена')

    obj = work.object
    sections = [
        {
            'title': 'Объект',
            'kind': 'kv',
            'rows': _object_header_rows(db, obj),
        },
        {
            'title': 'Дополнительные работы',
            'kind': 'kv',
            'rows': [
                ['Дата', _format_date(work.date)],
                ['Номер документа', str(work.document_number) if work.document_number else '—'],
                ['Вид работ', work.work_type.name if work.work_type else '—'],
                ['Количество', str(work.quantity or 0)],
                ['Стоимость ед.', _format_money(work.unit_cost)],
                ['Цена', _format_money(work.price)],
                ['Материал', work.material.name if work.material else '—'],
                ['Ед. изм.', work.unit.name if work.unit else '—'],
                ['Кол-во материала', str(work.material_quantity or 0)],
                ['Система', work.material_system or '—'],
            ],
        },
    ]

    return PrintPage(
        title='Дополнительные работы',
        subtitle=f'Объект № {obj.number_in_db} — {obj.inv_number}',
        sections=sections,
    )

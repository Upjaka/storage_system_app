from datetime import datetime

from components.print_component import _decode_token, encode_page
from services.composition_service import upsert_composition
from services.extra_work_service import create_extra_work
from services.maintenance_service import create_maintenance_record
from services.object_service import create_object
from services.report_service import (
    extra_work_page,
    maintenance_act_page,
    object_passport_page,
)
from services import catalog_service as cat
from conftest import object_payload


def _section_titles(page) -> list[str]:
    return [section['title'] for section in page.sections]


def test_object_passport_page_includes_core_sections(db):
    obj = create_object(db, object_payload(inv_number='INV-RPT', address='ул. Печатная, 1'))
    upsert_composition(db, obj.id, {'АПС_Прибор управления': 2})
    create_maintenance_record(
        db,
        object_id=obj.id,
        date=datetime(2026, 1, 15),
        act_to=True,
    )
    db.commit()

    page = object_passport_page(db, obj.id)

    assert page.title == 'Паспорт объекта'
    assert 'INV-RPT' in page.subtitle
    assert _section_titles(page) == [
        'Основные сведения',
        'Состав оборудования',
        'Журнал ТО',
        'Допработы',
    ]

    main_rows = dict(page.sections[0]['rows'])
    assert main_rows['Адрес'] == 'ул. Печатная, 1'
    assert main_rows['Инвентарный номер'] == 'INV-RPT'

    composition_rows = page.sections[1]['rows']
    assert any('Прибор управления' in row[0] for row in composition_rows)

    maintenance_rows = page.sections[2]['rows']
    assert maintenance_rows[0][0] == '15.01.2026'
    assert maintenance_rows[0][1] == 'Да'


def test_maintenance_act_page_contains_record_fields(db):
    obj = create_object(db, object_payload(inv_number='INV-ACT'))
    record = create_maintenance_record(
        db,
        object_id=obj.id,
        date=datetime(2026, 2, 1),
        act_to=True,
        extra_works_flag=True,
    )
    db.commit()

    page = maintenance_act_page(db, record.id)
    to_rows = dict(page.sections[1]['rows'])

    assert page.title == 'Акт технического обслуживания'
    assert to_rows['Дата ТО'] == '01.02.2026'
    assert to_rows['Акт ТО'] == 'Да'
    assert to_rows['Допработы'] == 'Да'


def test_extra_work_page_resolves_catalog_names(db):
    unit = cat.create_unit(db, 'шт')
    material = cat.create_material(db, name='Кабель', unit_id=unit.id, cost=50.0)
    work_type = cat.create_work_type(
        db,
        name='Монтаж',
        cost=100.0,
        section='Раздел',
    )
    obj = create_object(db, object_payload(inv_number='INV-EW'))
    work = create_extra_work(db, {
        'object_id': obj.id,
        'date': datetime(2026, 3, 10),
        'document_number': 42,
        'work_type_id': work_type.id,
        'quantity': 3,
        'unit_cost': 150.0,
        'price': 450.0,
        'material_id': material.id,
        'unit_id': unit.id,
        'material_quantity': 10,
        'material_system': 'АПС',
    })
    db.commit()

    page = extra_work_page(db, work.id)
    work_rows = dict(page.sections[1]['rows'])

    assert page.title == 'Дополнительные работы'
    assert work_rows['Вид работ'] == 'Монтаж'
    assert work_rows['Материал'] == 'Кабель'
    assert work_rows['Ед. изм.'] == 'шт'
    assert work_rows['Номер документа'] == '42'


def test_encode_page_roundtrip_preserves_payload():
    token = encode_page(
        'Заголовок',
        'Подзаголовок',
        [{'title': 'Раздел', 'kind': 'kv', 'rows': [['Поле', 'Значение']]}],
    )
    payload = _decode_token(token)

    assert payload['title'] == 'Заголовок'
    assert payload['subtitle'] == 'Подзаголовок'
    assert payload['sections'][0]['rows'][0] == ['Поле', 'Значение']

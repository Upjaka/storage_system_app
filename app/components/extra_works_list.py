from __future__ import annotations

from datetime import datetime

from nicegui import ui

from layout import DIALOG, FIELD, FORM, GRID_2, INPUT
from messages import guard_action, run_db_action, show_error, show_error_from_exception, show_warning
from components.print_component import launch_print_page
from services.database import get_db
from services.report_service import extra_work_page
from services.extra_work_service import (
    create_extra_work,
    delete_extra_work,
    get_extra_works,
    get_reference_options,
    update_extra_work,
)
from services.maintenance_service import get_objects_for_select


def _format_date(value) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    return str(value)


def _parse_date(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    return datetime.fromisoformat(str(value).strip())


def _show_work_dialog(*, work_id: int | None, object_id: int | None, defaults: dict | None, on_saved) -> None:
    try:
        with get_db() as db:
            object_options = {
                obj.id: f'{obj.number_in_db} — {obj.inv_number}'
                for obj in get_objects_for_select(db)
            }
            refs = get_reference_options(db)
    except Exception as exc:
        show_error_from_exception(exc)
        return

    defaults = defaults or {}
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label('Допработа' if work_id else 'Новая допработа').classes('text-h5')
        with ui.element('div').classes(GRID_2):
            object_select = ui.select(
                label='Объект',
                options=object_options,
                value=defaults.get('object_id', object_id),
            ).classes(INPUT)
            date_input = ui.input(
                label='Дата',
                value=_format_date(defaults.get('date')),
                placeholder='YYYY-MM-DD',
            ).classes(INPUT)
            document_input = ui.number(
                label='Номер документа',
                value=defaults.get('document_number'),
                step=1,
            ).classes(INPUT)
            work_type_select = ui.select(
                label='Вид работ',
                options=refs['work_types'],
                value=defaults.get('work_type_id'),
            ).classes(INPUT)
            quantity_input = ui.number(
                label='Количество',
                value=defaults.get('quantity', 0),
                step=1,
                min=0,
            ).classes(INPUT)
            unit_cost_input = ui.number(
                label='Стоимость ед.',
                value=defaults.get('unit_cost', 0),
                step=0.01,
                format='%.2f',
            ).classes(INPUT)
            price_input = ui.number(
                label='Цена',
                value=defaults.get('price', 0),
                step=0.01,
                format='%.2f',
            ).classes(INPUT)
            material_select = ui.select(
                label='Материал',
                options=refs['materials'],
                value=defaults.get('material_id'),
            ).classes(INPUT)
            unit_select = ui.select(
                label='Ед. изм.',
                options=refs['units'],
                value=defaults.get('unit_id'),
            ).classes(INPUT)
            material_qty_input = ui.number(
                label='Кол-во материала',
                value=defaults.get('material_quantity', 0),
                step=1,
                min=0,
            ).classes(INPUT)
            system_input = ui.input(
                label='Система',
                value=defaults.get('material_system') or '',
            ).classes(INPUT)

        def save() -> None:
            if not object_select.value:
                show_warning('Выберите объект')
                return
            payload = {
                'object_id': int(object_select.value),
                'date': _parse_date(date_input.value),
                'document_number': document_input.value,
                'work_type_id': work_type_select.value,
                'quantity': quantity_input.value,
                'unit_cost': unit_cost_input.value,
                'price': price_input.value,
                'material_id': material_select.value,
                'unit_id': unit_select.value,
                'material_quantity': material_qty_input.value,
                'material_system': system_input.value,
            }

            def action() -> None:
                with get_db() as db:
                    if work_id is None:
                        create_extra_work(db, payload)
                    else:
                        update_extra_work(db, work_id, payload)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    delete_extra_work(db, work_id)
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if work_id:
                def print_work() -> None:
                    try:
                        with get_db() as db:
                            page = extra_work_page(db, work_id)
                        launch_print_page(page)
                    except ValueError as exc:
                        show_error(str(exc))

                ui.button('Печать', on_click=print_work, icon='print').props('outline')
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def content(*, object_id: int | None = None, on_changed=None):
    filter_object_id = {'value': object_id}
    row_cache: list[dict] = []

    def refresh_table() -> None:
        def load() -> None:
            with get_db() as db:
                works = get_extra_works(db, object_id=filter_object_id['value'])
                rows = [{
                    'id': work.id,
                    'Дата': _format_date(work.date),
                    'Объект': f'{work.object.number_in_db} — {work.object.inv_number}',
                    'Вид работ': work.work_type.name if work.work_type else '',
                    'Количество': work.quantity or 0,
                    'Цена': work.price,
                    '_work': work,
                } for work in works]
            row_cache.clear()
            row_cache.extend(rows)
            table.rows = [{k: v for k, v in row.items() if not k.startswith('_')} for row in rows]
            count_label.set_text(f'Записей: {len(rows)}')

        guard_action(load)

    with ui.column().classes('w-full gap-4'):
        title = 'Допработы' if object_id is None else 'Допработы объекта'
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label(title).classes('text-h4')
            ui.button(
                'Добавить',
                on_click=lambda: _show_work_dialog(
                    work_id=None,
                    object_id=filter_object_id['value'],
                    defaults=None,
                    on_saved=refresh_table,
                ),
                icon='add',
            ).props('outline no-caps')

        if object_id is None:
            with get_db() as db:
                object_options = {None: 'Все объекты', **{
                    obj.id: f'{obj.number_in_db} — {obj.inv_number}'
                    for obj in get_objects_for_select(db)
                }}
            with ui.element('div').classes(FIELD):
                ui.select(
                    options=object_options,
                    value=None,
                    on_change=lambda e: filter_object_id.update({'value': e.value}) or refresh_table(),
                ).classes(INPUT)

        count_label = ui.label('').classes('text-caption')
        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'Дата', 'label': 'Дата', 'field': 'Дата'},
                    {'name': 'Объект', 'label': 'Объект', 'field': 'Объект'},
                    {'name': 'Вид работ', 'label': 'Вид работ', 'field': 'Вид работ'},
                    {'name': 'Количество', 'label': 'Кол-во', 'field': 'Количество'},
                    {'name': 'Цена', 'label': 'Цена', 'field': 'Цена', 'align': 'right'},
                ],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')

        def on_row_click(e) -> None:
            row = e.args[1]
            full_row = next((item for item in row_cache if item['id'] == row['id']), row)
            work = full_row['_work']
            _show_work_dialog(
                work_id=work.id,
                object_id=work.object_id,
                defaults={
                    'object_id': work.object_id,
                    'date': work.date,
                    'document_number': work.document_number,
                    'work_type_id': work.work_type_id,
                    'quantity': work.quantity,
                    'unit_cost': work.unit_cost,
                    'price': work.price,
                    'material_id': work.material_id,
                    'unit_id': work.unit_id,
                    'material_quantity': work.material_quantity,
                    'material_system': work.material_system,
                },
                on_saved=refresh_table,
            )

        table.on('rowClick', on_row_click)
        refresh_table()
        if on_changed:
            on_changed(refresh_table)

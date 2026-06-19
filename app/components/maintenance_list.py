from __future__ import annotations

from datetime import datetime

from nicegui import ui

from layout import DIALOG, FIELD, FORM, GRID_2, INPUT
from messages import guard_action, run_db_action, show_error, show_error_from_exception, show_warning
from components.print_component import launch_print_page
from services.database import get_db
from services.report_service import maintenance_act_page
from services.maintenance_service import (
    create_maintenance_record,
    delete_maintenance_record,
    get_maintenance_records,
    get_objects_for_select,
    update_maintenance_record,
)


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


def _show_record_dialog(
    *,
    record_id: int | None,
    object_id: int | None,
    defaults: dict | None,
    on_saved,
) -> None:
    try:
        with get_db() as db:
            object_options = {
                obj.id: f'{obj.number_in_db} — {obj.inv_number}'
                for obj in get_objects_for_select(db)
            }
    except Exception as exc:
        show_error_from_exception(exc)
        return

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        title = 'Добавить запись ТО' if record_id is None else 'Редактирование записи ТО'
        ui.label(title).classes('text-h5')
        object_select = ui.select(
            label='Объект',
            options=object_options,
            value=(defaults or {}).get('object_id', object_id),
        ).classes(INPUT)
        date_input = ui.input(
            label='Дата',
            value=_format_date((defaults or {}).get('date')),
            placeholder='YYYY-MM-DD',
        ).classes(INPUT)
        act_to = ui.checkbox('Акт ТО', value=bool((defaults or {}).get('act_to')))
        extra_works = ui.checkbox(
            'Допработы',
            value=bool((defaults or {}).get('extra_works_flag')),
        )

        def save() -> None:
            if not object_select.value:
                show_warning('Выберите объект')
                return
            payload = {
                'object_id': int(object_select.value),
                'date': _parse_date(date_input.value),
                'act_to': act_to.value,
                'extra_works_flag': extra_works.value,
            }

            def action() -> None:
                with get_db() as db:
                    if record_id is None:
                        create_maintenance_record(db, **payload)
                    else:
                        update_maintenance_record(db, record_id, payload)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    delete_maintenance_record(db, record_id)
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if record_id:
                def print_act() -> None:
                    try:
                        with get_db() as db:
                            page = maintenance_act_page(db, record_id)
                        launch_print_page(page)
                    except ValueError as exc:
                        show_error(str(exc))

                ui.button('Печать акта', on_click=print_act, icon='print').props('outline')
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def content(*, object_id: int | None = None, on_changed=None):
    filter_object_id = {'value': object_id}

    def refresh_table() -> None:
        def load() -> None:
            with get_db() as db:
                records = get_maintenance_records(db, object_id=filter_object_id['value'])
                rows = [{
                    'id': record.id,
                    'Дата': _format_date(record.date),
                    'Объект': f'{record.object.number_in_db} — {record.object.inv_number}',
                    'Акт ТО': 'Да' if record.act_to else '',
                    'Допработы': 'Да' if record.extra_works_flag else '',
                    '_record': record,
                } for record in records]
            row_cache.clear()
            row_cache.extend(rows)
            table.rows = [{k: v for k, v in row.items() if not k.startswith('_')} for row in rows]
            count_label.set_text(f'Записей: {len(rows)}')

        guard_action(load)

    row_cache: list[dict] = []

    with ui.column().classes('w-full gap-4'):
        title = 'Журнал ТО' if object_id is None else 'Журнал ТО объекта'
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label(title).classes('text-h4')
            ui.button(
                'Добавить',
                on_click=lambda: _show_record_dialog(
                    record_id=None,
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
                    {'name': 'Акт ТО', 'label': 'Акт ТО', 'field': 'Акт ТО'},
                    {'name': 'Допработы', 'label': 'Допработы', 'field': 'Допработы'},
                ],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')

        def on_row_click(e) -> None:
            row = e.args[1]
            full_row = next((item for item in row_cache if item['id'] == row['id']), row)
            record = full_row['_record']
            _show_record_dialog(
                record_id=record.id,
                object_id=record.object_id,
                defaults={
                    'object_id': record.object_id,
                    'date': record.date,
                    'act_to': record.act_to,
                    'extra_works_flag': record.extra_works_flag,
                },
                on_saved=refresh_table,
            )

        table.on('rowClick', on_row_click)
        refresh_table()
        if on_changed:
            on_changed(refresh_table)

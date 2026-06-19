from nicegui import ui
from models.object_model import Object, SYSTEM_CODES
from messages import guard_action
from services.database import get_db
from services.object_service import get_object_filter_autocomplete, get_objects_filtered
from components.object_detail import show_object_detail_dialog
from layout import FIELD, GRID_FILTERS, INPUT
from list_table import apply_table_state, object_filters_hint

_FILTER_FIELDS = {
    'number_in_db': 'Номер в БД',
    'inv_number': 'Инвентарный номер',
    'address': 'Адрес',
    'region': 'Регион',
    'object_type': 'Тип объекта',
    'responsible': 'Ответственный',
    'system_type': 'Тип системы',
}


def _format_system_codes(obj: Object) -> str:
    codes = sorted(
        (flag.system_code for flag in obj.system_flags),
        key=SYSTEM_CODES.index,
    )
    if codes:
        return ', '.join(codes)
    return obj.system_type or ''


def content(on_changed=None):
    filter_values = {field: '' for field in _FILTER_FIELDS}
    filter_inputs: dict[str, ui.input] = {}

    def refresh_table():
        def load() -> None:
            with get_db() as db:
                active = {k: v for k, v in filter_values.items() if v not in (None, '')}
                objects = get_objects_filtered(db, active)
                total = db.query(Object).count()
                autocomplete = get_object_filter_autocomplete(db)

            for field, widget in filter_inputs.items():
                widget.set_autocomplete(autocomplete.get(field, []))

            rows = [{
                'id': o.id,
                'Номер в БД': o.number_in_db,
                'Инв. №': o.inv_number,
                'Адрес': o.address,
                'Регион': o.region.name if o.region else '',
                'Тип': o.object_type,
                'Собственность': o.ownership,
                'Стоимость': o.cost,
                'Ответственный': o.responsible.name if o.responsible else '',
                'Режим ТО': o.maintenance_mode,
                'Системы': _format_system_codes(o),
            } for o in objects]
            apply_table_state(
                table,
                rows,
                count_label,
                shown=len(rows),
                total=total,
                unit='объектов',
                filters_active=bool(active),
                filter_hint=object_filters_hint(active, _FILTER_FIELDS),
            )

        guard_action(load)

    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label('Список объектов').classes('text-h4')
            ui.button(
                'Добавить объект',
                on_click=lambda: show_object_detail_dialog(on_changed=refresh_table),
                icon='add',
            ).props('outline no-caps')

        with ui.element('div').classes(GRID_FILTERS):
            for field, label in _FILTER_FIELDS.items():
                with ui.element('div').classes(FIELD):
                    filter_inputs[field] = ui.input(
                        placeholder=label,
                        on_change=lambda e, f=field: filter_values.update({f: e.value}) or refresh_table(),
                    ).classes(INPUT)

        count_label = ui.label('').classes('text-caption')

        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'Номер в БД', 'label': '№ в БД', 'field': 'Номер в БД', 'align': 'center'},
                    {'name': 'Инв. №', 'label': 'Инвентарный номер', 'field': 'Инв. №', 'align': 'left'},
                    {'name': 'Адрес', 'label': 'Адрес', 'field': 'Адрес', 'align': 'left'},
                    {'name': 'Регион', 'label': 'Регион', 'field': 'Регион', 'align': 'center'},
                    {'name': 'Тип', 'label': 'Тип объекта', 'field': 'Тип', 'align': 'left'},
                    {'name': 'Собственность', 'label': 'Собственность', 'field': 'Собственность', 'align': 'center'},
                    {'name': 'Стоимость', 'label': 'Стоимость', 'field': 'Стоимость', 'align': 'right'},
                    {'name': 'Ответственный', 'label': 'Ответственный', 'field': 'Ответственный'},
                    {'name': 'Режим ТО', 'label': 'Режим ТО', 'field': 'Режим ТО', 'align': 'center'},
                    {'name': 'Системы', 'label': 'Типы систем', 'field': 'Системы', 'align': 'left'},
                ],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')

        def on_row_click(e):
            row = e.args[1]
            show_object_detail_dialog(row['id'], on_changed=refresh_table)

        table.on('rowClick', on_row_click)
        refresh_table()
        if on_changed:
            on_changed(refresh_table)

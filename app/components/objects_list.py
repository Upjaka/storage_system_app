from nicegui import ui
from services.database import get_db
from services.object_service import get_objects_filtered
from components.object_detail import show_object_detail_dialog
from layout import FIELD, GRID_FILTERS, INPUT

def content():
    filters = {
        'number_in_db': 'Номер в БД',
        'inv_number': 'Инвентарный номер',
        'address': 'Адрес',
        'region': 'Регион',
        'object_type': 'Тип объекта',
        'responsible': 'Ответственный',
        'system_type': 'Тип системы'
    }

    def refresh_table():
        with get_db() as db:
            active = {k: v for k, v in filters.items() if v}
            objects = get_objects_filtered(db, active)
        rows = [{
            'id': o.id,
            'Номер в БД': o.number_in_db,
            'Инв. №': o.inv_number,
            'Адрес': o.address,
            'Регион': o.region,
            'Тип': o.object_type,
            'Собственность': o.ownership,
            'Стоимость': o.cost,
            'Ответственный': o.responsible,
            'Режим ТО': o.maintenance_mode,
            'Система': o.system_type
        } for o in objects]
        table.rows = rows

    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label('Список объектов').classes('text-h4')
            ui.button(
                'Добавить объект',
                on_click=lambda: show_object_detail_dialog(),
            ).props('flat')

        with ui.element('div').classes(GRID_FILTERS):
            for field, placeholder in filters.items():
                with ui.element('div').classes(FIELD):
                    ui.input(
                        label=placeholder,
                        on_change=lambda e, f=field: filters.update({f: e.value}) or refresh_table(),
                    ).classes(INPUT)

        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'Номер в БД', 'label': 'Номер в БД', 'field': 'Номер в БД'},
                    {'name': 'Инв. №', 'label': 'Инвентарный номер', 'field': 'Инв. №'},
                    {'name': 'Адрес', 'label': 'Адрес', 'field': 'Адрес'},
                    {'name': 'Ответственный', 'label': 'Ответственный', 'field': 'Ответственный'},
                    {'name': 'Система', 'label': 'Тип системы', 'field': 'Система'},
                ],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')
        table.on('rowClick', lambda e: show_object_detail_dialog(e.args['row']['id']))
        refresh_table()

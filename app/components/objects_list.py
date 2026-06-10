from nicegui import ui
from models.object_model import Object
from services.database import get_db
from services.object_service import get_objects_filtered
from services.reference_service import get_regions, get_responsibles
from components.object_detail import show_object_detail_dialog
from layout import FIELD, GRID_FILTERS, INPUT

_TEXT_FILTER_FIELDS = {
    'number_in_db': 'Номер в БД',
    'inv_number': 'Инвентарный номер',
    'address': 'Адрес',
    'object_type': 'Тип объекта',
    'system_type': 'Тип системы',
}

_REFERENCE_FILTER_FIELDS = {
    'region_id': 'Регион',
    'responsible_id': 'Ответственный',
}


def content(on_changed=None):
    filter_values = {
        **{field: '' for field in _TEXT_FILTER_FIELDS},
        **{field: None for field in _REFERENCE_FILTER_FIELDS},
    }

    def refresh_table():
        with get_db() as db:
            active = {k: v for k, v in filter_values.items() if v not in (None, '')}
            objects = get_objects_filtered(db, active)
            total = db.query(Object).count()
            regions = get_regions(db)
            responsibles = get_responsibles(db)

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
            'Система': o.system_type,
        } for o in objects]
        table.rows = rows
        count_label.set_text(f'Объектов в базе: {total}')

        region_filter.options = {None: 'Все', **{r.id: r.name for r in regions}}
        responsible_filter.options = {None: 'Все', **{r.id: r.name for r in responsibles}}

    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label('Список объектов').classes('text-h4')
            ui.button(
                'Добавить объект',
                on_click=lambda: show_object_detail_dialog(on_changed=refresh_table),
                icon='add',
            ).props('outline no-caps')

        with ui.element('div').classes(GRID_FILTERS):
            for field, label in _TEXT_FILTER_FIELDS.items():
                with ui.element('div').classes(FIELD):
                    ui.input(
                        label=label,
                        on_change=lambda e, f=field: filter_values.update({f: e.value}) or refresh_table(),
                    ).classes(INPUT)

            with ui.element('div').classes(FIELD):
                region_filter = ui.select(
                    label=_REFERENCE_FILTER_FIELDS['region_id'],
                    options={None: 'Все'},
                    value=None,
                    on_change=lambda e: filter_values.update({'region_id': e.value}) or refresh_table(),
                ).classes(INPUT)

            with ui.element('div').classes(FIELD):
                responsible_filter = ui.select(
                    label=_REFERENCE_FILTER_FIELDS['responsible_id'],
                    options={None: 'Все'},
                    value=None,
                    on_change=lambda e: filter_values.update({'responsible_id': e.value}) or refresh_table(),
                ).classes(INPUT)

        count_label = ui.label('').classes('text-caption')

        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'Номер в БД', 'label': 'Номер в БД', 'field': 'Номер в БД'},
                    {'name': 'Инв. №', 'label': 'Инвентарный номер', 'field': 'Инв. №'},
                    {'name': 'Адрес', 'label': 'Адрес', 'field': 'Адрес'},
                    {'name': 'Регион', 'label': 'Регион', 'field': 'Регион'},
                    {'name': 'Ответственный', 'label': 'Ответственный', 'field': 'Ответственный'},
                    {'name': 'Система', 'label': 'Тип системы', 'field': 'Система'},
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

from __future__ import annotations

from typing import Literal

from nicegui import ui

from layout import DIALOG, FIELD, FORM, GRID_2, INPUT
from list_table import apply_table_state, search_filter_hint
from messages import guard_action, run_db_action, show_error_from_exception
from services import catalog_service as cat
from services.database import get_db

CatalogKind = Literal['units', 'materials', 'work_types', 'maintenance_prices']

_TITLES = {
    'units': 'Единицы измерения',
    'materials': 'Материалы',
    'work_types': 'Виды работ',
    'maintenance_prices': 'Стоимость ТО',
}


def _unit_options(db) -> dict[int | None, str]:
    return {None: '—', **{unit.id: unit.name for unit in cat.get_units(db)}}


def _material_options(db) -> dict[int | None, str]:
    return {None: '—', **{item.id: item.name for item in cat.get_materials(db)}}


def _show_unit_dialog(row_id: int | None, current_name: str, usage: int, on_saved) -> None:
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        title = 'Добавить единицу измерения' if row_id is None else 'Редактирование единицы измерения'
        ui.label(title).classes('text-h5')
        name_input = ui.input(label='Единица измерения', value=current_name or '').classes(INPUT)
        if usage:
            ui.label(f'Привязано материалов: {usage}').classes('text-caption')

        def save() -> None:
            def action() -> None:
                with get_db() as db:
                    if row_id is None:
                        cat.create_unit(db, name_input.value)
                    else:
                        cat.update_unit(db, row_id, name_input.value)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    cat.delete_unit(db, row_id)
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if row_id and usage == 0:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def _show_material_dialog(row: dict | None, on_saved) -> None:
    try:
        with get_db() as db:
            unit_options = _unit_options(db)
    except Exception as exc:
        show_error_from_exception(exc)
        return

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label(
            'Добавить материал' if row is None else 'Редактирование материала',
        ).classes('text-h5')
        name_input = ui.input(label='Материал', value=row['name'] if row else '').classes(INPUT)
        unit_select = ui.select(
            label='Единица измерения',
            options=unit_options,
            value=row.get('unit_id') if row else None,
        ).classes(INPUT)
        cost_input = ui.number(
            label='Стоимость',
            value=row.get('cost', 0) if row else 0,
            step=0.01,
            format='%.2f',
        ).classes(INPUT)
        defect_input = ui.input(
            label='Дефект',
            value=row.get('defect', '') if row else '',
        ).classes(INPUT)
        link_input = ui.input(
            label='Ссылка',
            value=row.get('link', '') if row else '',
        ).classes(INPUT)
        usage = row.get('usage', 0) if row else 0
        if usage:
            ui.label(f'Привязано видов работ: {usage}').classes('text-caption')

        def save() -> None:
            payload = {
                'name': name_input.value,
                'unit_id': unit_select.value,
                'cost': cost_input.value,
                'defect': defect_input.value,
                'link': link_input.value,
            }

            def action() -> None:
                with get_db() as db:
                    if row is None:
                        cat.create_material(db, **payload)
                    else:
                        cat.update_material(db, row['id'], payload)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    cat.delete_material(db, row['id'])
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if row and usage == 0:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def _show_work_type_dialog(row: dict | None, on_saved) -> None:
    try:
        with get_db() as db:
            material_options = _material_options(db)
    except Exception as exc:
        show_error_from_exception(exc)
        return

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label(
            'Добавить вид работ' if row is None else 'Редактирование вида работ',
        ).classes('text-h5')
        with ui.element('div').classes(GRID_2):
            name_input = ui.input(
                label='Вид работ',
                value=row['name'] if row else '',
            ).classes(INPUT)
            cost_input = ui.number(
                label='Стоимость',
                value=row.get('cost', 0) if row else 0,
                step=0.01,
                format='%.2f',
            ).classes(INPUT)
            section_input = ui.input(
                label='Раздел',
                value=row.get('section', '') if row else '',
            ).classes(INPUT)
            material_select = ui.select(
                label='Материал',
                options=material_options,
                value=row.get('material_id') if row else None,
            ).classes(INPUT)
        output_input = ui.input(
            label='Вывод',
            value=row.get('output_text', '') if row else '',
        ).classes(INPUT)

        def save() -> None:
            payload = {
                'name': name_input.value,
                'cost': cost_input.value,
                'section': section_input.value,
                'output_text': output_input.value,
                'material_id': material_select.value,
            }

            def action() -> None:
                with get_db() as db:
                    if row is None:
                        cat.create_work_type(db, **payload)
                    else:
                        cat.update_work_type(db, row['id'], payload)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    cat.delete_work_type(db, row['id'])
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if row:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def _show_maintenance_price_dialog(row: dict | None, on_saved) -> None:
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label(
            'Добавить стоимость ТО' if row is None else 'Редактирование стоимости ТО',
        ).classes('text-h5')
        name_input = ui.input(
            label='Наименование оборудования',
            value=row['equipment_name'] if row else '',
        ).classes(INPUT)
        price_input = ui.number(
            label='Цена за единицу',
            value=row.get('unit_price', 0) if row else 0,
            step=0.01,
            format='%.2f',
        ).classes(INPUT)

        def save() -> None:
            payload = {
                'equipment_name': name_input.value,
                'unit_price': price_input.value,
            }

            def action() -> None:
                with get_db() as db:
                    if row is None:
                        cat.create_maintenance_price(db, **payload)
                    else:
                        cat.update_maintenance_price(db, row['id'], payload)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            def action() -> None:
                with get_db() as db:
                    cat.delete_maintenance_price(db, row['id'])
                    db.commit()

            if not run_db_action(action, success_message='Удалено'):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if row:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()


def _filter_autocomplete(kind: CatalogKind, db) -> list[str]:
    if kind == 'units':
        return [item.name for item in cat.get_units(db)]
    if kind == 'materials':
        return sorted({
            value
            for item in cat.get_materials(db)
            for value in (item.name, item.defect)
            if value
        })
    if kind == 'work_types':
        return sorted({
            value
            for item in cat.get_work_types(db)
            for value in (item.name, item.section, item.output_text)
            if value
        })
    return [item.equipment_name for item in cat.get_maintenance_prices(db)]


def _build_rows(kind: CatalogKind, db, needle: str) -> tuple[list[dict], int]:
    needle = needle.strip().lower()
    rows: list[dict] = []

    if kind == 'units':
        items = cat.get_units(db)
        for item in items:
            if needle and needle not in item.name.lower():
                continue
            rows.append({
                'id': item.id,
                'Наименование': item.name,
                'Материалов': cat.count_materials_for_unit(db, item.id),
                '_name': item.name,
                '_usage': cat.count_materials_for_unit(db, item.id),
            })
        return rows, len(items)

    if kind == 'materials':
        items = cat.get_materials(db)
        for item in items:
            haystack = ' '.join(filter(None, [item.name, item.defect])).lower()
            if needle and needle not in haystack:
                continue
            rows.append({
                'id': item.id,
                'Материал': item.name,
                'Ед. изм.': item.unit.name if item.unit else '',
                'Стоимость': item.cost,
                '_row': {
                    'id': item.id,
                    'name': item.name,
                    'unit_id': item.unit_id,
                    'cost': item.cost,
                    'defect': item.defect,
                    'link': item.link,
                    'usage': cat.count_work_types_for_material(db, item.id),
                },
            })
        return rows, len(items)

    if kind == 'work_types':
        items = cat.get_work_types(db)
        for item in items:
            haystack = ' '.join(filter(None, [item.name, item.section, item.output_text])).lower()
            if needle and needle not in haystack:
                continue
            rows.append({
                'id': item.id,
                'Вид работ': item.name,
                'Раздел': item.section or '',
                'Стоимость': item.cost,
                'Материал': item.material.name if item.material else '',
                '_row': {
                    'id': item.id,
                    'name': item.name,
                    'cost': item.cost,
                    'section': item.section,
                    'output_text': item.output_text,
                    'material_id': item.material_id,
                },
            })
        return rows, len(items)

    items = cat.get_maintenance_prices(db)
    for item in items:
        if needle and needle not in item.equipment_name.lower():
            continue
        rows.append({
            'id': item.id,
            'Оборудование': item.equipment_name,
            'Цена': item.unit_price,
            '_row': {
                'id': item.id,
                'equipment_name': item.equipment_name,
                'unit_price': item.unit_price,
            },
        })
    return rows, len(items)


_TABLE_COLUMNS = {
    'units': [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
        {'name': 'Наименование', 'label': 'Единица измерения', 'field': 'Наименование', 'align': 'center'},
        {'name': 'Материалов', 'label': 'Материалов', 'field': 'Материалов', 'align': 'right'},
    ],
    'materials': [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
        {'name': 'Материал', 'label': 'Материал', 'field': 'Материал', 'align': 'center'},
        {'name': 'Ед. изм.', 'label': 'Ед. изм.', 'field': 'Ед. изм.', 'align': 'center'},
        {'name': 'Стоимость', 'label': 'Стоимость', 'field': 'Стоимость', 'align': 'right'},
    ],
    'work_types': [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
        {'name': 'Вид работ', 'label': 'Вид работ', 'field': 'Вид работ', 'align': 'center'},
        {'name': 'Раздел', 'label': 'Раздел', 'field': 'Раздел', 'align': 'center'},
        {'name': 'Стоимость', 'label': 'Стоимость', 'field': 'Стоимость', 'align': 'right'},
        {'name': 'Материал', 'label': 'Материал', 'field': 'Материал', 'align': 'center'},
    ],
    'maintenance_prices': [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
        {'name': 'Оборудование', 'label': 'Оборудование', 'field': 'Оборудование', 'align': 'center'},
        {'name': 'Цена', 'label': 'Цена за ед.', 'field': 'Цена', 'align': 'right'},
    ],
}


def content(kind: CatalogKind, on_changed=None):
    title = _TITLES[kind]
    filter_text = {'name': ''}
    row_cache: list[dict] = []
    search_input: ui.input | None = None

    def refresh_table() -> None:
        def load() -> None:
            with get_db() as db:
                rows, total = _build_rows(kind, db, filter_text['name'])
                if search_input is not None:
                    search_input.set_autocomplete(_filter_autocomplete(kind, db))
            row_cache.clear()
            row_cache.extend(rows)
            display_rows = [{key: value for key, value in row.items() if not key.startswith('_')} for row in rows]
            needle = filter_text['name'].strip()
            apply_table_state(
                table,
                display_rows,
                count_label,
                shown=len(display_rows),
                total=total,
                unit='записей в справочнике',
                filters_active=bool(needle),
                filter_hint=search_filter_hint(needle, scope=title.lower(), total=total),
            )

        guard_action(load)

    def open_add_dialog() -> None:
        if kind == 'units':
            _show_unit_dialog(None, '', 0, refresh_table)
        elif kind == 'materials':
            _show_material_dialog(None, refresh_table)
        elif kind == 'work_types':
            _show_work_type_dialog(None, refresh_table)
        else:
            _show_maintenance_price_dialog(None, refresh_table)

    def on_row_click(e) -> None:
        row = e.args[1]
        full_row = next((item for item in row_cache if item['id'] == row['id']), row)
        if kind == 'units':
            _show_unit_dialog(
                full_row['id'],
                full_row['_name'],
                full_row['_usage'],
                refresh_table,
            )
        elif kind == 'materials':
            _show_material_dialog(full_row['_row'], refresh_table)
        elif kind == 'work_types':
            _show_work_type_dialog(full_row['_row'], refresh_table)
        else:
            _show_maintenance_price_dialog(full_row['_row'], refresh_table)

    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label(title).classes('text-h4')
            ui.button('Добавить', on_click=open_add_dialog, icon='add').props('outline no-caps')

        with ui.element('div').classes(FIELD):
            search_input = ui.input(
                placeholder='Поиск по наименованию',
                on_change=lambda e: filter_text.update({'name': e.value or ''}) or refresh_table(),
            ).classes(INPUT)

        count_label = ui.label('').classes('text-caption')

        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=_TABLE_COLUMNS[kind],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')

        table.on('rowClick', on_row_click)
        refresh_table()
        if on_changed:
            on_changed(refresh_table)

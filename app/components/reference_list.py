from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from nicegui import ui

from layout import DIALOG, FIELD, FORM, INPUT
from list_table import apply_table_state, search_filter_hint
from messages import guard_action, run_db_action
from services import reference_service as ref
from services.database import get_db

ReferenceKind = Literal['regions', 'responsibles']


@dataclass(frozen=True)
class _ReferenceConfig:
    title: str
    name_label: str
    max_length: int
    get_all: Callable
    count_usage: Callable
    create: Callable
    update: Callable
    delete: Callable


_CONFIGS: dict[ReferenceKind, _ReferenceConfig] = {
    'regions': _ReferenceConfig(
        title='Регионы',
        name_label='Регион',
        max_length=25,
        get_all=ref.get_regions,
        count_usage=ref.count_objects_for_region,
        create=ref.create_region,
        update=ref.update_region,
        delete=ref.delete_region,
    ),
    'responsibles': _ReferenceConfig(
        title='Ответственные',
        name_label='Ответственный',
        max_length=50,
        get_all=ref.get_responsibles,
        count_usage=ref.count_objects_for_responsible,
        create=ref.create_responsible,
        update=ref.update_responsible,
        delete=ref.delete_responsible,
    ),
}


def _show_add_dialog(config: _ReferenceConfig, on_saved: Callable[[], None]) -> None:
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label(f'Добавить: {config.name_label.lower()}').classes('text-h5')
        name_input = ui.input(label='Наименование').classes(INPUT).props(
            f'maxlength={config.max_length}',
        )

        def save() -> None:
            def action() -> None:
                with get_db() as db:
                    config.create(db, name_input.value)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        with ui.row().classes(f'{FORM} justify-end gap-2 mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            ui.button('Отмена', on_click=dialog.close, icon='close')

    dialog.open()


def _show_edit_dialog(
    config: _ReferenceConfig,
    row_id: int,
    current_name: str,
    usage_count: int,
    on_saved: Callable[[], None],
) -> None:
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label(f'Редактирование: {config.name_label.lower()}').classes('text-h5')
        name_input = ui.input(
            label='Наименование',
            value=current_name,
        ).classes(INPUT).props(f'maxlength={config.max_length}')
        if usage_count:
            ui.label(f'Привязано объектов: {usage_count}').classes('text-caption')

        def save() -> None:
            def action() -> None:
                with get_db() as db:
                    config.update(db, row_id, name_input.value)
                    db.commit()

            if not run_db_action(action):
                return
            dialog.close()
            on_saved()

        def remove() -> None:
            with ui.dialog() as confirm_dialog, ui.card().classes(DIALOG):
                ui.label('Удалить запись?').classes('text-h6')
                ui.label('Это действие нельзя отменить.').classes('text-caption')

                def confirm_remove() -> None:
                    def action() -> None:
                        with get_db() as db:
                            config.delete(db, row_id)
                            db.commit()

                    if not run_db_action(action, success_message='Удалено'):
                        return
                    confirm_dialog.close()
                    dialog.close()
                    on_saved()

                with ui.row().classes(f'{FORM} justify-end gap-2 mt-4'):
                    ui.button('Удалить', on_click=confirm_remove, icon='delete', color='red')
                    ui.button('Отмена', on_click=confirm_dialog.close, icon='close')

            confirm_dialog.open()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if usage_count == 0:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')

    dialog.open()


def content(kind: ReferenceKind, on_changed=None):
    config = _CONFIGS[kind]
    filter_text = {'name': ''}
    search_input: ui.input | None = None

    def refresh_table() -> None:
        def load() -> None:
            with get_db() as db:
                items = config.get_all(db)
                total = len(items)
                autocomplete_names = [item.name for item in items]
                rows = []
                needle = filter_text['name'].strip().lower()
                for item in items:
                    if needle and needle not in item.name.lower():
                        continue
                    rows.append({
                        'id': item.id,
                        'Наименование': item.name,
                        'Объектов': config.count_usage(db, item.id),
                    })

            if search_input is not None:
                search_input.set_autocomplete(autocomplete_names)

            needle = filter_text['name'].strip()
            apply_table_state(
                table,
                rows,
                count_label,
                shown=len(rows),
                total=total,
                unit='записей в справочнике',
                filters_active=bool(needle),
                filter_hint=search_filter_hint(needle, scope=config.title.lower(), total=total),
            )

        guard_action(load)

    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
            ui.label(config.title).classes('text-h4')
            ui.button(
                'Добавить',
                on_click=lambda: _show_add_dialog(config, refresh_table),
                icon='add',
            ).props('outline no-caps')

        with ui.element('div').classes(FIELD):
            search_input = ui.input(
                placeholder='Поиск по наименованию',
                on_change=lambda e: filter_text.update({'name': e.value or ''}) or refresh_table(),
            ).classes(INPUT)

        count_label = ui.label('').classes('text-caption')

        with ui.element('div').classes('w-full min-w-0 overflow-x-auto'):
            table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                    {'name': 'Наименование', 'label': 'Наименование', 'field': 'Наименование', 'align': 'center'},
                    {'name': 'Объектов', 'label': 'Объектов', 'field': 'Объектов', 'align': 'right'},
                ],
                rows=[],
                row_key='id',
                pagination={'rowsPerPage': 20},
            ).classes('w-full')

        def on_row_click(e) -> None:
            row = e.args[1]
            _show_edit_dialog(
                config,
                row['id'],
                row['Наименование'],
                row['Объектов'],
                refresh_table,
            )

        table.on('rowClick', on_row_click)
        refresh_table()
        if on_changed:
            on_changed(refresh_table)

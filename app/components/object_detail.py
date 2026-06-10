from nicegui import ui
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from services.database import get_db
from services.object_service import (
    get_object, update_object, create_object, delete_object, get_next_number_in_db,
)
from services.reference_service import get_regions, get_responsibles
from layout import DIALOG, FIELD, FORM, GRID_2, INPUT, SPAN_2
from services.object_validation import validate_create_data

# 'simple' — короткие сообщения для пользователя; 'verbose' — подробности для отладки
ERROR_MODE = 'simple'


def _integrity_message(exc: IntegrityError) -> str:
    raw = str(exc.orig) if exc.orig else str(exc)
    raw_lower = raw.lower()
    if 'number_in_db' in raw_lower:
        simple = 'Объект с таким номером в БД уже существует'
    elif 'inv_number' in raw_lower:
        simple = 'Объект с таким инвентарным номером уже существует'
    else:
        simple = 'Нарушено ограничение уникальности данных'
    if ERROR_MODE == 'verbose':
        return f'{simple}. {type(exc).__name__}: {raw}'
    return simple


def _reference_input(label: str, names: list[str]):
    """Text input with autocomplete; new values are created in справочник on save."""
    return ui.input(label=label, autocomplete=names).classes(INPUT)


def _load_reference_value(obj, field: str):
    if field == 'region_id':
        return obj.region.name if obj.region else None
    if field == 'responsible_id':
        return obj.responsible.name if obj.responsible else None
    return getattr(obj, field)


def _create_error_message(exc: Exception, data: dict) -> str:
    if isinstance(exc, IntegrityError):
        return _integrity_message(exc)
    if isinstance(exc, SQLAlchemyError):
        if ERROR_MODE == 'verbose':
            return f'Ошибка базы данных ({type(exc).__name__}): {exc} | данные: {data}'
        return 'Не удалось создать объект'
    if ERROR_MODE == 'verbose':
        return f'Непредвиденная ошибка ({type(exc).__name__}): {exc} | данные: {data}'
    return 'Произошла непредвиденная ошибка'


def show_object_detail_dialog(obj_id: int = None, on_changed=None):
    with get_db() as db:
        region_names = [r.name for r in get_regions(db)]
        responsible_names = [r.name for r in get_responsibles(db)]
        default_number_in_db = get_next_number_in_db(db) if obj_id is None else None

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label('Редактирование объекта' if obj_id else 'Создание объекта').classes('text-h5')

        form_data = {}

        with ui.column().classes(f'{FORM} gap-4 mt-2'):
            with ui.element('div').classes(GRID_2):
                with ui.element('div').classes(FIELD):
                    form_data['number_in_db'] = ui.number(
                        label='Номер в БД',
                        value=default_number_in_db,
                        step=1,
                        min=1,
                        max=1000,
                    ).classes(INPUT)
                with ui.element('div').classes(FIELD):
                    form_data['inv_number'] = ui.input(
                        label='Инвентарный номер',
                    ).classes(INPUT)
                with ui.element('div').classes(SPAN_2):
                    form_data['address'] = ui.textarea(
                        label='Адрес',
                    ).classes(INPUT)
                with ui.element('div').classes(FIELD):
                    form_data['region_id'] = _reference_input('Регион', region_names)
                with ui.element('div').classes(FIELD):
                    form_data['object_type'] = ui.input(
                        label='Тип объекта',
                    ).classes(INPUT)
                with ui.element('div').classes(SPAN_2):
                    form_data['ownership'] = ui.radio(
                        ['Собственность', 'Аренда'], value='Собственность',
                    )
                with ui.element('div').classes(FIELD):
                    form_data['cost'] = ui.number(
                        label='Стоимость', step=0.01, format='%.2f',
                    ).classes(INPUT)
                with ui.element('div').classes(FIELD):
                    form_data['responsible_id'] = _reference_input('Ответственный', responsible_names)
                with ui.element('div').classes(SPAN_2):
                    form_data['maintenance_mode'] = ui.radio(
                        ['ежемесячное', 'квартальное'], value='ежемесячное',
                    )
                with ui.element('div').classes(FIELD):
                    form_data['system_type'] = ui.select(
                        ['АПС', 'СОУЭ', 'АУГПТ', 'ВПВ'], value='АПС',
                    ).classes(INPUT)

        if obj_id:
            with get_db() as db:
                obj = get_object(db, obj_id)
                for key, widget in form_data.items():
                    widget.value = _load_reference_value(obj, key)

        def save():
            data = {key: widget.value for key, widget in form_data.items()}
            if not obj_id:
                validation_error = validate_create_data(data, error_mode=ERROR_MODE)
                if validation_error:
                    ui.notify(validation_error, type='negative')
                    return
                try:
                    with get_db() as db:
                        create_object(db, data)
                except Exception as exc:
                    ui.notify(_create_error_message(exc, data), type='negative')
                    return
            else:
                with get_db() as db:
                    update_object(db, obj_id, data)
            dialog.close()
            ui.notify('Сохранено', type='positive')
            if on_changed:
                on_changed()

        def remove():
            if obj_id:
                with get_db() as db:
                    delete_object(db, obj_id)
                dialog.close()
                ui.notify('Удалено', type='warning')
                if on_changed:
                    on_changed()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if obj_id:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()

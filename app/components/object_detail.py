from nicegui import ui
from services.database import get_db
from services.object_service import (
    get_object, update_object, create_object, delete_object, get_next_number_in_db,
)
from services.reference_service import get_regions, get_responsibles
from services.system_flag_service import get_system_codes, primary_system_code
from services.composition_service import get_composition_counts, upsert_composition
from services.documents_service import get_documents, upsert_documents
from models.object_model import SYSTEM_CODES
from models.composition_fields import (
    COMPOSITION_FIELD_GROUPS,
    COMPOSITION_FIELD_LABELS,
    FLOAT_COMPOSITION_FIELDS,
)
from models.operations_model import DOCUMENT_FIELD_LABELS
from components.maintenance_list import content as maintenance_tab_content
from components.extra_works_list import content as extra_works_tab_content
from components.print_component import launch_print_page
from services.report_service import object_passport_page
from layout import DIALOG, FIELD, FORM, GRID_2, INPUT, SPAN_2
from messages import (
    ERROR_MODE,
    run_db_action,
    show_error,
    show_error_from_exception,
    show_success,
    show_warning,
    user_message_from_exception,
)
from services.object_validation import validate_create_data


def _reference_input(label: str, names: list[str]):
    return ui.input(label=label, autocomplete=names).classes(INPUT)


def _load_reference_value(obj, field: str):
    if field == 'region_id':
        return obj.region.name if obj.region else None
    if field == 'responsible_id':
        return obj.responsible.name if obj.responsible else None
    return getattr(obj, field)


def _collect_form_data(form_data: dict) -> dict:
    data = {}
    for key, widget in form_data.items():
        if key == 'system_codes':
            data['system_codes'] = [
                code for code, checkbox in widget.items() if checkbox.value
            ]
        else:
            data[key] = widget.value
    codes = data.get('system_codes', [])
    data['system_type'] = primary_system_code(codes) if codes else 'АПС'
    return data


def _collect_composition_data(composition_widgets: dict) -> dict:
    return {field: widget.value for field, widget in composition_widgets.items()}


def show_object_detail_dialog(obj_id: int = None, on_changed=None):
    try:
        with get_db() as db:
            region_names = [r.name for r in get_regions(db)]
            responsible_names = [r.name for r in get_responsibles(db)]
            default_number_in_db = get_next_number_in_db(db) if obj_id is None else None
            composition_counts = get_composition_counts(db, obj_id) if obj_id else {}
            document_values = get_documents(db, obj_id) if obj_id else {}
    except Exception as exc:
        show_error_from_exception(exc)
        return

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label('Редактирование объекта' if obj_id else 'Создание объекта').classes('text-h5')

        form_data = {}
        composition_widgets: dict = {}
        document_inputs: dict = {}

        with ui.tabs().classes('w-full mt-2') as tabs:
            main_tab = ui.tab('Основное')
            composition_tab = ui.tab('Состав оборудования')
            maintenance_tab = ui.tab('Журнал ТО')
            extra_works_tab = ui.tab('Допработы')
            documents_tab = ui.tab('Документы')

        with ui.tab_panels(tabs, value=main_tab).classes('w-full'):
            with ui.tab_panel(main_tab):
                with ui.column().classes(f'{FORM} gap-4'):
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
                                ['Собственность', 'Аренда', 'н/д'], value='Собственность',
                            )
                        with ui.element('div').classes(FIELD):
                            form_data['cost'] = ui.number(
                                label='Стоимость', step=0.01, format='%.2f',
                            ).classes(INPUT)
                        with ui.element('div').classes(FIELD):
                            form_data['responsible_id'] = _reference_input(
                                'Ответственный', responsible_names,
                            )
                        with ui.element('div').classes(SPAN_2):
                            form_data['maintenance_mode'] = ui.radio(
                                ['ежемесячное', 'квартальное'], value='ежемесячное',
                            )
                        with ui.element('div').classes(SPAN_2):
                            ui.label('Типы систем').classes('text-caption')
                            with ui.row().classes('gap-4 flex-wrap'):
                                form_data['system_codes'] = {
                                    code: ui.checkbox(code, value=code == 'АПС')
                                    for code in SYSTEM_CODES
                                }

            with ui.tab_panel(composition_tab):
                if obj_id is None:
                    ui.label(
                        'Сначала сохраните объект, затем заполните состав оборудования.',
                    ).classes('text-caption')
                else:
                    with ui.column().classes(f'{FORM} gap-4'):
                        for group_name, fields in COMPOSITION_FIELD_GROUPS:
                            ui.label(group_name).classes('text-subtitle2')
                            with ui.element('div').classes(GRID_2):
                                for field in fields:
                                    is_float = field in FLOAT_COMPOSITION_FIELDS
                                    composition_widgets[field] = ui.number(
                                        label=COMPOSITION_FIELD_LABELS[field],
                                        value=composition_counts.get(field, 0),
                                        step=0.01 if is_float else 1,
                                        min=0,
                                    ).classes(INPUT)

            with ui.tab_panel(maintenance_tab):
                if obj_id is None:
                    ui.label('Сначала сохраните объект.').classes('text-caption')
                else:
                    maintenance_tab_content(object_id=obj_id)

            with ui.tab_panel(extra_works_tab):
                if obj_id is None:
                    ui.label('Сначала сохраните объект.').classes('text-caption')
                else:
                    extra_works_tab_content(object_id=obj_id)

            with ui.tab_panel(documents_tab):
                if obj_id is None:
                    ui.label('Сначала сохраните объект.').classes('text-caption')
                else:
                    with ui.column().classes(f'{FORM} gap-4'):
                        for field, label in DOCUMENT_FIELD_LABELS.items():
                            document_inputs[field] = ui.input(
                                label=label,
                                value=document_values.get(field) or '',
                            ).classes(INPUT)

                        def save_documents() -> None:
                            def action() -> None:
                                with get_db() as db:
                                    upsert_documents(
                                        db,
                                        obj_id,
                                        {field: widget.value for field, widget in document_inputs.items()},
                                    )
                                    db.commit()

                            run_db_action(action, success_message='Документы сохранены')

                        ui.button('Сохранить документы', on_click=save_documents, icon='save')

        if obj_id:
            try:
                with get_db() as db:
                    obj = get_object(db, obj_id)
                    if obj is None:
                        show_error('Объект не найден')
                        return
                    active_codes = set(get_system_codes(db, obj_id))
                    for key, widget in form_data.items():
                        if key == 'system_codes':
                            for code, checkbox in widget.items():
                                checkbox.value = code in active_codes
                        else:
                            widget.value = _load_reference_value(obj, key)
            except Exception as exc:
                show_error_from_exception(exc)
                return

        if obj_id is None:
            composition_tab.disable()
            maintenance_tab.disable()
            extra_works_tab.disable()
            documents_tab.disable()

        def save():
            data = _collect_form_data(form_data)
            if not data.get('system_codes'):
                show_warning('Выберите хотя бы один тип системы')
                return
            if not obj_id:
                validation_error = validate_create_data(data, error_mode=ERROR_MODE)
                if validation_error:
                    show_error(validation_error)
                    return
                try:
                    with get_db() as db:
                        create_object(db, data)
                except Exception as exc:
                    show_error(user_message_from_exception(exc, context=data))
                    return
            else:
                try:
                    with get_db() as db:
                        update_object(db, obj_id, data)
                    if composition_widgets:
                        with get_db() as db:
                            upsert_composition(
                                db,
                                obj_id,
                                _collect_composition_data(composition_widgets),
                            )
                            db.commit()
                except Exception as exc:
                    show_error(user_message_from_exception(exc, context=data))
                    return
            dialog.close()
            show_success('Сохранено')
            if on_changed:
                on_changed()

        def remove():
            if obj_id:
                try:
                    with get_db() as db:
                        delete_object(db, obj_id)
                except Exception as exc:
                    show_error_from_exception(exc)
                    return
                dialog.close()
                show_success('Удалено')
                if on_changed:
                    on_changed()

        with ui.row().classes(f'{FORM} justify-between mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if obj_id:
                def print_passport() -> None:
                    try:
                        with get_db() as db:
                            page = object_passport_page(db, obj_id)
                        launch_print_page(page)
                    except ValueError as exc:
                        show_error(str(exc))

                ui.button('Печать паспорта', on_click=print_passport, icon='print').props('outline')
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()

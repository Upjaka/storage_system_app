from nicegui import ui
from services.database import get_db
from services.object_service import get_object, update_object, create_object, delete_object

def show_object_detail_dialog(obj_id: int = None):
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl'):
        ui.label('Редактирование объекта' if obj_id else 'Создание объекта').classes('text-h5')
        form_data = {
            'number_in_db': ui.number(label='Номер в БД', step=1, min=1, max=1000),
            'inv_number': ui.input(label='Инвентарный номер'),
            'address': ui.textarea(label='Адрес'),
            'region': ui.input(label='Регион'),
            'object_type': ui.input(label='Тип объекта'),
            'ownership': ui.radio(['Собственность', 'Аренда'], value='Собственность'),
            'cost': ui.number(label='Стоимость', step=0.01, format='%.2f'),
            'responsible': ui.input(label='Ответственный'),
            'maintenance_mode': ui.radio(['ежемесячное', 'квартальное'], value='ежемесячное'),
            'system_type': ui.select(['АПС', 'СОУЭ', 'АУГПТ', 'ВПВ'], value='АПС')
        }

        if obj_id:
            with get_db() as db:
                obj = get_object(db, obj_id)
                for key, widget in form_data.items():
                    widget.value = getattr(obj, key)

        def save():
            data = {key: widget.value for key, widget in form_data.items()}
            with get_db() as db:
                if obj_id:
                    update_object(db, obj_id, data)
                else:
                    create_object(db, data)
            dialog.close()
            ui.notify('Сохранено', type='positive')
            ui.open('/')   # перезагружаем главную страницу

        def remove():
            if obj_id:
                with get_db() as db:
                    delete_object(db, obj_id)
                dialog.close()
                ui.notify('Удалено', type='warning')
                ui.open('/')

        with ui.row().classes('justify-between w-full mt-4'):
            ui.button('Сохранить', on_click=save, icon='save')
            if obj_id:
                ui.button('Удалить', on_click=remove, icon='delete', color='red')
            ui.button('Отмена', on_click=dialog.close, icon='close')
    dialog.open()
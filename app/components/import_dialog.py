from nicegui import ui
from services.database import get_db
from services.import_service import import_from_access
import pyodbc
from layout import DIALOG, FORM, INPUT

def show_import_dialog():
    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label('Импорт из Access').classes('text-h5')

        with ui.column().classes(f'{FORM} gap-4 mt-2'):
            file_input = ui.upload(
                label='Выберите файл Access (.mdb или .accdb)',
                auto_upload=True,
                on_upload=lambda e: load_tables(e, table_select, file_path, dialog, progress),
            ).props('accept=".mdb,.accdb"').classes(INPUT)
            file_path = ui.label('Файл не выбран').classes('text-caption')

            table_select = ui.select(
                label='Таблица для импорта',
                options=[],
                with_input=True,
            ).classes(INPUT).set_visibility(False)

            progress = ui.linear_progress(value=0).classes(INPUT).set_visibility(False)

        def do_import():
            if not file_input.value or not table_select.value:
                ui.notify('Выберите файл и таблицу', type='warning')
                return
            try:
                with get_db() as db:
                    count = import_from_access(db, file_input.value[0].name, table_select.value)
                ui.notify(f'Импортировано {count} записей', type='positive')
                dialog.close()
                ui.open('/')
            except Exception as e:
                ui.notify(f'Ошибка: {e}', type='negative')

        def load_tables(upload_event, select_widget, path_label, dlg, prog):
            path_label.set_text(f'Файл: {upload_event.name}')
            try:
                conn_str = (
                    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                    fr'DBQ={upload_event.name};'
                )
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()
                tables = cursor.tables(tableType='TABLE')
                table_names = [row.table_name for row in tables]
                conn.close()
                select_widget.options = table_names
                if table_names:
                    select_widget.value = table_names[0]
                    select_widget.set_visibility(True)
                    prog.set_visibility(True)
                else:
                    ui.notify('В базе данных нет таблиц', type='warning')
                    select_widget.set_visibility(False)
                    prog.set_visibility(False)
            except Exception as e:
                ui.notify(f'Ошибка получения списка таблиц: {e}', type='negative')
                select_widget.options = []
                select_widget.set_visibility(False)
                prog.set_visibility(False)

        with ui.row().classes(f'{FORM} justify-end gap-2 mt-4'):
            ui.button('Импортировать', on_click=do_import, icon='publish', color='primary')
            ui.button('Отмена', on_click=dialog.close, icon='close')

    dialog.open()

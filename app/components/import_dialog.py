from pathlib import Path
import tempfile

import pyodbc
from nicegui import ui

from layout import DIALOG, FORM, INPUT
from services.database import get_db
from services.import_service import import_from_access

UPLOAD_DIR = Path(tempfile.gettempdir()) / 'storage_system_app' / 'access_uploads'


def show_import_dialog(on_changed=None):
    upload_state = {'path': None}

    async def load_tables(upload_event, select_widget, path_label, prog):
        safe_name = Path(upload_event.file.name).name
        path_label.set_text(f'Файл: {safe_name}')
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            save_path = UPLOAD_DIR / safe_name
            await upload_event.file.save(save_path)
            upload_state['path'] = str(save_path.resolve())

            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                fr'DBQ={upload_state["path"]};'
            )
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            tables = cursor.tables(tableType='TABLE')
            table_names = [row.table_name for row in tables]
            conn.close()
            select_widget.options = table_names
            if table_names:
                select_widget.value = (
                    'Объекты' if 'Объекты' in table_names else table_names[0]
                )
                select_widget.set_visibility(True)
                prog.set_visibility(True)
            else:
                ui.notify('В базе данных нет таблиц', type='warning')
                select_widget.set_visibility(False)
                prog.set_visibility(False)
        except Exception as e:
            upload_state['path'] = None
            ui.notify(f'Ошибка получения списка таблиц: {e}', type='negative')
            if select_widget is not None:
                select_widget.options = []
                select_widget.set_visibility(False)
            if prog is not None:
                prog.set_visibility(False)

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        ui.label('Импорт из Access').classes('text-h5')

        with ui.column().classes(f'{FORM} gap-4 mt-2'):
            file_path = ui.label('Файл не выбран').classes('text-caption')

            table_select = ui.select(
                label='Таблица для импорта',
                options=[],
                with_input=True,
            ).classes(INPUT)
            table_select.set_visibility(False)

            progress = ui.linear_progress(value=0).classes(INPUT)
            progress.set_visibility(False)

            async def handle_upload(upload_event):
                await load_tables(upload_event, table_select, file_path, progress)

            ui.upload(
                label='Выберите файл Access (.mdb или .accdb)',
                auto_upload=True,
                on_upload=handle_upload,
            ).props('accept=".mdb,.accdb"').classes(INPUT)

        async def do_import():
            if not upload_state['path'] or not table_select.value:
                ui.notify('Выберите файл и таблицу', type='warning')
                return
            try:
                with get_db() as db:
                    count = import_from_access(db, upload_state['path'], table_select.value)
                ui.notify(f'Импортировано {count} записей', type='positive')
                dialog.close()
                if on_changed:
                    on_changed()
            except Exception as e:
                ui.notify(f'Ошибка: {e}', type='negative')

        with ui.row().classes(f'{FORM} justify-end gap-2 mt-4'):
            ui.button('Импортировать', on_click=do_import, icon='publish', color='primary')
            ui.button('Отмена', on_click=dialog.close, icon='close')

    dialog.open()

from pathlib import Path

import tempfile



import pyodbc

from nicegui import ui



from layout import DIALOG, FORM, INPUT

from services.database import get_db

from services.import_service import ImportReport, import_from_access, import_full_access



UPLOAD_DIR = Path(tempfile.gettempdir()) / 'storage_system_app' / 'access_uploads'



IMPORT_MODE_FULL = 'Полный импорт'

IMPORT_MODE_TABLE = 'Одна таблица'





def _show_validation_report(report: ImportReport, *, on_close=None) -> None:

    with ui.dialog() as result_dialog, ui.card().classes(DIALOG):

        ui.label('Результат импорта').classes('text-h5')



        with ui.column().classes('w-full gap-1 mt-2'):

            ui.label('Импортировано').classes('text-subtitle2')

            for line in report.count_lines():

                ui.label(line).classes('text-sm')



            if report.has_warnings:

                ui.label('Предупреждения').classes('text-subtitle2 mt-3 text-orange')

                for line in report.warning_lines():

                    ui.label(line).classes('text-sm text-orange')

            else:

                ui.label('Предупреждений нет').classes('text-sm text-positive mt-3')



        def close_dialog() -> None:

            result_dialog.close()

            if on_close:

                on_close()



        with ui.row().classes(f'{FORM} justify-end mt-4'):

            ui.button('Закрыть', on_click=close_dialog, icon='check')



    result_dialog.open()





def show_import_dialog(on_changed=None):

    upload_state = {'path': None}

    ui_state = {'importing': False}



    async def load_tables(upload_event, select_widget, path_label, prog, status_label):

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

            prog.set_visibility(False)

            status_label.set_text('')

        except Exception as e:

            upload_state['path'] = None

            ui.notify(f'Ошибка получения списка таблиц: {e}', type='negative')

            if select_widget is not None:

                select_widget.options = []

            prog.set_visibility(False)

            status_label.set_text('')



    def _update_table_select_visibility() -> None:

        is_table_mode = mode_select.value == IMPORT_MODE_TABLE

        table_select.set_visibility(is_table_mode and bool(upload_state['path']))



    with ui.dialog() as dialog, ui.card().classes(DIALOG):

        ui.label('Импорт из Access').classes('text-h5')



        with ui.column().classes(f'{FORM} gap-4 mt-2'):

            file_path = ui.label('Файл не выбран').classes('text-caption')



            mode_select = ui.radio(

                [IMPORT_MODE_FULL, IMPORT_MODE_TABLE],

                value=IMPORT_MODE_FULL,

            ).props('inline')



            table_select = ui.select(

                label='Таблица для импорта',

                options=[],

                with_input=True,

            ).classes(INPUT)

            table_select.set_visibility(False)



            status_label = ui.label('').classes('text-caption')

            progress = ui.linear_progress(value=0).props('instant-feedback')

            progress.set_visibility(False)



            async def handle_upload(upload_event):

                await load_tables(upload_event, table_select, file_path, progress, status_label)

                _update_table_select_visibility()



            def on_mode_change():

                _update_table_select_visibility()



            mode_select.on('update:model-value', on_mode_change)



            ui.upload(

                label='Выберите файл Access (.mdb или .accdb)',

                auto_upload=True,

                on_upload=handle_upload,

            ).props('accept=".mdb,.accdb"').classes(INPUT)



        async def do_import():

            if ui_state['importing']:

                return

            if not upload_state['path']:

                ui.notify('Выберите файл', type='warning')

                return

            if mode_select.value == IMPORT_MODE_TABLE and not table_select.value:

                ui.notify('Выберите таблицу', type='warning')

                return



            ui_state['importing'] = True

            import_button.disable()

            progress.set_visibility(True)

            progress.value = 0

            status_label.set_text('Подготовка…')



            def on_progress(label: str, step: int, total_steps: int) -> None:

                progress.value = step / total_steps if total_steps else 0

                status_label.set_text(label)



            try:

                with get_db() as db:

                    if mode_select.value == IMPORT_MODE_FULL:

                        report = import_full_access(

                            db,

                            upload_state['path'],

                            on_progress=on_progress,

                        )

                    else:

                        on_progress('Импорт таблицы…', 0, 1)

                        count = import_from_access(

                            db,

                            upload_state['path'],

                            table_select.value,

                        )

                        on_progress('Готово', 1, 1)

                        report = ImportReport(objects=count)



                dialog.close()



                def after_report() -> None:

                    if on_changed:

                        on_changed()



                if mode_select.value == IMPORT_MODE_FULL:

                    notify_type = 'warning' if report.has_warnings else 'positive'

                    ui.notify(report.summary_message(), type=notify_type)

                    _show_validation_report(report, on_close=after_report)

                else:

                    ui.notify(f'Импортировано записей: {report.objects}', type='positive')

                    after_report()

            except Exception as e:

                progress.set_visibility(False)

                status_label.set_text('')

                ui.notify(f'Ошибка импорта: {e}', type='negative')

            finally:

                ui_state['importing'] = False

                import_button.enable()



        with ui.row().classes(f'{FORM} justify-end gap-2 mt-4'):

            import_button = ui.button(

                'Импортировать',

                on_click=do_import,

                icon='publish',

                color='primary',

            )

            ui.button('Отмена', on_click=dialog.close, icon='close')



    dialog.open()


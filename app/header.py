from contextlib import contextmanager
from nicegui import ui

@contextmanager
def frame(title: str, version: str, import_callback):
    """Контекстный менеджер для хедера приложения."""
    with ui.header(elevated=True).classes('items-center justify-between'):
        ui.label(title).classes('text-h5')
        ui.label(f'v{version}').classes('text-caption')
        ui.button('Импорт из Access', on_click=import_callback,
                  icon='cloud_upload').props('flat').classes('bg-white text-black')
    yield
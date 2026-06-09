from contextlib import contextmanager
from nicegui import ui
from layout import PAGE

@contextmanager
def frame(title: str, version: str, import_callback):
    """Контекстный менеджер для хедера приложения."""
    with ui.header(elevated=True).classes('px-4'):
        with ui.row().classes(f'{PAGE} items-center justify-between gap-4'):
            with ui.row().classes('items-center gap-3 min-w-0'):
                ui.label(title).classes('text-h5 truncate')
                ui.label(f'v{version}').classes('text-caption shrink-0')
            ui.button(
                'Импорт из Access',
                on_click=import_callback,
                icon='cloud_upload',
            ).props('flat').classes('bg-white text-black shrink-0')
    yield

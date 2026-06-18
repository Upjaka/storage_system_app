from collections.abc import Callable

from nicegui import ui
from layout import CONTENT


def render(
    title: str,
    version: str,
    import_callback: Callable[[], None],
    menu_callback: Callable[[], None] | None = None,
):
    """Render the application header bar."""
    with ui.header(elevated=True):
        with ui.row().classes(f'{CONTENT} items-center justify-between gap-4 w-full'):
            with ui.row().classes('items-center gap-3 min-w-0'):
                if menu_callback is not None:
                    ui.button(icon='menu', on_click=menu_callback).props('flat')
                ui.label(title).classes('text-h5 truncate')
                ui.label(f'v{version}').classes('text-caption shrink-0')
            ui.button(
                'Импорт из Access',
                on_click=import_callback,
                icon='cloud_upload',
            ).props('flat').classes('bg-white text-black shrink-0')

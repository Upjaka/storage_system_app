from contextlib import contextmanager

from nicegui import ui

import header
import sidebar
from layout import CONTENT


@contextmanager
def app_shell(title: str, version: str, import_callback):
    """Top-level page shell: theme, header, left drawer, and main content area."""
    ui.colors(
        primary='#18181b',
        secondary='#f4f4f5',
        positive='#4caf50',
        negative='#ef4444',
        warning='#f59e0b',
        info='#3b82f6',
        accent='#e4e4e7',
    )

    with sidebar.drawer() as left_drawer:
        pass

    header.render(
        title=title,
        version=version,
        import_callback=import_callback,
        menu_callback=left_drawer.toggle,
    )

    with ui.column().classes('w-full flex-grow px-2 py-4').style('min-height: 0'):
        with ui.column().classes(f'{CONTENT} gap-4 min-h-0'):
            yield

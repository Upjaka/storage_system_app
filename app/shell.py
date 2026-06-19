import logging
from contextlib import contextmanager

from nicegui import app, ui

import header
import sidebar
from layout import CONTENT
from messages import show_error_from_exception

_app_exception_handlers_registered = False


def _register_exception_handlers() -> None:
    global _app_exception_handlers_registered

    ui.on_exception(show_error_from_exception)

    if _app_exception_handlers_registered:
        return

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s %(name)s: %(message)s',
    )
    app.on_exception(lambda exc: logging.exception('Unhandled app error: %s', exc))
    _app_exception_handlers_registered = True


@contextmanager
def app_shell(title: str, version: str, import_callback):
    """Top-level page shell: theme, header, left drawer, and main content area."""
    _register_exception_handlers()

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

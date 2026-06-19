"""Centralized user-facing messages via modal dialogs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum

from nicegui import ui
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from layout import DIALOG, FORM

logger = logging.getLogger(__name__)

ERROR_MODE = 'simple'

DUPLICATE_NAME_MSG = 'Запись с таким наименованием уже существует'

_LEVEL_META: dict['MessageLevel', dict[str, str]] = {}


class MessageLevel(str, Enum):
    ERROR = 'error'
    WARNING = 'warning'
    SUCCESS = 'success'
    INFO = 'info'


_LEVEL_META.update({
    MessageLevel.ERROR: {
        'title': 'Ошибка',
        'icon': 'error',
        'color': 'negative',
    },
    MessageLevel.WARNING: {
        'title': 'Предупреждение',
        'icon': 'warning',
        'color': 'warning',
    },
    MessageLevel.SUCCESS: {
        'title': 'Готово',
        'icon': 'check_circle',
        'color': 'positive',
    },
    MessageLevel.INFO: {
        'title': 'Сообщение',
        'icon': 'info',
        'color': 'info',
    },
})


def user_message_from_exception(
    exc: Exception,
    *,
    context: dict | None = None,
) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, IntegrityError):
        return _integrity_message(exc)
    if isinstance(exc, ConnectionError):
        return 'Не удалось подключиться к базе Access'
    if isinstance(exc, SQLAlchemyError):
        if ERROR_MODE == 'verbose':
            return f'Ошибка базы данных ({type(exc).__name__}): {exc} | данные: {context}'
        return 'Ошибка базы данных'
    if ERROR_MODE == 'verbose':
        return f'Непредвиденная ошибка ({type(exc).__name__}): {exc} | данные: {context}'
    return 'Произошла непредвиденная ошибка'


def _integrity_message(exc: IntegrityError) -> str:
    raw = str(exc.orig) if exc.orig else str(exc)
    raw_lower = raw.lower()
    if 'number_in_db' in raw_lower:
        simple = 'Объект с таким номером в БД уже существует'
    elif 'inv_number' in raw_lower:
        simple = 'Объект с таким инвентарным номером уже существует'
    elif 'name' in raw_lower:
        simple = DUPLICATE_NAME_MSG
    else:
        simple = 'Нарушено ограничение уникальности данных'
    if ERROR_MODE == 'verbose':
        return f'{simple}. {type(exc).__name__}: {raw}'
    return simple


def show_message(
    message: str,
    *,
    level: MessageLevel = MessageLevel.ERROR,
    title: str | None = None,
    details: str | None = None,
) -> None:
    meta = _LEVEL_META[level]
    dialog_title = title or meta['title']

    with ui.dialog() as dialog, ui.card().classes(DIALOG):
        with ui.row().classes('items-center gap-2'):
            ui.icon(meta['icon']).props(f'color={meta["color"]} size=md')
            ui.label(dialog_title).classes('text-h6')

        ui.label(message).classes('w-full mt-3 whitespace-pre-wrap')

        if details:
            ui.label(details).classes('w-full mt-2 text-caption text-grey')

        with ui.row().classes(f'{FORM} justify-end mt-4'):
            ui.button('Закрыть', on_click=dialog.close, icon='close')

    dialog.open()


def show_error(
    message: str,
    *,
    title: str | None = None,
    details: str | None = None,
) -> None:
    show_message(message, level=MessageLevel.ERROR, title=title, details=details)


def show_warning(
    message: str,
    *,
    title: str | None = None,
    details: str | None = None,
) -> None:
    show_message(message, level=MessageLevel.WARNING, title=title, details=details)


def show_success(
    message: str,
    *,
    title: str | None = None,
    details: str | None = None,
) -> None:
    show_message(message, level=MessageLevel.SUCCESS, title=title, details=details)


def show_info(
    message: str,
    *,
    title: str | None = None,
    details: str | None = None,
) -> None:
    show_message(message, level=MessageLevel.INFO, title=title, details=details)


def show_error_from_exception(
    exc: Exception,
    *,
    context: dict | None = None,
    title: str | None = None,
) -> None:
    logger.exception('Operation failed')
    message = user_message_from_exception(exc, context=context)
    details = None
    if ERROR_MODE == 'verbose' and not isinstance(exc, (ValueError, IntegrityError)):
        details = f'{type(exc).__name__}: {exc}'
    show_error(message, title=title, details=details)


def run_db_action(
    action: Callable[[], None],
    *,
    on_success: Callable[[], None] | None = None,
    success_message: str = 'Сохранено',
) -> bool:
    try:
        action()
    except Exception as exc:
        show_error_from_exception(exc)
        return False

    show_success(success_message)
    if on_success:
        on_success()
    return True


def guard_action(action: Callable[[], None]) -> bool:
    """Run action; show error dialog and return False on failure."""
    try:
        action()
    except Exception as exc:
        show_error_from_exception(exc)
        return False
    return True

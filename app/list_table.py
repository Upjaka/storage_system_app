"""Empty-state messages and count labels for filtered data tables."""

from __future__ import annotations


def table_empty_message(
    *,
    filters_active: bool,
    total: int,
    filter_hint: str | None = None,
) -> str:
    if filters_active:
        if filter_hint:
            return filter_hint
        return (
            'По заданным условиям фильтрации ничего не найдено. '
            'Измените параметры поиска или очистите фильтры.'
        )
    if total == 0:
        return 'Список пуст — добавьте первую запись через кнопку «Добавить».'
    return 'Нет записей для отображения.'


def list_count_label(
    *,
    shown: int,
    total: int,
    unit: str,
    filters_active: bool,
) -> str:
    if filters_active:
        return f'Найдено: {shown} из {total} ({unit})'
    return f'{unit}: {total}'


def _escape_prop(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def apply_table_state(
    table,
    rows: list,
    count_label,
    *,
    shown: int,
    total: int,
    unit: str,
    filters_active: bool,
    filter_hint: str | None = None,
) -> None:
    table.rows = rows
    message = table_empty_message(
        filters_active=filters_active,
        total=total,
        filter_hint=filter_hint,
    )
    table.props(f'no-data-label="{_escape_prop(message)}"')
    count_label.set_text(list_count_label(
        shown=shown,
        total=total,
        unit=unit,
        filters_active=filters_active,
    ))


def search_filter_hint(needle: str, *, scope: str, total: int) -> str | None:
    if not needle.strip():
        return None
    return (
        f'По запросу «{needle.strip()}» в {scope} ничего не найдено. '
        f'Всего записей в справочнике: {total}.'
    )


def object_journal_filter_hint(*, object_label: str, journal: str) -> str:
    return f'Для объекта «{object_label}» записей в {journal} не найдено.'


def object_filters_hint(active: dict[str, str], labels: dict[str, str]) -> str | None:
    if not active:
        return None
    parts = [f'{labels.get(key, key)} — «{value}»' for key, value in active.items()]
    return (
        'По заданным фильтрам объекты не найдены: '
        + '; '.join(parts)
        + '. Сбросьте или измените условия поиска.'
    )

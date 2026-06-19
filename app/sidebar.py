from contextlib import contextmanager
from dataclasses import dataclass

from nicegui import ui


@dataclass(frozen=True)
class NavItem:
    label: str
    path: str
    icon: str


OBJECTS_NAV = (
    NavItem('Список объектов', '/', 'list'),
    NavItem('Журнал ТО', '/maintenance', 'event_note'),
    NavItem('Допработы', '/extra-works', 'receipt_long'),
)

REFERENCES_NAV = (
    NavItem('Регионы', '/references/regions', 'map'),
    NavItem('Ответственные', '/references/responsibles', 'person'),
    NavItem('Единицы измерения', '/references/units', 'straighten'),
    NavItem('Материалы', '/references/materials', 'inventory_2'),
    NavItem('Виды работ', '/references/work-types', 'construction'),
    NavItem('Стоимость ТО', '/references/maintenance-prices', 'payments'),
)


def _normalize_path(path: str) -> str:
    path = path.split('?')[0].split('#')[0]
    if not path or path == '/':
        return '/'
    return path.rstrip('/')


def _is_active(item_path: str, current_path: str) -> bool:
    if item_path == '/':
        return current_path == '/'
    return current_path == item_path or current_path.startswith(item_path + '/')


def _nav_item(item: NavItem, link_refs: dict[str, tuple]) -> None:
    link = ui.link(target=item.path).classes('w-full no-underline text-inherit')
    with link:
        with ui.row().classes('sidebar-row w-full items-center gap-3 py-2 px-3 rounded-full'):
            icon = ui.icon(item.icon).classes('text-muted')
            ui.label(item.label).classes('sidebar-label expanded text-sm')
    link_refs[item.path] = (link, icon)


def _update_active(path: str, link_refs: dict[str, tuple]) -> None:
    current = _normalize_path(path)
    for item_path, (link, icon) in link_refs.items():
        active = _is_active(item_path, current)
        if active:
            link.classes(add='nav-link-active')
            icon.classes(add='nav-icon-active')
        else:
            link.classes(remove='nav-link-active')
            icon.classes(remove='nav-icon-active')


@contextmanager
def drawer():
    """Left navigation drawer with grouped links and active-route highlighting."""
    link_refs: dict[str, tuple] = {}

    with ui.left_drawer(value=True).props('width=240 bordered show-if-above').classes('px-2 py-4') as left_drawer:
        with ui.column().classes('w-full gap-1'):
            ui.label('Объекты').classes('label-text px-3 pt-2 pb-1')
            for item in OBJECTS_NAV:
                _nav_item(item, link_refs)

            ui.label('Справочники').classes('label-text px-3 pt-4 pb-1')
            for item in REFERENCES_NAV:
                _nav_item(item, link_refs)

    router = ui.context.client.sub_pages_router
    router.on_path_changed(lambda path: _update_active(path, link_refs))
    _update_active(router.current_path, link_refs)

    yield left_drawer

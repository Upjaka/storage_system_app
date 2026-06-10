"""Application entry point — page routing, shared layout decorator and run targets."""

import json
from functools import wraps
from nicegui import app, ui
import header
from layout import PAGE
from components.objects_list import content as objects_list_content
from components.import_dialog import show_import_dialog

# ── Config ────────────────────────────────────────────────────────────────
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

appName    = config["appName"]
appVersion = config["appVersion"]
appPort    = config["appPort"]

_list_refresh = lambda: None

# ── Base layout decorator — applies theme and header shell ───────────────
def with_base_layout(route_handler):
    @wraps(route_handler)
    def wrapper(*args, **kwargs):
        ui.colors(primary='#18181b', secondary='#f4f4f5',
                  positive='#4caf50', negative='#ef4444',
                  warning='#f59e0b', info='#3b82f6', accent='#e4e4e7')
        with header.frame(
            title=appName,
            version=appVersion,
            import_callback=lambda: show_import_dialog(on_changed=_list_refresh),
        ):
            with ui.column().classes('w-full flex-grow px-4 py-4').style('min-height: 0'):
                with ui.column().classes(f'{PAGE} gap-4 min-h-0'):
                    return route_handler(*args, **kwargs)
    return wrapper

# ── Page and sub‑page routing ────────────────────────────────────────────
@ui.page('/')
@with_base_layout
def root():
    ui.sub_pages({
        '/': index,
        '/object/{object_id}': object_detail_page,   # опционально
    })

def index():
    def register_refresh(refresh):
        global _list_refresh
        _list_refresh = refresh

    objects_list_content(on_changed=register_refresh)

def object_detail_page(object_id: int):
    from components.object_detail import content as object_detail_content
    object_detail_content(object_id)

# ── Entry point ──────────────────────────────────────────────────────────
ui.run(root, storage_secret="myStorageSecret",
       title=appName, port=appPort, favicon='ico.ico', reconnect_timeout=20)

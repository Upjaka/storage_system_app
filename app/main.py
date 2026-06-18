"""Application entry point — page routing, shared layout decorator and run targets."""

import json
from functools import wraps

from nicegui import app, ui

import shell
from components.import_dialog import show_import_dialog
from components.objects_list import content as objects_list_content
from components.regions_list import content as regions_list_content
from components.responsibles_list import content as responsibles_list_content

# ── Static assets and global styles ───────────────────────────────────────
app.add_static_files('/assets', 'assets')
ui.add_head_html(
    '<link rel="stylesheet" href="/assets/css/global-css.css">'
    '<link rel="stylesheet" href="/assets/css/icons.css">',
    shared=True,
)

# ── Config ────────────────────────────────────────────────────────────────
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

appName    = config["appName"]
appVersion = config["appVersion"]
appPort    = config["appPort"]

_list_refresh = lambda: None

# ── Base layout decorator — applies theme and app shell ───────────────────
def with_base_layout(route_handler):
    @wraps(route_handler)
    def wrapper(*args, **kwargs):
        with shell.app_shell(
            title=appName,
            version=appVersion,
            import_callback=lambda: show_import_dialog(on_changed=_list_refresh),
        ):
            return route_handler(*args, **kwargs)
    return wrapper

# ── Page and sub‑page routing ────────────────────────────────────────────
@ui.page('/')
@with_base_layout
def root():
    ui.sub_pages({
        '/': index,
        '/references/regions': regions_page,
        '/references/responsibles': responsibles_page,
    })

def index():
    def register_refresh(refresh):
        global _list_refresh
        _list_refresh = refresh

    objects_list_content(on_changed=register_refresh)

def regions_page():
    regions_list_content()

def responsibles_page():
    responsibles_list_content()

# ── Entry point ──────────────────────────────────────────────────────────
ui.run(root, storage_secret="myStorageSecret",
       title=appName, port=appPort, favicon='dashboard.ico', reconnect_timeout=20)

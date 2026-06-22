"""Application entry point — page routing, shared layout decorator and run targets."""

import json
import sys
from functools import wraps

from nicegui import app, ui

import shell
from paths import resource_dir
from components.import_dialog import show_import_dialog
from components.objects_list import content as objects_list_content
from components.regions_list import content as regions_list_content
from components.responsibles_list import content as responsibles_list_content
from components.units_list import content as units_list_content
from components.materials_list import content as materials_list_content
from components.work_types_list import content as work_types_list_content
from components.maintenance_prices_list import content as maintenance_prices_list_content
from components.maintenance_list import content as maintenance_list_content
from components.extra_works_list import content as extra_works_list_content
from components.print_component import register_print_route


_APP_DIR = resource_dir()

# ── Static assets and global styles ───────────────────────────────────────
app.add_static_files('/assets', str(_APP_DIR / 'assets'))
ui.add_head_html(
    '<link rel="stylesheet" href="/assets/css/global-css.css">'
    '<link rel="stylesheet" href="/assets/css/icons.css">',
    shared=True,
)

# ── Config ────────────────────────────────────────────────────────────────
with open(_APP_DIR / 'config.json', encoding='utf-8') as f:
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
        '/references/units': units_page,
        '/references/materials': materials_page,
        '/references/work-types': work_types_page,
        '/references/maintenance-prices': maintenance_prices_page,
        '/maintenance': maintenance_page,
        '/extra-works': extra_works_page,
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

def units_page():
    units_list_content()

def materials_page():
    materials_list_content()

def work_types_page():
    work_types_list_content()

def maintenance_prices_page():
    maintenance_prices_list_content()

def maintenance_page():
    maintenance_list_content()

def extra_works_page():
    extra_works_list_content()

# ── Entry point ──────────────────────────────────────────────────────────
if __name__ in {'__main__', '__mp_main__'}:
    from multiprocessing import freeze_support

    freeze_support()
    register_print_route()
    ui.run(
        root,
        storage_secret="myStorageSecret",
        title=appName,
        port=appPort,
        favicon=str(_APP_DIR / 'dashboard.ico'),
        reconnect_timeout=20,
        reload=not getattr(sys, 'frozen', False),
        native=getattr(sys, 'frozen', False),
    )

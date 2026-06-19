from __future__ import annotations

import base64
import html
import json
from typing import Any

from nicegui import ui

from messages import show_error_from_exception
from services.report_service import PrintPage

_PRINT_CSS = """
@page { margin: 1.5cm; }
@media print {
  .no-print { display: none !important; }
  body { margin: 0; }
}
body {
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  color: #111;
  margin: 0;
  padding: 1.5rem;
  line-height: 1.4;
}
.print-wrap { max-width: 52rem; margin: 0 auto; }
h1 { font-size: 1.35rem; margin: 0 0 0.25rem; }
.subtitle { color: #555; margin: 0 0 1.25rem; font-size: 0.95rem; }
section { margin-bottom: 1.25rem; }
section h2 {
  font-size: 0.95rem;
  margin: 0 0 0.5rem;
  border-bottom: 1px solid #ccc;
  padding-bottom: 0.2rem;
}
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { border: 1px solid #ddd; padding: 0.35rem 0.5rem; text-align: left; vertical-align: top; }
th { background: #f5f5f5; font-weight: 600; }
.kv-table td:first-child { width: 34%; font-weight: 500; background: #fafafa; }
.group-row td { background: #f0f0f0; font-weight: 600; }
.text-block { white-space: pre-wrap; }
"""


def _encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def _decode_token(token: str) -> dict[str, Any]:
    padding = '=' * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + padding)
    return json.loads(raw.decode('utf-8'))


def encode_html(html_content: str) -> str:
    return _encode_payload({'type': 'html', 'html': html_content})


def encode_page(title: str, subtitle: str, sections: list[dict[str, Any]]) -> str:
    return _encode_payload({
        'type': 'page',
        'title': title,
        'subtitle': subtitle,
        'sections': sections,
    })


def open_print(token: str) -> None:
    ui.navigate.to(f'/print/{token}', new_tab=True)


def launch_print_page(page: PrintPage) -> None:
    open_print(encode_page(page.title, page.subtitle, page.sections))


def _render_section(section: dict[str, Any]) -> str:
    title = section.get('title')
    kind = section.get('kind', 'kv')
    parts: list[str] = []
    if title:
        parts.append(f'<section><h2>{html.escape(title)}</h2>')

    if kind == 'text':
        content = html.escape(str(section.get('content', '')))
        parts.append(f'<div class="text-block">{content}</div>')
    elif kind == 'table':
        headers = section.get('headers', [])
        rows = section.get('rows', [])
        parts.append('<table><thead><tr>')
        for header in headers:
            parts.append(f'<th>{html.escape(str(header))}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            is_group = len(row) == 2 and row[1] == ''
            row_class = ' class="group-row"' if is_group else ''
            parts.append(f'<tr{row_class}>')
            for cell in row:
                parts.append(f'<td>{html.escape(str(cell))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
    else:
        rows = section.get('rows', [])
        parts.append('<table class="kv-table"><tbody>')
        for label, value in rows:
            parts.append(
                f'<tr><td>{html.escape(str(label))}</td>'
                f'<td>{html.escape(str(value))}</td></tr>'
            )
        parts.append('</tbody></table>')

    if title:
        parts.append('</section>')
    return ''.join(parts)


def _render_page_html(payload: dict[str, Any]) -> str:
    title = html.escape(payload.get('title', ''))
    subtitle = html.escape(payload.get('subtitle', ''))
    sections_html = ''.join(_render_section(section) for section in payload.get('sections', []))
    return (
        f'<div class="print-wrap">'
        f'<h1>{title}</h1>'
        f'<p class="subtitle">{subtitle}</p>'
        f'{sections_html}'
        f'</div>'
    )


def _render_print_error(message: str) -> None:
    ui.add_head_html(f'<style>{_PRINT_CSS}</style>')
    with ui.column().classes('w-full gap-2'):
        ui.label('Ошибка печати').classes('text-h5 text-negative')
        ui.label(message).classes('text-body1')


def register_print_route() -> None:
    @ui.page('/print/{token}')
    def print_view(token: str) -> None:
        ui.on_exception(show_error_from_exception)

        try:
            payload = _decode_token(token)
        except Exception:
            _render_print_error(
                'Не удалось открыть документ для печати. Ссылка повреждена или устарела.',
            )
            return

        ui.add_head_html(f'<style>{_PRINT_CSS}</style>')

        with ui.column().classes('w-full'):
            ui.button(
                'Печать',
                on_click=lambda: ui.run_javascript('window.print()'),
                icon='print',
            ).classes('no-print mb-4')

            try:
                if payload.get('type') == 'html':
                    ui.html(payload.get('html', ''), sanitize=False)
                else:
                    ui.html(_render_page_html(payload), sanitize=False)
            except Exception as exc:
                show_error_from_exception(exc)

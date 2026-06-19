from __future__ import annotations

from difflib import get_close_matches

from models.object_model import SYSTEM_CODES

SYSTEM_TYPE_COLUMNS = SYSTEM_CODES

OWNERSHIP_ALIASES = {
    'н\\д': 'н/д',
    'н/д': 'н/д',
}


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    text = str(value).strip()
    return not text or text.lower() == 'nan'


def normalize_ownership(value: str | None, valid_values: set[str] | None = None) -> str | None:
    if is_blank(value):
        return None
    text = str(value).strip()
    if text in OWNERSHIP_ALIASES:
        text = OWNERSHIP_ALIASES[text]
    if valid_values and text not in valid_values:
        alias = OWNERSHIP_ALIASES.get(text, text)
        if alias in valid_values:
            return alias
    return text


def normalize_region_name(
    raw: str | None,
    canonical_names: list[str],
    *,
    cutoff: float = 0.8,
) -> tuple[str | None, bool]:
    """Return (resolved name, matched canonical справочник entry)."""
    if is_blank(raw):
        return None, True

    text = str(raw).strip()
    if text in canonical_names:
        return text, True

    by_lower = {name.lower(): name for name in canonical_names}
    canonical = by_lower.get(text.lower())
    if canonical is not None:
        return canonical, True

    matches = get_close_matches(text, canonical_names, n=1, cutoff=cutoff)
    if matches:
        return matches[0], True

    return text, False


def system_codes_from_type_row(row) -> list[str]:
    codes: list[str] = []
    for code in SYSTEM_TYPE_COLUMNS:
        if code not in row.index:
            continue
        value = row[code]
        if _is_truthy_bit(value):
            codes.append(code)
    return sorted(codes, key=SYSTEM_CODES.index)


def _is_truthy_bit(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value:
            return False
        return int(value) != 0
    text = str(value).strip().lower()
    return text in {'1', 'true', 'yes', '-1'}

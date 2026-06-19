from __future__ import annotations

import math

import pandas as pd
from sqlalchemy.orm import Session

from models.composition_fields import (
    COMPOSITION_FIELDS,
    FLOAT_COMPOSITION_FIELDS,
)
from models.object_model import ObjectComposition


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _normalize_count_value(field: str, value) -> int | float:
    if _is_blank(value):
        return 0.0 if field in FLOAT_COMPOSITION_FIELDS else 0
    if field in FLOAT_COMPOSITION_FIELDS:
        return float(value)
    return int(value)


def counts_from_access_row(row) -> dict[str, int | float]:
    counts: dict[str, int | float] = {}
    for field in COMPOSITION_FIELDS:
        if field not in row.index:
            continue
        counts[field] = _normalize_count_value(field, row[field])
    return counts


def get_composition_counts(db: Session, object_id: int) -> dict[str, int | float]:
    composition = (
        db.query(ObjectComposition)
        .filter(ObjectComposition.object_id == object_id)
        .first()
    )
    if composition is None or not composition.counts:
        return {field: (0.0 if field in FLOAT_COMPOSITION_FIELDS else 0) for field in COMPOSITION_FIELDS}
    return {
        field: _normalize_count_value(field, composition.counts.get(field))
        for field in COMPOSITION_FIELDS
    }


def upsert_composition(db: Session, object_id: int, counts: dict) -> ObjectComposition:
    normalized = {
        field: _normalize_count_value(field, counts.get(field))
        for field in COMPOSITION_FIELDS
    }
    composition = (
        db.query(ObjectComposition)
        .filter(ObjectComposition.object_id == object_id)
        .first()
    )
    if composition is None:
        composition = ObjectComposition(object_id=object_id, counts=normalized)
        db.add(composition)
    else:
        composition.counts = normalized
    db.flush()
    return composition

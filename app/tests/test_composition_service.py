import pandas as pd
import pytest

from models.object_model import ObjectComposition
from services.composition_service import (
    counts_from_access_row,
    get_composition_counts,
    upsert_composition,
)
from services.object_service import create_object
from conftest import object_payload


def test_counts_from_access_row_normalizes_integers_and_floats():
    row = pd.Series({
        'АПС_Прибор управления': 3,
        'АПС_Извещатель пожарный': None,
        'Поле34': 1.5,
        'Поле35': None,
    })

    counts = counts_from_access_row(row)

    assert counts['АПС_Прибор управления'] == 3
    assert counts['АПС_Извещатель пожарный'] == 0
    assert counts['Поле34'] == 1.5
    assert counts['Поле35'] == 0.0


def test_upsert_composition_creates_and_updates(db):
    obj = create_object(db, object_payload(inv_number='INV-COMP'))
    upsert_composition(db, obj.id, {'АПС_Прибор управления': 2, 'Поле34': 1.25})
    db.commit()

    counts = get_composition_counts(db, obj.id)
    assert counts['АПС_Прибор управления'] == 2
    assert counts['Поле34'] == 1.25

    upsert_composition(db, obj.id, {'АПС_Прибор управления': 5})
    db.commit()

    counts = get_composition_counts(db, obj.id)
    assert counts['АПС_Прибор управления'] == 5
    assert db.query(ObjectComposition).filter_by(object_id=obj.id).count() == 1


def test_get_composition_counts_returns_zeros_when_missing(db):
    obj = create_object(db, object_payload(inv_number='INV-EMPTY'))

    counts = get_composition_counts(db, obj.id)

    assert counts['АПС_Прибор управления'] == 0
    assert counts['Поле34'] == 0.0

import pytest

from services.import_normalization import (
    normalize_ownership,
    normalize_region_name,
    system_codes_from_type_row,
)


def test_normalize_region_name_exact_match():
    canonical = ['г. Сургут', 'Сургутский район']
    name, matched = normalize_region_name('г. Сургут', canonical)
    assert name == 'г. Сургут'
    assert matched is True


def test_normalize_region_name_case_insensitive():
    canonical = ['г. Сургут']
    name, matched = normalize_region_name('Г. СУРГУТ', canonical)
    assert name == 'г. Сургут'
    assert matched is True


def test_normalize_region_name_fuzzy_match():
    canonical = ['Сургутский район']
    name, matched = normalize_region_name('Сургутский р-н', canonical, cutoff=0.6)
    assert name == 'Сургутский район'
    assert matched is True


def test_normalize_region_name_unmatched_returns_raw():
    canonical = ['г. Сургут']
    name, matched = normalize_region_name('Неизвестный регион XYZ', canonical)
    assert name == 'Неизвестный регион XYZ'
    assert matched is False


def test_normalize_ownership_alias():
    assert normalize_ownership('н\\д') == 'н/д'
    assert normalize_ownership('Собственность', {'Собственность', 'Аренда'}) == 'Собственность'


def test_system_codes_from_type_row_reads_bits():
    import pandas as pd

    row = pd.Series({'АПС': True, 'СОУЭ': False, 'ВПВ': 1, 'АУГПТ': 0})
    assert system_codes_from_type_row(row) == ['АПС', 'ВПВ']


def test_system_codes_from_type_row_empty():
    import pandas as pd

    row = pd.Series({'АПС': False, 'СОУЭ': False, 'ВПВ': False, 'АУГПТ': False})
    assert system_codes_from_type_row(row) == []

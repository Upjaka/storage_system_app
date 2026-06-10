from services.object_validation import validate_create_data
from conftest import object_payload


def test_validate_create_data_accepts_valid_payload():
    assert validate_create_data(object_payload()) is None


def test_validate_create_data_rejects_missing_required_fields():
    payload = object_payload(number_in_db=None, inv_number='', address='  ')

    error = validate_create_data(payload)

    assert error is not None
    assert 'Заполните обязательные поля' in error
    assert 'Номер в БД' in error
    assert 'Инвентарный номер' in error
    assert 'Адрес' in error


def test_validate_create_data_verbose_mode_includes_field_keys():
    payload = object_payload(inv_number='')

    error = validate_create_data(payload, error_mode='verbose')

    assert error is not None
    assert 'inv_number' in error

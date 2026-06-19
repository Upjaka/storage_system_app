from sqlalchemy.exc import IntegrityError

import messages


def _integrity_error(message: str) -> IntegrityError:
    return IntegrityError('INSERT', {}, Exception(message))


def test_user_message_from_exception_value_error():
    assert messages.user_message_from_exception(ValueError('Пустое имя')) == 'Пустое имя'


def test_user_message_from_exception_number_in_db():
    exc = _integrity_error('UNIQUE constraint failed: objects.number_in_db')

    assert messages.user_message_from_exception(exc) == 'Объект с таким номером в БД уже существует'


def test_user_message_from_exception_inv_number():
    exc = _integrity_error('UNIQUE constraint failed: objects.inv_number')

    assert messages.user_message_from_exception(exc) == 'Объект с таким инвентарным номером уже существует'


def test_user_message_from_exception_duplicate_name():
    exc = _integrity_error('UNIQUE constraint failed: regions.name')

    assert messages.user_message_from_exception(exc) == messages.DUPLICATE_NAME_MSG


def test_user_message_from_exception_generic_integrity():
    exc = _integrity_error('UNIQUE constraint failed: some_table.some_col')

    assert messages.user_message_from_exception(exc) == 'Нарушено ограничение уникальности данных'


def test_user_message_from_exception_connection_error():
    assert messages.user_message_from_exception(ConnectionError('odbc failed')) == (
        'Не удалось подключиться к базе Access'
    )


def test_user_message_from_exception_unknown():
    assert messages.user_message_from_exception(RuntimeError('boom')) == 'Произошла непредвиденная ошибка'


def test_guard_action_returns_false_on_error(monkeypatch):
    errors: list[Exception] = []
    monkeypatch.setattr(messages, 'show_error_from_exception', lambda exc, **kwargs: errors.append(exc))

    assert messages.guard_action(lambda: (_ for _ in ()).throw(RuntimeError('fail'))) is False
    assert len(errors) == 1


def test_guard_action_returns_true_on_success(monkeypatch):
    errors: list[Exception] = []
    monkeypatch.setattr(messages, 'show_error_from_exception', lambda exc, **kwargs: errors.append(exc))

    assert messages.guard_action(lambda: None) is True
    assert errors == []


def test_user_message_from_exception_verbose_mode(monkeypatch):
    monkeypatch.setattr(messages, 'ERROR_MODE', 'verbose')

    message = messages.user_message_from_exception(RuntimeError('boom'), context={'id': 1})

    assert 'RuntimeError' in message
    assert 'boom' in message
    assert "'id': 1" in message

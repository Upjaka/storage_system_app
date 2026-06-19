from list_table import (
    list_count_label,
    object_filters_hint,
    search_filter_hint,
    table_empty_message,
)


def test_table_empty_message_with_filters():
    message = table_empty_message(filters_active=True, total=10)
    assert 'фильтрации' in message


def test_table_empty_message_with_filter_hint():
    message = table_empty_message(
        filters_active=True,
        total=10,
        filter_hint='По запросу «тест» ничего не найдено.',
    )
    assert message == 'По запросу «тест» ничего не найдено.'


def test_table_empty_message_empty_list():
    message = table_empty_message(filters_active=False, total=0)
    assert 'Список пуст' in message


def test_list_count_label_filtered():
    assert list_count_label(
        shown=2,
        total=10,
        unit='объектов',
        filters_active=True,
    ) == 'Найдено: 2 из 10 (объектов)'


def test_search_filter_hint_includes_query_and_total():
    hint = search_filter_hint('москва', scope='регионах', total=5)
    assert '«москва»' in hint
    assert '5' in hint


def test_object_filters_hint_lists_active_filters():
    hint = object_filters_hint(
        {'region': 'Москва'},
        {'region': 'Регион'},
    )
    assert 'Регион — «Москва»' in hint

import pytest

from components.print_component import _decode_token, encode_page


def test_decode_token_roundtrip():
    token = encode_page('Title', 'Subtitle', [{'title': 'Section', 'rows': [('A', '1')]}])
    payload = _decode_token(token)

    assert payload['title'] == 'Title'
    assert payload['subtitle'] == 'Subtitle'


@pytest.mark.parametrize('token', ['', 'not-a-valid-token', '!!!'])
def test_decode_token_rejects_invalid_input(token: str):
    with pytest.raises(Exception):
        _decode_token(token)

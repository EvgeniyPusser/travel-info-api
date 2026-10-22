import pytest
from pydantic import ValidationError

from models.travel_model import TravelInfoRequest, TravelInfoResponse

@pytest.fixture
def request_data():
    return {
        'country_from': 'France',
        'country_to': 'Israel',
        'is_capital': True,
        'is_weather': False,
        'is_currency': True,
    }


def test_travel_info_request_valid_data(request_data):
    request = TravelInfoRequest(**request_data)
    assert request.model_dump() == request_data


@pytest.mark.parametrize('field_name', [
    'country_from', 'country_to', 'is_capital', 'is_weather', 'is_currency',
])
def test_travel_info_request_requires_all_fields(request_data, field_name):
    del request_data[field_name]
    with pytest.raises(ValidationError) as error:
        TravelInfoRequest(**request_data)
    assert error.value.errors()[0]['loc'] == (field_name,)
    assert error.value.errors()[0]['type'] == 'missing'


@pytest.mark.parametrize('field_name', ['country_from', 'country_to'])
@pytest.mark.parametrize('invalid_value', [None, 123, []])
def test_travel_info_request_rejects_invalid_countries(request_data, field_name, invalid_value):
    request_data[field_name] = invalid_value
    with pytest.raises(ValidationError):
        TravelInfoRequest(**request_data)


@pytest.mark.parametrize('field_name', ['is_capital', 'is_weather', 'is_currency'])
@pytest.mark.parametrize('flag', [True, False])
def test_travel_info_request_accepts_boolean_flags(request_data, field_name, flag):
    request_data[field_name] = flag
    request = TravelInfoRequest(**request_data)
    assert getattr(request, field_name) is flag


@pytest.mark.parametrize('field_name', ['is_capital', 'is_weather', 'is_currency'])
@pytest.mark.parametrize('invalid_value', [None, 'maybe', 2])
def test_travel_info_request_rejects_invalid_flags(request_data, field_name, invalid_value):
    request_data[field_name] = invalid_value
    with pytest.raises(ValidationError):
        TravelInfoRequest(**request_data)


def test_travel_info_response_optional_fields_default_to_none():
    response = TravelInfoResponse(country_from='France', country_to='Israel')
    assert response.model_dump() == {
        'country_from': 'France',
        'country_to': 'Israel',
        'capital_to': None,
        'weather': None,
        'currency_code_from': None,
        'currency_code_to': None,
        'currency_name_from': None,
        'currency_name_to': None,
        'exchange_rate': None,
    }


def test_travel_info_response_valid_data():
    response_data = {
        'country_from': 'France',
        'country_to': 'Israel',
        'capital_to': 'Jerusalem',
        'weather': 'Sunny, 25 °C',
        'currency_code_from': 'EUR',
        'currency_code_to': 'ILS',
        'currency_name_from': 'Euro',
        'currency_name_to': 'Israeli new shekel',
        'exchange_rate': 3.9,
    }
    response = TravelInfoResponse(**response_data)
    assert response.model_dump() == response_data


@pytest.mark.parametrize('field_name', ['country_from', 'country_to'])
def test_travel_info_response_requires_countries(field_name):
    response_data = {'country_from': 'France', 'country_to': 'Israel'}
    del response_data[field_name]
    with pytest.raises(ValidationError) as error:
        TravelInfoResponse(**response_data)
    assert error.value.errors()[0]['loc'] == (field_name,)
    assert error.value.errors()[0]['type'] == 'missing'


@pytest.mark.parametrize('field_name', ['country_from', 'country_to'])
@pytest.mark.parametrize('invalid_value', [None, 123, []])
def test_travel_info_response_rejects_invalid_countries(field_name, invalid_value):
    response_data = {'country_from': 'France', 'country_to': 'Israel'}
    response_data[field_name] = invalid_value
    with pytest.raises(ValidationError):
        TravelInfoResponse(**response_data)


@pytest.mark.parametrize('field_name', [
    'capital_to', 'weather', 'currency_code_from', 'currency_code_to',
    'currency_name_from', 'currency_name_to', 'exchange_rate',
])
def test_travel_info_response_accepts_explicit_none(field_name):
    response = TravelInfoResponse(
        country_from='France', country_to='Israel', **{field_name: None},
    )
    assert getattr(response, field_name) is None


@pytest.mark.parametrize('field_name', [
    'capital_to', 'weather', 'currency_code_from', 'currency_code_to',
    'currency_name_from', 'currency_name_to',
])
def test_travel_info_response_rejects_invalid_text_fields(field_name):
    with pytest.raises(ValidationError):
        TravelInfoResponse(country_from='France', country_to='Israel', **{field_name: 123})


@pytest.mark.parametrize('field_name', ['currency_code_from', 'currency_code_to'])
@pytest.mark.parametrize('code', ['', 'US', 'EURO'])
def test_travel_info_response_currency_codes_require_three_characters(field_name, code):
    with pytest.raises(ValidationError) as error:
        TravelInfoResponse(country_from='France', country_to='Israel', **{field_name: code})
    assert error.value.errors()[0]['loc'] == (field_name,)


@pytest.mark.parametrize('field_name', ['currency_code_from', 'currency_code_to'])
@pytest.mark.parametrize('code', ['EUR', 'ILS', 'USD'])
def test_travel_info_response_accepts_three_character_currency_codes(field_name, code):
    response = TravelInfoResponse(country_from='France', country_to='Israel', **{field_name: code})
    assert getattr(response, field_name) == code


@pytest.mark.parametrize('rate', [1, 3.9])
def test_travel_info_response_accepts_numeric_exchange_rate(rate):
    response = TravelInfoResponse(country_from='France', country_to='Israel', exchange_rate=rate)
    assert response.exchange_rate == rate


@pytest.mark.parametrize('invalid_value', ['unknown', [], {}])
def test_travel_info_response_rejects_invalid_exchange_rate(invalid_value):
    with pytest.raises(ValidationError):
        TravelInfoResponse(country_from='France', country_to='Israel', exchange_rate=invalid_value)

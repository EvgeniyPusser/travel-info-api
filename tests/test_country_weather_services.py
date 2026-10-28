import asyncio

import httpx
import pytest
from fastapi import HTTPException

from services import countries, weather


@pytest.fixture
def mock_service(monkeypatch):
    original_client = httpx.AsyncClient

    def configure(service, handler):
        monkeypatch.setattr(service, 'API_KEY', 'test-key')
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            service.httpx, 'AsyncClient',
            lambda **kwargs: original_client(transport=transport, **kwargs),
        )

    return configure


def test_geography_returns_capital_and_currency(mock_service):
    def handler(request):
        assert request.headers['Authorization'] == 'Bearer test-key'
        assert request.url.path == '/countries/v5'
        assert dict(request.url.params) == {'q': 'France', 'limit': '10'}
        return httpx.Response(200, json={'data': {'objects': [{
            'codes': {'alpha_2': 'FR'},
            'capitals': [{'name': 'Paris', 'primary': True}],
            'currencies': [{'code': 'EUR', 'name': 'Euro'}],
        }]}})

    mock_service(countries, handler)
    result = asyncio.run(countries.get_country_info('France'))
    assert result.capital == 'Paris'
    assert result.country_code == 'FR'
    assert result.currency_code == 'EUR'
    assert result.currency_name == 'Euro'


def test_country_search_prefers_exact_match(mock_service):
    records = [
        {'names': {'common': 'French Guiana'}},
        {
            'names': {'common': 'France'},
            'codes': {'alpha_2': 'FR'},
            'capitals': [{'name': 'Paris', 'primary': True}],
            'currencies': [{'code': 'EUR', 'name': 'Euro'}],
        },
    ]
    mock_service(countries, lambda request: httpx.Response(200, json={
        'data': {'objects': records},
    }))
    result = asyncio.run(countries.get_country_info(country_name='France'))
    assert result.capital == 'Paris'


@pytest.mark.parametrize('country_name, records, expected_status', [
    ('France', [], 400),
    ('Congo', [{'names': {'common': 'Congo'}}, {'names': {'common': 'Congo'}}], 422),
])
def test_country_search_handles_empty_and_ambiguous_results(
    mock_service, country_name, records, expected_status,
):
    mock_service(countries, lambda request: httpx.Response(200, json={
        'data': {'objects': records},
    }))
    with pytest.raises(HTTPException) as error:
        asyncio.run(countries.get_country_info(country_name))
    assert error.value.status_code == expected_status


@pytest.mark.parametrize('country_name', ['Frnace', 'French', '  FRANCE  ', 'French Republic'])
def test_country_search_selects_most_similar_name(mock_service, country_name):
    records = [
        {'names': {'common': 'French Guiana'}},
        {
            'names': {'common': 'France', 'official': 'French Republic'},
            'codes': {'alpha_2': 'FR'},
            'capitals': [{'name': 'Paris', 'primary': True}],
            'currencies': [{'code': 'EUR', 'name': 'Euro'}],
        },
    ]
    mock_service(countries, lambda request: httpx.Response(200, json={
        'data': {'objects': records},
    }))
    result = asyncio.run(countries.get_country_info(country_name))
    assert result.country_code == 'FR'
    assert result.capital == 'Paris'


def test_weather_returns_description_and_celsius(mock_service):
    def handler(request):
        assert request.url.params['q'] == 'Paris,FR'
        assert request.url.params['units'] == 'metric'
        assert request.url.params['appid'] == 'test-key'
        return httpx.Response(200, json={
            'weather': [{'description': 'Sunny'}], 'main': {'temp': 25},
        })

    mock_service(weather, handler)
    assert asyncio.run(weather.get_weather_summary('Paris,FR')) == 'Sunny, 25 °C'


@pytest.mark.parametrize('service, function, argument, status_code, payload, expected_status', [
    (weather, weather.get_weather_summary, 'Paris,FR', 404, {}, 404),
    (weather, weather.get_weather_summary, 'Paris,FR', 200, {}, 502),
    (countries, countries.get_country_info, 'France', 404, {}, 404),
    (countries, countries.get_country_info, 'France', 200, {}, 400),
])
def test_services_handle_missing_or_invalid_data(
    mock_service, service, function, argument, status_code, payload, expected_status,
):
    mock_service(service, lambda request: httpx.Response(status_code, json=payload))
    with pytest.raises(HTTPException) as error:
        asyncio.run(function(argument))
    assert error.value.status_code == expected_status


def test_weather_requires_its_own_key(monkeypatch):
    monkeypatch.setattr(weather, 'API_KEY', None)
    with pytest.raises(ValueError, match='WEATHER_API_KEY'):
        asyncio.run(weather.get_weather_summary('Paris,FR'))


def test_geography_requires_its_own_key(monkeypatch):
    monkeypatch.setattr(countries, 'API_KEY', None)
    with pytest.raises(ValueError, match='COUNTRY_API_KEY environment variable is not set'):
        asyncio.run(countries.get_country_info('France'))

import asyncio

import httpx
import pytest
from fastapi import HTTPException

from services import geography, weather


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
        assert request.url.path.endswith('/names.common/France')
        return httpx.Response(200, json={'data': {'objects': [{
            'codes': {'alpha_2': 'FR'},
            'capitals': [{'name': 'Paris', 'primary': True}],
            'currencies': [{'code': 'EUR', 'name': 'Euro'}],
        }]}})

    mock_service(geography, handler)
    result = asyncio.run(geography.get_country_info('France'))
    assert result.capital == 'Paris'
    assert result.country_code == 'FR'
    assert result.currency_code == 'EUR'
    assert result.currency_name == 'Euro'


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


@pytest.mark.parametrize('service, function, argument', [
    (weather, weather.get_weather_summary, 'Paris,FR'),
    (geography, geography.get_country_info, 'France'),
])
@pytest.mark.parametrize('status_code, payload, expected_status', [
    (404, {}, 404),
    (200, {}, 502),
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
    monkeypatch.setattr(geography, 'API_KEY', None)
    with pytest.raises(HTTPException) as error:
        asyncio.run(geography.get_country_info('France'))
    assert error.value.status_code == 500
    assert error.value.detail == 'Country API key not found'

import asyncio
from unittest.mock import AsyncMock

import pytest

from models.travel_model import TravelInfoRequest
from services import travel
from services.countries import CountryInfo


@pytest.mark.parametrize('is_capital', [True, False])
@pytest.mark.parametrize('is_weather', [True, False])
@pytest.mark.parametrize('is_currency', [True, False])
def test_travel_info_calls_only_requested_services(monkeypatch, is_capital, is_weather, is_currency):
    destination = CountryInfo(
        country_code='IL', capital='Jerusalem', currency_code='ILS',
        currency_name='Israeli new shekel',
    )
    origin = CountryInfo(
        country_code='FR', capital='Paris', currency_code='EUR', currency_name='Euro',
    )
    geography_mock = AsyncMock(side_effect=[destination, origin])
    weather_mock = AsyncMock(return_value='Sunny, 25 °C')
    currency_mock = AsyncMock(return_value=3.9)
    monkeypatch.setattr(travel, 'get_country_info', geography_mock)
    monkeypatch.setattr(travel, 'get_weather_summary', weather_mock)
    monkeypatch.setattr(travel, 'get_exchange_rate', currency_mock)

    response = asyncio.run(travel.get_travel_info(TravelInfoRequest(
        country_from='France', country_to='Israel', is_capital=is_capital,
        is_weather=is_weather, is_currency=is_currency,
    )))

    assert response.country_from == 'France'
    assert response.country_to == 'Israel'
    assert response.capital_to == ('Jerusalem' if is_capital else None)
    assert response.weather == ('Sunny, 25 °C' if is_weather else None)
    assert response.exchange_rate == (3.9 if is_currency else None)
    assert response.currency_code_from == ('EUR' if is_currency else None)
    assert response.currency_code_to == ('ILS' if is_currency else None)
    assert response.currency_name_from == ('Euro' if is_currency else None)
    assert response.currency_name_to == ('Israeli new shekel' if is_currency else None)
    assert geography_mock.await_count == (
        1 + int(is_currency) if any((is_capital, is_weather, is_currency)) else 0
    )
    if is_weather:
        weather_mock.assert_awaited_once_with('Jerusalem,IL')
    else:
        weather_mock.assert_not_awaited()
    if is_currency:
        currency_mock.assert_awaited_once_with('EUR', 'ILS')
    else:
        currency_mock.assert_not_awaited()

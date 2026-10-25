import asyncio

import httpx
import pytest
from fastapi import HTTPException

from services import currency


@pytest.fixture
def mock_fixer(monkeypatch):
    monkeypatch.setattr(currency, 'API_KEY', 'test-key')
    original_client = httpx.AsyncClient

    def configure(handler):
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            currency.httpx, 'AsyncClient',
            lambda **kwargs: original_client(transport=transport, **kwargs),
        )

    return configure


def test_get_exchange_rate_converts_between_currencies(mock_fixer):
    def handler(request):
        assert str(request.url).startswith('https://api.apilayer.com/fixer/convert?')
        assert request.headers['apikey'] == 'test-key'
        assert dict(request.url.params) == {'from': 'USD', 'to': 'ILS', 'amount': '1'}
        return httpx.Response(200, json={'success': True, 'result': 4})

    mock_fixer(handler)
    assert asyncio.run(currency.get_exchange_rate('usd', 'ils')) == 4


@pytest.mark.parametrize('payload', [
    {'success': False, 'error': {'code': 101}},
    {'success': True},
    {'success': True, 'result': 0},
    {'success': True, 'result': 'unknown'},
])
def test_get_exchange_rate_rejects_invalid_responses(mock_fixer, payload):
    mock_fixer(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(HTTPException) as error:
        asyncio.run(currency.get_exchange_rate('USD', 'ILS'))
    assert error.value.status_code == 502


def test_get_exchange_rate_handles_network_error(mock_fixer):
    def handler(request):
        raise httpx.ConnectError('Connection failed', request=request)

    mock_fixer(handler)
    with pytest.raises(HTTPException) as error:
        asyncio.run(currency.get_exchange_rate('USD', 'ILS'))
    assert error.value.status_code == 502


def test_get_exchange_rate_handles_http_error(mock_fixer):
    mock_fixer(lambda request: httpx.Response(500))
    with pytest.raises(HTTPException) as error:
        asyncio.run(currency.get_exchange_rate('USD', 'ILS'))
    assert error.value.status_code == 502


def test_get_exchange_rate_requires_api_key(monkeypatch):
    monkeypatch.setattr(currency, 'API_KEY', None)
    with pytest.raises(ValueError, match='FIXER_API_KEY'):
        asyncio.run(currency.get_exchange_rate('USD', 'ILS'))

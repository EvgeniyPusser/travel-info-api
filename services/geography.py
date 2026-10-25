import os
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from loggers.logger_req import logger


COUNTRIES_URL = 'https://api.restcountries.com/countries/v5'
API_KEY = os.environ.get('COUNTRY_API_KEY')


class CountryInfo(BaseModel):
    country_code: str
    capital: str | None = None
    currency_code: str | None = None
    currency_name: str | None = None


async def get_country_info(country: str) -> CountryInfo:
    if not API_KEY:
        raise HTTPException(status_code=500, detail='Country API key not found')

    logger.debug(f'Fetching geography for {country}')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f'{COUNTRIES_URL}/names.common/{quote(country, safe="")}',
                headers={'Authorization': f'Bearer {API_KEY}'},
                params={'response_fields': 'codes.alpha_2,capitals,currencies'},
            )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f'Country {country} not found')
        resp.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail='Geography service unreachable') from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail='Error fetching geography') from exc

    try:
        record = resp.json()['data']['objects'][0]
        capitals = record.get('capitals', [])
        capital = next((item for item in capitals if item.get('primary')), None)
        if capital is None and capitals:
            capital = capitals[0]
        currencies = record.get('currencies', [])
        if len(currencies) > 1:
            raise HTTPException(status_code=422, detail=f'Country {country} has multiple currencies')
        currency = currencies[0] if currencies else None
        return CountryInfo(
            country_code=record['codes']['alpha_2'],
            capital=capital['name'] if capital else None,
            currency_code=currency['code'] if currency else None,
            currency_name=currency['name'] if currency else None,
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail='Invalid geography response') from exc

import os
from dataclasses import dataclass
from difflib import SequenceMatcher

import httpx
from fastapi import HTTPException

from loggers.logger_req import logger


COUNTRIES_URL = 'https://api.restcountries.com/countries/v5'
API_KEY = os.environ.get('COUNTRY_API_KEY')


@dataclass
class CountryInfo:
    capital: str | None
    currency_code: str | None
    currency_name: str | None
    country_code: str = ''


def find_best_country_match(country_name: str, objects: list[dict]) -> dict:
    """Choose the country whose common or official name is most similar."""
    if not objects:
        logger.warning(f'Country {country_name} not found')
        raise HTTPException(status_code=400, detail=f'Country info not found: {country_name}')
    if len(objects) == 1:
        return objects[0]

    query = country_name.strip().casefold()
    best_score = -1.0
    matches = []
    for record in objects:
        names = record.get('names', {})
        score = max(
            SequenceMatcher(None, query, name.strip().casefold()).ratio()
            for name in (names.get('common', ''), names.get('official', ''))
        )
        if score > best_score:
            best_score = score
            matches = [record]
        elif score == best_score:
            matches.append(record)

    if len(matches) != 1:
        raise HTTPException(status_code=422, detail='Country name is ambiguous')
    return matches[0]


async def get_country_info(country_name: str) -> CountryInfo:
    if not API_KEY:
        raise ValueError('COUNTRY_API_KEY environment variable is not set')

    logger.debug(f'Fetching country info for {country_name}')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                COUNTRIES_URL,
                headers={'Authorization': f'Bearer {API_KEY}'},
                params={'q': country_name, 'limit': 10},
            )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f'Country {country_name} not found')
        resp.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f'Country service unreachable: {exc}')
        raise HTTPException(status_code=502, detail='Geography service unreachable') from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f'Error fetch country info: {exc}')
        raise HTTPException(status_code=502, detail='Error fetch country info') from exc

    try:
        data = resp.json()
        objects = data.get('data', {}).get('objects', [])
        if not isinstance(objects, list):
            raise ValueError('Invalid country list')
        record = find_best_country_match(country_name, objects)
        capitals = record.get('capitals', [])
        capital = next((item for item in capitals if item.get('primary')), None)
        if capital is None and capitals:
            capital = capitals[0]
        currencies = record.get('currencies', [])
        if len(currencies) > 1:
            raise HTTPException(status_code=422, detail=f'Country {country_name} has multiple currencies')
        currency = currencies[0] if currencies else None
        return CountryInfo(
            country_code=record['codes']['alpha_2'],
            capital=capital['name'] if capital else None,
            currency_code=currency['code'] if currency else None,
            currency_name=currency['name'] if currency else None,
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail='Invalid geography response') from exc

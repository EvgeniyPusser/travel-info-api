import os

import httpx
from fastapi import HTTPException

from loggers.logger_req import logger


FIXER_URL = 'https://api.apilayer.com/fixer/convert'
API_KEY = os.getenv('FIXER_API_KEY')


async def get_exchange_rate(code_from: str, code_to: str) -> float | int:
    if not API_KEY:
        raise ValueError('FIXER_API_KEY environment variable is not set')

    code_from = code_from.upper()
    code_to = code_to.upper()
    logger.debug(f'Fetching exchange rate {code_from} -> {code_to}')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                FIXER_URL,
                params={'from': code_from, 'to': code_to, 'amount': 1},
                headers={'apikey': API_KEY},
            )
        resp.raise_for_status()
    except httpx.RequestError as exc:
        logger.error('Currency service unreachable')
        raise HTTPException(status_code=502, detail='Currency service unreachable') from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f'Currency service returned HTTP {exc.response.status_code}')
        raise HTTPException(status_code=502, detail='Error fetching exchange rate') from exc

    try:
        data = resp.json()
        if not data.get('success'):
            raise HTTPException(status_code=502, detail='Fixer API returned an error')
        rate = float(data['result'])
        if not 0 < rate < float('inf'):
            raise ValueError('Invalid exchange rate')
        return rate
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.error('Invalid exchange rate response')
        raise HTTPException(status_code=502, detail='Invalid exchange rate response') from exc

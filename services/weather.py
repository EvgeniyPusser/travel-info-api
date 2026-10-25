import os

import httpx
from fastapi import HTTPException

from loggers.logger_req import logger


WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather'
API_KEY = os.getenv('WEATHER_API_KEY')

async def get_weather_summary(city: str) -> str:
    if not API_KEY:
        raise ValueError('WEATHER_API_KEY environment variable is not set')

    logger.debug(f'Fetching weather summary for {city}')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                WEATHER_URL,
                params={'q': city, 'appid': API_KEY, 'units': 'metric'},
            )
    except httpx.RequestError as exc:
        logger.error(f'Weather service unreachable: {exc}')
        raise HTTPException(status_code=502, detail='Weather service unreachable') from exc

    if resp.status_code == 404:
        logger.warning(f'City not found: {city}')
        raise HTTPException(status_code=404, detail=f'City {city} not found')

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(f'Error fetching weather data: {exc}')
        raise HTTPException(status_code=500, detail='Error fetching weather data') from exc

    try:
        data = resp.json()
        description = data['weather'][0]['description']
        temperature = float(data['main']['temp'])
        return f'{description}, {temperature:g} °C'
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail='Invalid weather response') from exc

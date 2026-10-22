"""OpenWeather adapter using the same endpoint and fields as weather-ts."""
import math
import os
from datetime import datetime, timedelta, timezone

import httpx

URL = 'https://api.openweathermap.org/data/2.5/weather'


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def parse_weather(data):
    """Validate the API response before mapping the weather-ts fields."""
    if not isinstance(data, dict):
        raise ValueError('Invalid weather response')
    if str(data.get('cod', 200)) != '200':
        raise ValueError('Weather service returned an error')
    sys = data.get('sys')
    main = data.get('main')
    if not isinstance(sys, dict) or not isinstance(main, dict):
        raise ValueError('Missing weather fields')
    if not all(isinstance(v, str) and v.strip() for v in (data.get('name'), sys.get('country'))):
        raise ValueError('Missing location')
    if not all(_number(v) for v in (main.get('temp'), main.get('pressure'), sys.get('sunset'))):
        raise ValueError('Invalid weather numbers')
    if main['pressure'] <= 0 or sys['sunset'] < 0:
        raise ValueError('Invalid pressure or sunset')
    offset = data.get('timezone', 0)
    if not _number(offset) or offset != int(offset) or abs(offset) >= 86400:
        raise ValueError('Invalid city timezone')
    city_timezone = timezone(timedelta(seconds=offset))
    # A timezone-aware value avoids displaying the PC's timezone as city time.
    sunset = datetime.fromtimestamp(sys['sunset'], timezone.utc).astimezone(city_timezone)
    observed = data.get('dt')
    if observed is not None:
        if not _number(observed) or observed < 0:
            raise ValueError('Invalid observation timestamp')
        observed = datetime.fromtimestamp(observed, timezone.utc).isoformat()
    return {
        'country': sys['country'], 'city': data['name'],
        'temp': main['temp'], 'pressure': main['pressure'],
        'sunset': sunset.isoformat(), 'observed_at': observed,
    }


async def get_weather(city):
    if not isinstance(city, str) or not city.strip():
        return 'Укажите город, например Rehovot,IL.'
    city = city.strip()
    if len(city) > 150 or any(ord(c) < 32 for c in city):
        return 'Название города должно содержать до 150 символов без управляющих символов.'
    key = os.getenv('OPENWEATHER_API_KEY') or os.getenv('VITE_WEATHER_API_KEY')
    if not key or not key.strip():
        return 'Не задан OPENWEATHER_API_KEY (поддерживается также VITE_WEATHER_API_KEY из weather-ts).'
    params = {'q': city, 'appid': key.strip(), 'units': 'metric'}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(URL, params=params)
            response.raise_for_status()
            weather = parse_weather(response.json())
    except httpx.HTTPStatusError as error:
        return {
            401: 'OpenWeather отклонил API-ключ. Проверьте ключ и его активацию.',
            404: 'Город не найден. Уточните название и код страны, например London,GB.',
            429: 'Превышен лимит запросов OpenWeather. Повторите позже.',
        }.get(error.response.status_code, 'Сервис погоды временно недоступен. Повторите позже.')
    except (httpx.RequestError, TimeoutError, OSError):
        return 'Не удалось подключиться к OpenWeather. Проверьте соединение.'
    except (ValueError, TypeError, OverflowError):
        return 'Сервис погоды вернул некорректный ответ.'
    observed = f"\nНаблюдение (UTC): {weather['observed_at']}" if weather['observed_at'] else ''
    return (
        f"Место: {weather['city']}, {weather['country']}\n"
        f"Температура: {weather['temp']:g} °C\n"
        f"Давление: {weather['pressure']:g} hPa\n"
        f"Закат (время города с UTC-смещением): {weather['sunset']}"
        f'{observed}\nИсточник: https://openweathermap.org'
    )


TOOLS = {'get_weather': get_weather}

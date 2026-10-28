# Учебный проект FastAPI

Текущий этап повторяет структуру примера преподавателя:

- `models/travel_model.py` — модели `TravelInfoRequest` и `TravelInfoResponse`.
- `loggers/logger_req.py` — логгер `app` с уровнем `DEBUG`.
- `services/countries.py` — столица и валюта страны через REST Countries v5.
- `services/weather.py` — погода в городе через OpenWeather.
- `services/currency.py` — курс между валютами через Fixer.
- `services/travel.py` — `get_travel_info(request)` собирает ответ по флагам `is_capital`, `is_weather`, `is_currency`.
- `tests/test_logger_req.py` — тесты логгера.
- `pytest.ini` — настройки запуска тестов.

Установка зависимостей и запуск тестов в PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
```

Погодный чат и его тесты сохранены в `archive/weather_llm`.
Приложение FastAPI и его запуск через Uvicorn пока не добавлены.

Для сервисов задайте переменные окружения в конфигурации запуска PyCharm:
`WEATHER_API_KEY` (OpenWeather), `FIXER_API_KEY` (Fixer в APILayer Marketplace),
`COUNTRY_API_KEY` (REST Countries). Названия приведены в `.env.example`;
сам файл `.env` автоматически не загружается. Каждый ключ проверяется только
при вызове соответствующего сервиса. Страны передаются по полному общему
названию на английском, например `France` и `Israel`.

География: https://restcountries.com/docs/countries
Погода: https://openweathermap.org/api/current
Валюта: https://marketplace.apilayer.com/fixer-api/ (`/convert`, ключ в заголовке `apikey`).

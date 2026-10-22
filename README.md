# Учебный проект FastAPI

Текущий этап повторяет структуру примера преподавателя:

- `models/travel_model.py` — модели `TravelInfoRequest` и `TravelInfoResponse`.
- `loggers/logger_req.py` — логгер `app` с уровнем `DEBUG`.
- `tests/test_logger_req.py` — тесты логгера.
- `pytest.ini` — настройки запуска тестов.

Установка зависимостей и запуск тестов в PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
```

Погодный чат и его тесты сохранены в `archive/weather_llm`.
Приложение FastAPI и его запуск через Uvicorn пока не добавлены.

# Погодный чат с Ollama

Архив предыдущего примера. Зависимости находятся в `../../requirements.txt`.

Отдельный аналог валютного чата `Downloads/07_SortedContainers/llm/llm`:
Ollama выбирает инструмент `get_weather(city)`, Python обращается к OpenWeather,
после чего модель формулирует ответ. По умолчанию используется `phi3`.

Запросы к Ollama (`AsyncClient`) и OpenWeather (`httpx.AsyncClient`) выполняются
асинхронно. Ввод в консоли вынесен в `asyncio.to_thread`, запуск — через
`asyncio.run(main())`. При вызове из Python используйте `await get_weather(city)`
и `await answer_turn(messages, text)`; функции разбора данных остаются синхронными.

Связь с `weather-ts`: тот же API `/data/2.5/weather`, `units=metric`, поля
`sys.country`, `name`, `main.temp`, `main.pressure`, `sys.sunset`.
Время заката выводится в часовом поясе города; также сохраняется время наблюдения.
Это текущая погода, не прогноз. Веса модели и погодные данные в проект не включены.

## Запуск в PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull phi3
# Ollama должна быть запущена; при необходимости: ollama serve
$env:OPENWEATHER_API_KEY = 'ваш ключ OpenWeather'
.\.venv\Scripts\python.exe main.py
```

В PyCharm выберите интерпретатор `.venv` и добавьте ключ в Environment variables
конфигурации запуска `main.py`. Ключ не нужно вставлять в исходники.
Поддерживается также переменная `VITE_WEATHER_API_KEY`, как в `weather-ts`.
Файлы `.env` соседнего React-проекта автоматически не читаются.
Можно изменить `OLLAMA_MODEL` и `OLLAMA_HOST`.

Примеры: «Какая погода в Rehovot,IL?», «Температура в Berlin,DE?»,
«Когда закат в London,GB?». Если город не указан, модель должна его уточнить.
Маршрутизация зависит от поведения выбранной модели.

## Проверка API без языковой модели

```powershell
python main.py --city 'Rehovot,IL'
```

## Автоматические тесты

```powershell
python -m pytest tests -v
```

Тесты не требуют ключа, сети, установки Ollama или загрузки модели: используются
поддельные ответы OpenWeather в формате `weather-ts` и поддельный ответ модели.
Проверяются преобразование полей, единицы, часовой пояс, кодирование города,
ошибки API/сети/JSON, проверка аргументов, вызов инструмента и история диалога.
Это тесты Python-интеграции, а не компонентов React `weather-ts`.

Документация: https://docs.ollama.com/api/chat и https://openweathermap.org/current

import copy
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import httpx

import main
import tools


# The same JSON fields consumed by weather-ts/src/components/Data.tsx.
WEATHER_TS_RESPONSE = {
    'cod': 200, 'name': 'Rehovot', 'timezone': 10800, 'dt': 1700000000,
    'sys': {'country': 'IL', 'sunset': 1700006400},
    'main': {'temp': 22.5, 'pressure': 1013},
}


class WeatherTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENWEATHER_API_KEY': 'test-key'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self, data):
        return httpx.Response(200, json=data, request=httpx.Request('GET', tools.URL))

    def test_weather_ts_fields(self):
        result = tools.parse_weather(WEATHER_TS_RESPONSE)
        self.assertEqual(result['city'], 'Rehovot')
        self.assertEqual(result['country'], 'IL')
        self.assertEqual(result['temp'], 22.5)
        self.assertEqual(result['pressure'], 1013)
        self.assertTrue(result['sunset'].endswith('+03:00'))
        self.assertTrue(result['observed_at'].endswith('+00:00'))

    async def test_request_encodes_city_and_units(self):
        requests = []

        def respond(request):
            requests.append(request)
            return self.response(WEATHER_TS_RESPONSE)

        transport = httpx.MockTransport(respond)
        client = httpx.AsyncClient(transport=transport, timeout=15)
        with patch('tools.httpx.AsyncClient', return_value=client) as client_factory:
            answer = await tools.get_weather(' São Paulo,BR &extra=1 ')
        params = parse_qs(urlparse(str(requests[0].url)).query)
        self.assertEqual(params, {'q': ['São Paulo,BR &extra=1'], 'appid': ['test-key'], 'units': ['metric']})
        client_factory.assert_called_once_with(timeout=15)
        self.assertTrue(client.is_closed)
        self.assertIn('22.5 °C', answer)
        self.assertIn('1013 hPa', answer)
        self.assertIn('https://openweathermap.org', answer)
        self.assertNotIn('test-key', answer)

    async def test_invalid_city_never_calls_network(self):
        with patch('tools.httpx.AsyncClient') as request:
            for city in ('', '  ', None, 123, 'x'*151, 'Paris\nBerlin'):
                with self.subTest(city=city):
                    self.assertIsInstance(await tools.get_weather(city), str)
            request.assert_not_called()

    async def test_missing_key(self):
        os.environ.clear()
        with patch('tools.httpx.AsyncClient') as request:
            self.assertIn('OPENWEATHER_API_KEY', await tools.get_weather('Rehovot'))
            request.assert_not_called()

    async def test_vite_key_compatibility(self):
        os.environ.clear()
        os.environ['VITE_WEATHER_API_KEY'] = 'vite-test-key'
        with patch('tools.httpx.AsyncClient.get', new_callable=AsyncMock,
                   return_value=self.response(WEATHER_TS_RESPONSE)) as request:
            await tools.get_weather('Rehovot')
        self.assertEqual(request.call_args.kwargs['params']['appid'], 'vite-test-key')

    async def test_http_errors_hide_credentials(self):
        for code, fragment in [(401, 'API-ключ'), (404, 'не найден'), (429, 'лимит'), (500, 'недоступен')]:
            with self.subTest(code=code):
                response = httpx.Response(code, request=httpx.Request('GET', 'https://example/?appid=test-key'))
                with patch('tools.httpx.AsyncClient.get', new_callable=AsyncMock, return_value=response):
                    result = await tools.get_weather('Rehovot')
                self.assertIn(fragment, result)
                self.assertNotIn('test-key', result)

    async def test_network_errors(self):
        for error in [httpx.ConnectError('offline'), httpx.ReadTimeout('timeout'), TimeoutError(), OSError('unavailable')]:
            with patch('tools.httpx.AsyncClient.get', new_callable=AsyncMock, side_effect=error):
                self.assertIn('подключиться', await tools.get_weather('Rehovot'))

    async def test_invalid_json(self):
        response = httpx.Response(200, content=b'<html>bad gateway</html>', request=httpx.Request('GET', tools.URL))
        with patch('tools.httpx.AsyncClient.get', new_callable=AsyncMock, return_value=response):
            self.assertIn('некорректный', await tools.get_weather('Rehovot'))

    async def test_invalid_api_fields(self):
        variants = [None, [], {}, {'cod': '404'}]
        for group, key, value in [('main', 'temp', True), ('main', 'temp', '22'),
                                  ('main', 'pressure', -1), ('sys', 'sunset', -1),
                                  ('sys', 'sunset', 1e100), ('sys', 'country', '')]:
            data = copy.deepcopy(WEATHER_TS_RESPONSE)
            data[group][key] = value
            variants.append(data)
        for data in variants:
            with self.subTest(data=data), patch('tools.httpx.AsyncClient.get', new_callable=AsyncMock,
                                               return_value=self.response(data)):
                self.assertIn('некорректный', await tools.get_weather('Rehovot'))

    def test_nonfinite_numbers(self):
        for value in [float('inf'), float('-inf'), float('nan')]:
            data = copy.deepcopy(WEATHER_TS_RESPONSE)
            data['main']['temp'] = value
            with self.assertRaises(ValueError):
                tools.parse_weather(data)

    def test_timezone_validation(self):
        for value in [True, '10800', 86400, -86400, 0.5]:
            data = copy.deepcopy(WEATHER_TS_RESPONSE)
            data['timezone'] = value
            with self.assertRaises(ValueError):
                tools.parse_weather(data)

    def test_optional_observation(self):
        data = copy.deepcopy(WEATHER_TS_RESPONSE)
        del data['dt']
        self.assertIsNone(tools.parse_weather(data)['observed_at'])


class ChatTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_json_and_code_fence(self):
        call = {'tool': 'get_weather', 'arguments': {'city': 'Rehovot'}}
        text = json.dumps(call)
        self.assertEqual(main.parse_tool_call(text), call)
        self.assertEqual(main.parse_tool_call('```json\n'+text+'\n```'), call)

    def test_prose_and_invalid_json_are_not_tools(self):
        for text in ['Hello!', '[]', '{bad}', 'Let me call {"tool":"get_weather"}', '{"other": 1}']:
            self.assertIsNone(main.parse_tool_call(text))

    async def test_invalid_tool_arguments_do_not_execute(self):
        with patch.dict(main.TOOLS, {'get_weather': AsyncMock()}):
            for call in [{'tool': 1}, {'tool': 'delete'}, {'tool': 'get_weather', 'arguments': []},
                         {'tool': 'get_weather', 'arguments': {'city': ''}},
                         {'tool': 'get_weather', 'arguments': {'city': 'Paris', 'extra': 1}}]:
                self.assertIsInstance(await main.call_tool(call), str)
            main.TOOLS['get_weather'].assert_not_awaited()

    async def test_weather_tool_and_history(self):
        history = [{'role': 'system', 'content': 'instructions'}]
        request = AsyncMock(side_effect=[
            '{"tool":"get_weather","arguments":{"city":"Rehovot,IL"}}', '22.5 °C'])
        with patch.dict(main.TOOLS, {'get_weather': AsyncMock(return_value='22.5 °C')}):
            self.assertEqual(await main.answer_turn(history, 'weather in Rehovot', request), '22.5 °C')
            main.TOOLS['get_weather'].assert_awaited_once_with(city='Rehovot,IL')
        self.assertEqual(len(history), 3)
        self.assertEqual([m['role'] for m in history], ['system', 'user', 'assistant'])
        self.assertIn('Application tool result', request.call_args.args[0][-1]['content'])

    async def test_failed_routing_leaves_history_unchanged(self):
        history = [{'role': 'system', 'content': 'instructions'}]
        with self.assertRaises(ConnectionError):
            await main.answer_turn(history, 'weather', AsyncMock(side_effect=ConnectionError()))
        self.assertEqual(len(history), 1)

    async def test_failed_followup_uses_actual_tool_result(self):
        history = []
        request = AsyncMock(side_effect=[
            '{"tool":"get_weather","arguments":{"city":"Rehovot"}}', ConnectionError()])
        with patch.dict(main.TOOLS, {'get_weather': AsyncMock(return_value='actual measurement')}):
            self.assertEqual(await main.answer_turn(history, 'weather', request), 'actual measurement')

    async def test_no_tool_for_normal_conversation(self):
        history = []
        request = AsyncMock(return_value='Hello!')
        self.assertEqual(await main.answer_turn(history, 'Hi', request), 'Hello!')
        request.assert_awaited_once()

    async def test_chat_request_consumes_async_stream(self):
        async def chunks():
            yield {'message': {'content': 'Hello'}}
            yield {'message': {'content': '!'}}

        client = Mock(chat=AsyncMock(return_value=chunks()))
        messages = [{'role': 'user', 'content': 'Hi'}]
        with patch.dict('sys.modules', {'ollama': Mock(AsyncClient=Mock(return_value=client))}):
            self.assertEqual(await main.chat_request(messages), 'Hello!')
        client.chat.assert_awaited_once_with(model=main.MODEL_NAME, messages=messages,
                                             stream=True, options={'temperature': 0})

    async def test_main_reads_input_in_thread(self):
        with patch('sys.argv', ['main.py']), patch('builtins.input', side_effect=['Hi', 'exit']) as read_input, \
                patch('main.asyncio.to_thread', wraps=asyncio.to_thread) as to_thread, \
                patch('main.answer_turn', new_callable=AsyncMock, return_value='Hello!') as answer, \
                patch('builtins.print'):
            await main.main()
        self.assertEqual(to_thread.await_count, 2)
        read_input.assert_called_with('Вы: ')
        answer.assert_awaited_once()

    async def test_main_city_awaits_weather(self):
        with patch('sys.argv', ['main.py', '--city', 'Rehovot,IL']), \
                patch('main.get_weather', new_callable=AsyncMock, return_value='22.5 °C') as weather, \
                patch('builtins.print') as output:
            await main.main()
        weather.assert_awaited_once_with('Rehovot,IL')
        output.assert_called_once_with('22.5 °C')


if __name__ == '__main__':
    unittest.main()

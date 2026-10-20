import copy
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import main
import tools


# The same JSON fields consumed by weather-ts/src/components/Data.tsx.
WEATHER_TS_RESPONSE = {
    'cod': 200, 'name': 'Rehovot', 'timezone': 10800, 'dt': 1700000000,
    'sys': {'country': 'IL', 'sunset': 1700006400},
    'main': {'temp': 22.5, 'pressure': 1013},
}


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENWEATHER_API_KEY': 'test-key'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self, data):
        return io.BytesIO(json.dumps(data).encode())

    def test_weather_ts_fields(self):
        result = tools.parse_weather(WEATHER_TS_RESPONSE)
        self.assertEqual(result['city'], 'Rehovot')
        self.assertEqual(result['country'], 'IL')
        self.assertEqual(result['temp'], 22.5)
        self.assertEqual(result['pressure'], 1013)
        self.assertTrue(result['sunset'].endswith('+03:00'))
        self.assertTrue(result['observed_at'].endswith('+00:00'))

    def test_request_encodes_city_and_units(self):
        with patch('tools.urlopen', return_value=self.response(WEATHER_TS_RESPONSE)) as request:
            answer = tools.get_weather(' São Paulo,BR &extra=1 ')
        params = parse_qs(urlparse(request.call_args.args[0]).query)
        self.assertEqual(params, {'q': ['São Paulo,BR &extra=1'], 'appid': ['test-key'], 'units': ['metric']})
        self.assertEqual(request.call_args.kwargs['timeout'], 15)
        self.assertIn('22.5 °C', answer)
        self.assertIn('1013 hPa', answer)
        self.assertIn('https://openweathermap.org', answer)
        self.assertNotIn('test-key', answer)

    def test_invalid_city_never_calls_network(self):
        with patch('tools.urlopen') as request:
            for city in ('', '  ', None, 123, 'x'*151, 'Paris\nBerlin'):
                with self.subTest(city=city):
                    self.assertIsInstance(tools.get_weather(city), str)
            request.assert_not_called()

    def test_missing_key(self):
        os.environ.clear()
        with patch('tools.urlopen') as request:
            self.assertIn('OPENWEATHER_API_KEY', tools.get_weather('Rehovot'))
            request.assert_not_called()

    def test_vite_key_compatibility(self):
        os.environ.clear()
        os.environ['VITE_WEATHER_API_KEY'] = 'vite-test-key'
        with patch('tools.urlopen', return_value=self.response(WEATHER_TS_RESPONSE)) as request:
            tools.get_weather('Rehovot')
        self.assertIn('appid=vite-test-key', request.call_args.args[0])

    def test_http_errors_hide_credentials(self):
        for code, fragment in [(401, 'API-ключ'), (404, 'не найден'), (429, 'лимит'), (500, 'недоступен')]:
            with self.subTest(code=code):
                with patch('tools.urlopen', side_effect=HTTPError('https://example/?appid=test-key', code, 'error', None, None)):
                    result = tools.get_weather('Rehovot')
                self.assertIn(fragment, result)
                self.assertNotIn('test-key', result)

    def test_network_errors(self):
        for error in [URLError('offline'), TimeoutError(), OSError('unavailable')]:
            with patch('tools.urlopen', side_effect=error):
                self.assertIn('подключиться', tools.get_weather('Rehovot'))

    def test_invalid_json(self):
        with patch('tools.urlopen', return_value=io.BytesIO(b'<html>bad gateway</html>')):
            self.assertIn('некорректный', tools.get_weather('Rehovot'))

    def test_invalid_api_fields(self):
        variants = [None, [], {}, {'cod': '404'}]
        for group, key, value in [('main', 'temp', True), ('main', 'temp', '22'),
                                  ('main', 'pressure', -1), ('sys', 'sunset', -1),
                                  ('sys', 'sunset', 1e100), ('sys', 'country', '')]:
            data = copy.deepcopy(WEATHER_TS_RESPONSE)
            data[group][key] = value
            variants.append(data)
        for data in variants:
            with self.subTest(data=data), patch('tools.urlopen', return_value=self.response(data)):
                self.assertIn('некорректный', tools.get_weather('Rehovot'))

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


class ChatTests(unittest.TestCase):
    def test_parse_json_and_code_fence(self):
        call = {'tool': 'get_weather', 'arguments': {'city': 'Rehovot'}}
        text = json.dumps(call)
        self.assertEqual(main.parse_tool_call(text), call)
        self.assertEqual(main.parse_tool_call('```json\n'+text+'\n```'), call)

    def test_prose_and_invalid_json_are_not_tools(self):
        for text in ['Hello!', '[]', '{bad}', 'Let me call {"tool":"get_weather"}', '{"other": 1}']:
            self.assertIsNone(main.parse_tool_call(text))

    def test_invalid_tool_arguments_do_not_execute(self):
        with patch.dict(main.TOOLS, {'get_weather': unittest.mock.Mock()}):
            for call in [{'tool': 1}, {'tool': 'delete'}, {'tool': 'get_weather', 'arguments': []},
                         {'tool': 'get_weather', 'arguments': {'city': ''}},
                         {'tool': 'get_weather', 'arguments': {'city': 'Paris', 'extra': 1}}]:
                self.assertIsInstance(main.call_tool(call), str)
            main.TOOLS['get_weather'].assert_not_called()

    def test_weather_tool_and_history(self):
        history = [{'role': 'system', 'content': 'instructions'}]
        request = unittest.mock.Mock(side_effect=[
            '{"tool":"get_weather","arguments":{"city":"Rehovot,IL"}}', '22.5 °C'])
        with patch.dict(main.TOOLS, {'get_weather': unittest.mock.Mock(return_value='22.5 °C')}):
            self.assertEqual(main.answer_turn(history, 'weather in Rehovot', request), '22.5 °C')
            main.TOOLS['get_weather'].assert_called_once_with(city='Rehovot,IL')
        self.assertEqual(len(history), 3)
        self.assertEqual([m['role'] for m in history], ['system', 'user', 'assistant'])
        self.assertIn('Application tool result', request.call_args.args[0][-1]['content'])

    def test_failed_routing_leaves_history_unchanged(self):
        history = [{'role': 'system', 'content': 'instructions'}]
        with self.assertRaises(ConnectionError):
            main.answer_turn(history, 'weather', unittest.mock.Mock(side_effect=ConnectionError()))
        self.assertEqual(len(history), 1)

    def test_failed_followup_uses_actual_tool_result(self):
        history = []
        request = unittest.mock.Mock(side_effect=[
            '{"tool":"get_weather","arguments":{"city":"Rehovot"}}', ConnectionError()])
        with patch.dict(main.TOOLS, {'get_weather': lambda city: 'actual measurement'}):
            self.assertEqual(main.answer_turn(history, 'weather', request), 'actual measurement')

    def test_no_tool_for_normal_conversation(self):
        history = []
        request = unittest.mock.Mock(return_value='Hello!')
        self.assertEqual(main.answer_turn(history, 'Hi', request), 'Hello!')
        request.assert_called_once()


if __name__ == '__main__':
    unittest.main()

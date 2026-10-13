"""Offline regression checks for the request-spacing client patch."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from curriculum_engine.config import Settings, PROJECT_ROOT
from curriculum_engine.demo import DemoClient
from curriculum_engine.source_loader import load_sources
from curriculum_engine.lesson_types import LessonPlan
from curriculum_engine.llm_client import JsonModelClient, GenerationError, provider_details


class ProviderError(Exception):
    def __init__(self, status, body, retry=None):
        self.status_code = status
        self.body = body
        self.response = SimpleNamespace(headers={} if retry is None else {'Retry-After': str(retry)})
        super().__init__('Provider wrapper - ' + json.dumps(body))


class RateLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        documents = load_sources([PROJECT_ROOT / 'examples/demo_lecture.md'])
        cls.valid = json.dumps(DemoClient(documents).responses['plan'])

    def good(self):
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason='stop', message=SimpleNamespace(content=self.valid))])

    def client(self, sequence):
        waits = []
        queue = list(sequence)
        def transport(**kwargs):
            result = queue.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        client = JsonModelClient(Settings(), lambda _: None, transport=transport, sleep=waits.append)
        return client, waits

    def complete(self, client):
        return client.complete_json(LessonPlan, 'Return the plan.', {}, stage='Test plan')

    def test_retry_after_header_is_respected_in_visible_chunks(self):
        error = ProviderError(429, {'error': {'code': 'rate_limit_exceeded', 'message': 'Slow down'}}, 90)
        client, waits = self.client([error, self.good()])
        self.complete(client)
        self.assertEqual(sum(waits), 91)
        self.assertTrue(all(value <= 30 for value in waits))
        self.assertEqual(client.call_count, 2)

    def test_long_retry_after_stops_without_retrying_early(self):
        error = ProviderError(429, {'error': {'message': 'Daily quota'}}, 3600)
        client, waits = self.client([error])
        with self.assertRaisesRegex(GenerationError, '3601s'):
            self.complete(client)
        self.assertEqual(client.call_count, 1)
        self.assertEqual(waits, [])

    def test_429_fallback_then_400_preserves_provider_message(self):
        rate = ProviderError(429, {'error': {'message': 'Slow down'}})
        bad = ProviderError(400, {'error': {'code': 'invalid_request_error', 'message': 'Invalid parameter'}})
        client, waits = self.client([rate, bad])
        with self.assertRaisesRegex(GenerationError, 'Invalid parameter'):
            self.complete(client)
        self.assertEqual(sum(waits), 65)
        self.assertEqual(client.call_count, 2)

    def test_provider_json_failure_gets_one_repair(self):
        bad = ProviderError(400, {'error': {'code': 'json_validate_failed',
            'message': 'Failed to generate JSON', 'failed_generation': 'DO NOT DISPLAY'}})
        client, waits = self.client([bad, self.good()])
        self.assertIsInstance(self.complete(client), LessonPlan)
        self.assertEqual(client.call_count, 2)
        self.assertEqual(sum(waits), 65)

    def test_provider_details_redact_key_and_omit_failed_generation(self):
        with patch.dict('os.environ', {'GROQ_API_KEY': 'dummy-sensitive-value'}):
            error = ProviderError(400, {'error': {'code': 'bad',
                'message': 'Invalid dummy-sensitive-value', 'failed_generation': 'DO NOT DISPLAY'}})
            code, detail = provider_details(error)
        self.assertEqual(code, 'bad')
        self.assertIn('[REDACTED]', detail)
        self.assertNotIn('dummy-sensitive-value', detail)
        self.assertNotIn('DO NOT DISPLAY', detail)

    def test_successful_requests_are_spaced(self):
        current = [0]
        waits = []
        def sleep(seconds):
            waits.append(seconds)
            current[0] += seconds
        client = JsonModelClient(Settings(), lambda _: None,
            transport=lambda **kwargs: self.good(), sleep=sleep,
            clock=lambda: current[0], request_interval=65)
        self.complete(client)
        self.complete(client)
        self.assertEqual(sum(waits), 65)
        self.assertEqual(client.call_count, 2)


if __name__ == '__main__':
    unittest.main()

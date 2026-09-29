"""Exercise the REAL SDK against a local HTTP contract server, never real credentials."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from backend.config import Settings, ROOT
from backend.memory.hindsight import HindsightMemory, MemoryUnavailable
from backend.models import Deal


@pytest.fixture
def deal():
    return Deal.model_validate(json.loads((ROOT / 'data/sample_deals.json').read_text())[0])


@pytest.fixture
def upstream():
    requests = []
    state = {'fail': False, 'success': True, 'empty': False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_request(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
            requests.append((self.command, self.path, body))
            status = 401 if state['fail'] else 200
            if state['fail']:
                result = {'detail': 'secret-that-must-not-leak'}
            elif self.path.endswith('/recall'):
                result = {'results': [{'id': 'fact-1', 'text': 'India-only residency required.', 'document_id': 'aster-01'}]}
            elif self.path.endswith('/reflect'):
                result = {'text': '' if state['empty'] else 'Ask Rohan to review residency. [fact-1]'}
            elif self.path.endswith('/memories'):
                result = {'success': state['success'], 'bank_id': 'test-aster-health', 'items_count': 1, 'async': False}
            else:
                result = {'bank_id': 'test-aster-health', 'name': 'Aster', 'mission': '',
                          'disposition': {'skepticism': 3, 'literalism': 3, 'empathy': 3}}
            encoded = json.dumps(result).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        do_POST = handle_request
        do_PUT = handle_request

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}', requests, state
    server.shutdown()
    server.server_close()
    thread.join()


def adapter(url):
    return HindsightMemory(Settings(_env_file=None, hindsight_base_url=url, hindsight_api_key='',
                                    hindsight_bank_prefix='test', hindsight_timeout=5))


def test_sdk_wire_contract(upstream, deal):
    url, requests, _ = upstream

    async def run():
        memory = adapter(url)
        try:
            await memory.retain(deal, deal.interactions[0])
            memories = await memory.recall(deal, 'Residency requirements?')
            assert memories[0].document_id == 'aster-01'
            assert memories[0].type == 'world'  # optional upstream type is nullable
            assert 'Rohan' in await memory.reflect(deal, 'Next step?', memories)
            assert memory.bank_id('other') != memory.bank_id(deal.id)
        finally:
            await memory.close()

    asyncio.run(run())
    assert requests[0][0] == 'PUT'
    assert requests[1][1] == '/v1/default/banks/test-aster-health/memories'
    retain = requests[1][2]
    assert retain['async'] is False
    assert retain['items'][0]['document_id'] == 'aster-01'
    assert 'India-only' in retain['items'][0]['content']
    assert retain['items'][0]['metadata']['deal_id'] == deal.id
    assert requests[2][2]['query'] == 'Residency requirements?'
    assert 'fact-1' in requests[3][2]['context']


@pytest.mark.parametrize('failure', ['fail', 'success', 'empty'])
def test_sdk_errors_are_safe(upstream, deal, failure):
    url, _, state = upstream
    state[failure] = failure != 'success'

    async def run():
        memory = adapter(url)
        try:
            with pytest.raises(MemoryUnavailable) as error:
                if failure == 'empty':
                    await memory.reflect(deal, 'Next step?', [])
                else:
                    await memory.retain(deal, deal.interactions[0])
            assert 'secret-that-must-not-leak' not in str(error.value)
        finally:
            await memory.close()

    asyncio.run(run())


def test_cloud_payment_required_has_actionable_message(deal):
    class CloudOutOfCredits(Exception):
        status = 402

    async def run():
        memory = adapter('https://api.hindsight.vectorize.io')
        memory.client.acreate_bank = AsyncMock(return_value=None)
        memory.client.aretain = AsyncMock(side_effect=CloudOutOfCredits())
        try:
            with pytest.raises(MemoryUnavailable, match='insufficient credits.*HTTP 402'):
                await memory.retain(deal, deal.interactions[0])
        finally:
            await memory.close()

    from unittest.mock import AsyncMock
    asyncio.run(run())

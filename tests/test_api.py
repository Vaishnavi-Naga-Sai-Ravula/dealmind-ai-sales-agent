"""External-service doubles are injected only in tests; the app has no fake memory."""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.memory.hindsight import MemoryUnavailable
from backend.models import Memory


@pytest.fixture
def memory():
    service = AsyncMock()
    service.bank_id = lambda deal_id: f'test-{deal_id}'
    service.recall.return_value = [Memory(id='evidence-1', text='Priya requires India-only data residency.')]
    service.reflect.return_value = 'Confirm India-only residency with Rohan. [evidence-1]'
    return service


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, database_path=tmp_path / 'test.db', hindsight_base_url='')


@pytest.fixture
def client(settings, memory):
    with TestClient(create_app(settings, memory)) as session:
        yield session


def test_health_and_samples(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    deals = client.get('/api/deals').json()
    assert len(deals) == 3
    assert sum(len(d['interactions']) for d in deals) == 10
    detail = client.get('/api/deals/aster-health').json()
    assert detail['interactions'][0]['id'] == 'aster-04'
    assert all(i['memory_status'] == 'pending' for i in detail['interactions'])


def test_create_deal_and_persistence(client, settings, memory):
    response = client.post('/api/deals', json={'company': 'New Co', 'contact': 'Dev', 'title': 'Pilot', 'value': 1200})
    assert response.status_code == 201
    deal_id = response.json()['id']
    with TestClient(create_app(settings, memory)) as restarted:
        assert restarted.get(f'/api/deals/{deal_id}').json()['company'] == 'New Co'
        assert len(restarted.get('/api/deals').json()) == 4  # samples seed only once


def test_interaction_saved_and_retained(client, memory):
    response = client.post('/api/deals/aster-health/interactions', json={
        'title': 'Security review', 'content': 'Rohan requires SSO validation.', 'channel': 'Meeting'})
    assert response.status_code == 201
    assert response.json()['memory_status'] == 'retained'
    assert memory.retain.await_count == 1
    assert len(client.get('/api/deals/aster-health').json()['interactions']) == 5


def test_failed_delivery_persists_then_retry_is_safe(client, memory):
    memory.retain.side_effect = MemoryUnavailable('Service unavailable')
    saved = client.post('/api/deals/aster-health/interactions', json={'title': 'Call', 'content': 'Needs SSO'}).json()
    assert saved['memory_status'] == 'failed'
    failed = client.post('/api/deals/aster-health/memory/sync').json()
    assert failed['remaining'] == 5
    assert failed['error'] == 'Service unavailable'
    memory.retain.side_effect = None
    memory.retain.reset_mock()
    synced = client.post('/api/deals/aster-health/memory/sync').json()
    assert synced == {'retained': 5, 'remaining': 0, 'error': None}
    ids = [call.args[1].id for call in memory.retain.await_args_list]
    assert ids[:4] == ['aster-01', 'aster-02', 'aster-03', 'aster-04']
    assert ids[-1] == saved['id']
    assert client.post('/api/deals/aster-health/memory/sync').json()['retained'] == 0
    assert memory.retain.await_count == 5


def test_recall_and_intelligence_use_evidence(client, memory):
    recall = client.post('/api/deals/aster-health/memory/recall', json={'query': 'What security concerns remain?'})
    assert recall.status_code == 200
    assert recall.json()['memories'][0]['id'] == 'evidence-1'
    brief = client.post('/api/deals/aster-health/intelligence', json={}).json()
    assert brief['mode'] == 'hindsight'
    assert 'India-only' in brief['brief']
    assert any('India-only' in action for action in brief['next_actions'])
    args = memory.reflect.await_args.args
    assert args[0].id == 'aster-health'
    assert args[2][0].id == 'evidence-1'


@pytest.mark.parametrize('failure', ['recall', 'reflect', 'empty'])
def test_intelligence_fallback_is_labelled(client, memory, failure):
    if failure == 'empty':
        memory.recall.return_value = []
    else:
        getattr(memory, failure).side_effect = MemoryUnavailable('Service unavailable')
    response = client.post('/api/deals/aster-health/intelligence', json={})
    assert response.status_code == 200
    assert response.json()['mode'] == 'demo'
    assert 'not AI-generated' in response.json()['warning']


def test_unconfigured_real_adapter(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/deals/aster-health/memory/recall', json={}).status_code == 503
        response = client.post('/api/deals/aster-health/interactions', json={'title': 'Call', 'content': 'Needs SSO'})
        assert response.status_code == 201
        assert response.json()['memory_status'] == 'failed'
        assert 'not configured' in response.json()['memory_error']


@pytest.mark.parametrize('path,body,status', [
    ('/api/deals', {'company': ' ', 'contact': 'A', 'title': 'B'}, 422),
    ('/api/deals', {'company': 'A', 'contact': 'B', 'title': 'C', 'value': -1}, 422),
    ('/api/deals/aster-health/interactions', {'title': 'X', 'content': 'ab'}, 422),
    ('/api/deals/aster-health/interactions', {'title': 'X', 'content': 'abc', 'occurred_at': '2026-09-01T09:00:00'}, 422),
    ('/api/deals/aster-health/memory/recall', {'query': ' '}, 422),
    ('/api/deals/missing/interactions', {'title': 'X', 'content': 'abc'}, 404),
    ('/api/deals/missing/memory/sync', {}, 404),
    ('/api/deals/missing/intelligence', {}, 404),
])
def test_validation_and_missing_records(client, path, body, status):
    assert client.post(path, json=body).status_code == status


def test_cors(client):
    response = client.options('/api/deals', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert client.get('/api/deals/missing').status_code == 404

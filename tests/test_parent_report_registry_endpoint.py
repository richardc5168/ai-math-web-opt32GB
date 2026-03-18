import importlib
import os

import httpx
import pytest


@pytest.mark.anyio
async def test_parent_report_registry_upsert_and_fetch(tmp_path):
    db_path = tmp_path / 'parent_report_registry.db'
    os.environ['DB_PATH'] = str(db_path)

    import server

    importlib.reload(server)

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        report_data = {
            'v': 1,
            'name': 'Kai',
            'ts': 1700000000000,
            'days': 7,
            'd': {
                'practice': {
                    'events': []
                }
            }
        }

        upsert_report = await client.post(
            '/v1/parent-report/registry/upsert',
            json={
                'name': 'Kai',
                'pin': '1234',
                'report_data': report_data,
            },
        )
        assert upsert_report.status_code == 200
        assert upsert_report.json()['ok'] is True

        upsert_event = await client.post(
            '/v1/parent-report/registry/upsert',
            json={
                'name': 'Kai',
                'pin': '1234',
                'practice_event': {
                    'ts': 1700000005000,
                    'score': 2,
                    'total': 3,
                    'topic': 'fraction-word-g5',
                    'kind': 'generic_fraction_word',
                    'mode': 'quiz3',
                    'completed': True,
                },
            },
        )
        assert upsert_event.status_code == 200
        assert upsert_event.json()['ok'] is True

        fetched = await client.post(
            '/v1/parent-report/registry/fetch',
            json={
                'name': 'Kai',
                'pin': '1234',
            },
        )
        assert fetched.status_code == 200
        payload = fetched.json()
        assert payload['ok'] is True
        assert payload['entry']['name'] == 'Kai'
        assert 'pin' not in payload['entry']
        events = payload['entry']['data']['d']['practice']['events']
        assert len(events) == 1
        assert events[0]['topic'] == 'fraction-word-g5'
        assert events[0]['score'] == 2
        assert events[0]['total'] == 3

        wrong_pin = await client.post(
            '/v1/parent-report/registry/fetch',
            json={
                'name': 'Kai',
                'pin': '9999',
            },
        )
        assert wrong_pin.status_code == 403

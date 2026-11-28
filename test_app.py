from app import app

client = app.test_client()


def test_health():
    assert client.get('/health').get_json() == {'status': 'ok'}


def test_message_is_kept():
    assert client.get('/api').get_json() == {'message': 'Hello from Jenkins demo app!'}


def test_ui_page():
    r = client.get('/')
    assert r.status_code == 200 and b'Jenkins Demo App' in r.data


def test_task_flow():
    created = client.post('/api/tasks', json={'title': 'write tests'})
    assert created.status_code == 201
    task_id = created.get_json()['id']
    assert any(t['id'] == task_id for t in client.get('/api/tasks').get_json())
    assert client.delete(f'/api/tasks/{task_id}').status_code == 204
    assert client.post('/api/tasks', json={'title': ''}).status_code == 400
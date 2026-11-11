# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import datetime
import requests
import threading

TOKEN = '8855463512:AAHtzqo-mUEmM0Qz73XqX5uKFizEq1LRjRY'
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
daily_like_pending = {}
auto_like_jobs = {}
redeem_codes = {} # Format: {code: {'amount': float, 'max_uses': int, 'used_by': set, 'expiry_time': float}}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'referrals': 0,
            'activePlan': 'None',
            'planExpiry': 'N/A',
            'lastDemoClaim': 0,
            'dailyClaimsCount': 0,
            'lastClaimDate': '',
            'refPlanClaimed': False,
            'referred': False,
            'notifiedAdmin': False
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
    markup.row('💖 𝑩𝒖𝒚 𝑳𝒊𝒌𝒆 / 𝑷𝒍𝒂𝒏𝒔', '🎁 𝙳𝘢𝘪𝗹𝘺 𝙵𝚛𝚎e 𝙻i𝙆𝚎')
    markup.row('🛒 𝑪𝑪 𝑺𝒕𝒐𝒓𝒆', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)')
    markup.row('🎁 𝑹𝒆𝒇𝒆𝒓 & 𝑬𝒂𝒓𝒏', '🎁 𝑹𝒆𝒆𝒅𝒆𝒎 𝑪𝒐𝒅𝒆')
    markup.row('💼 𝗠𝘆 𝑷rо𝒇𝒊𝒍𝒆', '💬 𝐇𝐞𝐥𝐩 & 𝐒𝐮𝐩𝐩𝐨𝐫𝐭')
    if user_id == ADMIN_ID:
        markup.row('👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝒍')
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
        markup.add(types.InlineKeyboardButton("🔄 𝙼𝚊𝘪𝘯 𝖢𝘩𝘦𝘤𝘬 𝖪𝘢𝘳 𝗟𝗶𝘆𝗮", callback_data='verify_join'))
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
        bot.answer_callback_query(call.id, "❌ 𝘈𝘢𝘱𝘯𝘦 𝘢𝘣𝘩𝘪 𝘵𝘢𝘬 𝘴𝘢𝘣𝘩𝘪 𝘤𝘩𝒂𝘯𝘯𝘦𝘭𝘴 𝘫𝘰𝘪𝘯 𝘕𝘢𝘩𝘪 𝘬𝘪𝘺𝘢!", show_alert=True)

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

@bot.message_handler(commands=['u'])
def user_profile_cmd(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or 'User'
    username = f"@{message.from_user.username}" if message.from_user.username else 'None'
    user = get_user(user_id)
    text = (
        f"👤 *𝒀𝑶𝑼𝑹 𝑨𝑪𝑪𝑶𝑼𝑵𝑻 𝑫𝑬𝑻𝑨𝑰𝑳𝑺* 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📛 *Name:* {first_name}\n"
        f"🆔 *User ID:* `{user_id}`\n"
        f"🔗 *Username:* {username}\n"
        f"💰 *Wallet Balance:* `Rs. {user['balance']}`\n"
        f"📦 *Active Plan:* {user['activePlan']}\n"
        f"⏰ *Plan Expiry:* {user['planExpiry']}\n"
        f"👥 *Total Referrals:* {user['referrals']}/10\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text

    if text in ['👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝙡', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)', '💖 𝑩𝒖𝒚 𝑳𝒊𝒌𝒆 / 𝑷𝒍𝒂𝒏𝒔', '🛒 𝑪𝑪 𝑺𝒕𝒐𝒓𝒆', '💼 𝗠𝘆 𝑷𝗿𝗼𝒇𝗶𝗹𝗲', '🎁 𝑹𝒆𝒇𝒆𝒓 & 𝑬𝒂𝒓𝒏', '💬 𝐇𝐞𝐥𝐩 & 𝐒𝐮𝐩𝐩𝐨𝐫𝒕', '🎁 𝙳𝘢𝘪𝗹𝘺 𝙵𝚛𝚎e 𝙻i𝙆𝚎', '🎁 𝑹𝒆𝒆𝒅𝒆𝒎 𝑪𝒐𝒅𝒆']:
        pending_state.pop(user_id, None)
        pending_uid.pop(user_id, None)
        if text != '🎁 𝙳𝘢𝘪𝗹𝘺 𝙵𝚛𝚎e 𝙻i𝙆𝚎':
            daily_like_pending.pop(user_id, None)

    state = pending_state.get(user_id)
    user = get_user(user_id)

    # Redeem Code User Flow
    if text == '🎁 𝑹𝒆𝒆𝒅𝒆𝒎 𝑪𝒐𝒅𝒆':
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

        # Notify Admin with full details of user who redeemed the code
        try:
            first_name = message.from_user.first_name or 'User'
            username = f"@{message.from_user.username}" if message.from_user.username else 'None'
            current_uses = len(r_data['used_by'])
            bot.send_message(
                ADMIN_ID,
                f"🎁 *𝑵𝒂𝒚𝒂 𝗥𝗲𝗱𝗲𝗲m 𝕮𝒐𝒅𝒆 𝑼𝒔𝒆𝒅!* 🔥\n\n"
                f"👤 *Name:* {first_name}\n"
                f"🆔 *User ID:* `{user_id}`\n"
                f"🔗 *Username:* {username}\n"
                f"🎟️ *Code:* `{code_input}`\n"
                f"💰 *Amount Credited:* Rs. {amount}\n"
                f"📊 *Usage Count:* {current_uses}/{r_data['max_uses']}",
                parse_mode='Markdown'
            )
        except Exception:
            pass
        return

    # Admin Bypass Mode for Daily Free Like
    if user_id == ADMIN_ID and user_id in daily_like_pending and daily_like_pending[user_id].get('step') == 'WAITING_FOR_UID':
        uid = text.strip()
        daily_like_pending.pop(user_id, None)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇮🇳 IND", callback_data=f"dl_ind_{uid}"),
            types.InlineKeyboardButton("🇧🇩 BD", callback_data=f"dl_bd_{uid}"),
            types.InlineKeyboardButton("🇮🇩 ID", callback_data=f"dl_id_{uid}"),
            types.InlineKeyboardButton("🇸🇬 SG", callback_data=f"dl_sg_{uid}")
        )
        bot.send_message(user_id, f"👑 *Admin Bypass Mode:* Unlimited Free Likes\n🆔 UID Saved: `{uid}`\n\n👇 Apna Server / Region select karein:", parse_mode='Markdown', reply_markup=markup)
        return

    if user_id in daily_like_pending and daily_like_pending[user_id].get('step') == 'WAITING_FOR_UID':
        uid = text.strip()
        daily_like_pending.pop(user_id, None)
        
        today_str = datetime.date.today().isoformat()
        if user['lastClaimDate'] != today_str:
            user['lastClaimDate'] = today_str
            user['dailyClaimsCount'] = 0

        current_count = user['dailyClaimsCount']
        
        if current_count == 0:
            cost_msg = "🎁 *1st Time Today: ABSOLUTELY FREE!* ✨"
        elif current_count in [1, 2]:
            if user['balance'] < 3:
                bot.send_message(user_id, "❌ *Low Balance!* Aapke wallet me Rs. 3 nahi hain. Pehle 💳 **Add Money (UPI)** se balance add karein.", parse_mode='Markdown')
                return
            user['balance'] -= 3
            cost_msg = f"💳 *Paid Like #{current_count}: Rs. 3 Deducted Successfully!* 💰"
        else:
            bot.send_message(user_id, "❌ Aap aaj ki 3 limits (1 Free + 2 Paid) poori kar chuke hain! Kal dobara try karein.", parse_mode='Markdown')
            return

        user['dailyClaimsCount'] += 1

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇮🇳 IND", callback_data=f"dl_ind_{uid}"),
            types.InlineKeyboardButton("🇧🇩 BD", callback_data=f"dl_bd_{uid}"),
            types.InlineKeyboardButton("🇮🇩 ID", callback_data=f"dl_id_{uid}"),
            types.InlineKeyboardButton("🇸🇬 SG", callback_data=f"dl_sg_{uid}")
        )
        bot.send_message(user_id, f"{cost_msg}\n🆔 UID Saved: `{uid}`\n\n👇 Apna Server / Region select karein:", parse_mode='Markdown', reply_markup=markup)
        return

    if text == '🎁 𝙳𝘢𝘪𝗹𝘺 𝙵𝚛𝚎e 𝙻i𝙆𝚎':
        if user_id == ADMIN_ID:
            daily_like_pending[user_id] = {'step': 'WAITING_FOR_UID'}
            bot.send_message(user_id, "👑 *Admin Panel:* Unlimited Free Likes Mode Active.\n\n✍️ Free Fire / Profile **UID** bhejein:", parse_mode='Markdown')
            return

        today_str = datetime.date.today().isoformat()
        if user['lastClaimDate'] != today_str:
            user['lastClaimDate'] = today_str
            user['dailyClaimsCount'] = 0

        used_count = user['dailyClaimsCount']
        if used_count >= 3:
            bot.send_message(user_id, "❌ Aapne aaj ke 3 attempts (1 Free + 2 Paid) use kar liye hain! Kal fir aana.", parse_mode='Markdown')
            return

        next_type = "Free (1st)" if used_count == 0 else f"Paid (Rs. 3) [{used_count}/2]"
        daily_like_pending[user_id] = {'step': 'WAITING_FOR_UID'}
        bot.send_message(
            user_id,
            f"🎁 *𝙳𝙰𝙸𝙻𝚈 𝙻𝙸𝙺𝙴 𝗦𝗬𝗦𝗧𝗘𝗠* ⚡\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• Aaj ka use: {used_count}/3 attempts\n"
            f"• Agla option: *{next_type}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"✍️ Apna Free Fire / Profile **UID** bhejein:",
            parse_mode='Markdown'
        )
        return

    if text == '👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝒍' and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("📢 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_add_channel'),
                   types.InlineKeyboardButton("❌ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_remove_channel'))
        markup.row(types.InlineKeyboardButton("📋 𝗩𝗶𝗲𝘄 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀", callback_data='admin_view_channels'),
                   types.InlineKeyboardButton("💰 𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", callback_data='admin_add_balance'))
        markup.row(types.InlineKeyboardButton("🎁 𝗖𝗿𝗲𝗮𝘁𝗲 𝗥𝗲𝗱𝗲𝗲𝗺", callback_data='admin_create_redeem'),
                   types.InlineKeyboardButton("⚡ 𝗔𝘂𝘁𝗼 𝗟𝗶𝗸𝗲 (5 PM)", callback_data='admin_auto_like'))
        markup.row(types.InlineKeyboardButton("📊 𝗩𝗶𝗲𝘄 𝗔𝘂𝘁𝗼 𝗟𝗶𝗸𝗲𝘀", callback_data='admin_view_auto'),
                   types.InlineKeyboardButton("🎁 𝗦𝗲𝘁 𝗥𝗲𝗳𝗲𝗿", callback_data='admin_set_refer'))
        markup.row(types.InlineKeyboardButton("✉️ 𝖯𝘳𝘰𝘤𝘦𝘴𝘴 𝘔𝘴𝘨 𝖲𝘦𝘯𝘥", callback_data='admin_send_msg'),
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

    if text == '💖 𝑩𝒖𝒚 𝑳𝒊𝒌𝒆 / 𝑷𝒍𝒂𝒏𝒔':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 𝑩𝒖𝒚 𝑹𝒔. 𝟔 𝑫𝒆𝒎𝒐 𝑷𝒍𝒂𝒏", callback_data='buy_demo'))
        markup.add(types.InlineKeyboardButton("🔥 𝑩𝒖𝒚 𝑹𝒔. 𝟓𝟗 𝑷𝒍𝒂𝒏 (15 Days)", callback_data='buy_59'))
        markup.add(types.InlineKeyboardButton("🔥 𝑩𝒖𝒚 𝑹𝒔. 𝟏𝟏𝟎 𝑷𝒍𝒂𝒏 (30 Days)", callback_data='buy_110'))
        markup.add(types.InlineKeyboardButton("🔓 10 Refs Unlock Plan (7 Days)", callback_data='buy_ref_unlock'))
        bot.send_message(
            user_id,
            "💖 *𝑺𝑬𝑳𝑬𝑪𝑻 𝑳𝑰𝑲𝑬 𝑷𝑳𝑨𝑵𝚂* 🔥\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "0️⃣ *𝑹𝒔. 𝟔 𝑫𝒆𝒎𝒐 𝑷𝒍𝒂𝒏*\n   • 220 Likes | 1 Day me 1 Bar ⚡\n\n"
            "1️⃣ *𝑹𝒔. 𝟓𝟗 𝑷𝒍𝒂𝒏 (15 Days)*\n   • 220 Likes Daily for 15 Days ✨\n\n"
            "2️⃣ *𝑹𝒔. 𝟏𝟏𝟎 𝑷𝒍𝒂𝒏 (30 Days)*\n   • 220 Likes Daily for 30 Days 🌟\n\n"
            "3️⃣ *10 Refs Unlock Plan*\n   • 7 Days 220 Likes Daily (Free on 10 Referrals) 🔓\n"
            "━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    if text == '🛒 𝑪𝑪 𝑺𝒕𝒐𝒓𝒆':
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

    if text == '💼 𝗠𝘆 𝑷rо𝒇𝒊𝒍𝒆':
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

    if text == '🎁 𝑹𝒆𝒇𝒆𝒓 & 𝑬𝒂𝒓𝒏':
        username = bot.get_me().username
        link = f"https://t.me/{username}?start={user_id}"
        user = get_user(user_id)
        bot.send_message(user_id, f"🎁 *𝑹𝑬𝑭𝑬𝑹 & 𝑬𝑨𝑹𝑵* 🌟\n\nHar join par milenge **Rs. {bot_settings['referralBonus']}**! ✨\n👥 Aapke Total Referrals: {user['referrals']}/10\n\n🔗 *Link:*\n`{link}`", parse_mode='Markdown')
        return

    if text == '💬 𝐇𝐞𝐥𝐩 & 𝐒𝐮𝐩𝐩𝐨𝐫𝐭':
        username = f"@{message.from_user.username}" if message.from_user.username else 'None'
        bot.send_message(
            user_id,
            f"💬 *𝐂𝐔𝐒𝐓𝐎𝐌𝐄𝐑 𝐇𝐄𝐋𝐏 & 𝐒𝐔𝐏𝐏𝐎𝐑𝐓* 📞\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Aapki User ID:* `{user_id}`\n"
            f"🔗 *Username:* {username}\n"
            f"⚠️ *Problem Details:* Koi bhi problem ho toh seedhe Admin ko message karein!\n"
            f"👉 *Admin Support ID:* @Xenon_ask9\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    # Admin State Handlers
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
        if state == 'SET_REFER':
            try:
                new_bonus = int(text.strip())
                if new_bonus < 0:
                    raise ValueError()
                bot_settings['referralBonus'] = new_bonus
                pending_state.pop(user_id, None)
                bot.send_message(user_id, f"✅ Referral bonus successfully updated to: Rs. {bot_settings['referralBonus']}")
            except ValueError:
                bot.send_message(user_id, "❌ Sahi number me refer bonus amount daalein:")
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

        if state.get('step') == 'AUTO_LIKE_UID':
            state['auto_uid'] = text.strip()
            state['step'] = 'AUTO_LIKE_REGION'
            bot.send_message(user_id, "🌐 Ab region/server name bhejein (jaise `ind`, `bd`, `id`, `sg`):")
            return
        if state.get('step') == 'AUTO_LIKE_REGION':
            region = text.strip().lower()
            uid = state['auto_uid']
            pending_state.pop(user_id, None)
            
            auto_like_jobs[uid] = {
                'region': region,
                'count_today': 0,
                'last_date': str(datetime.date.today())
            }
            bot.send_message(user_id, f"✅ Auto Like successfully set!\n🆔 UID: `{uid}`\n🌐 Region: `{region.upper()}`\n⏰ Daily 5:00 PM par likes jayenge.", parse_mode='Markdown')
            return

    if user_id == ADMIN_ID and isinstance(state, dict) and state.get('step') == 'ADD_BAL_UID':
        try:
            target_uid = int(text)
            pending_state[user_id] = {'step': 'ADD_BAL_AMOUNT', 'targetUid': target_uid}
            bot.send_message(user_id, "✍️ Kitna balance add karna hai? Amount number me bhejein:")
        except ValueError:
            bot.send_message(user_id, "❌ Sahi User ID number me daalein:")
        return

    if user_id == ADMIN_ID and isinstance(state, dict) and state.get('step') == 'ADD_BAL_AMOUNT':
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

    if user_id == ADMIN_ID and isinstance(state, dict) and state.get('step') == 'SEND_MSG_UID':
        state['targetId'] = int(text)
        state['step'] = 'SEND_MSG_TEXT'
        bot.send_message(user_id, "✍️ Ab woh message type karein jo is user ko bhejna hai:")
        return

    if user_id == ADMIN_ID and isinstance(state, dict) and state.get('step') == 'SEND_MSG_TEXT':
        target_id = state['targetId']
        msg_text = text
        pending_state.pop(user_id, None)
        try:
            bot.send_message(target_id, f"💬 *𝑨𝒅𝒎𝒊𝒏 𝑴𝒆𝒔𝒔𝒂𝒈𝒆:*\n\n{msg_text}", parse_mode='Markdown')
            bot.send_message(user_id, "✅ Message successfully bhej diya gaya hai!")
        except Exception:
            bot.send_message(user_id, "❌ User ko message nahi bhej paye!")
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
        bot.send_message(user_id, f"💳 UPI ID: `{bot_settings['upiId']}`\n💰 Amount: Rs. {amount}\n\n⏳ 12-digit UTR/Txn ID bhejein:", parse_mode='Markdown')
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
        time.sleep(1.5)
        try:
            bot.edit_message_text("🔄 *𝑪𝒐𝒏𝒏𝒆𝒄𝒕𝒊𝒏𝒈 𝒕𝒐 𝑺𝒆𝒓𝒗𝒆𝒓...* [🔄]", user_id, load_msg.message_id, parse_mode='Markdown')
        except Exception:
            pass
        time.sleep(1.5)
        try:
            bot.edit_message_text("⚡ *𝑽𝒆𝒓𝒊𝒇𝒚𝒊𝒏𝒈 𝑼𝑰𝑫 & 𝑳𝒊𝒌𝒆𝒔...* [⚡]", user_id, load_msg.message_id, parse_mode='Markdown')
        except Exception:
            pass
        time.sleep(2.0)

        success_text = (
            f"✅ *𝑶𝑹𝑫𝑬𝑹 𝑷𝑹𝑶𝑪𝑬𝑺𝑺𝑬𝑫 𝑺𝑼𝑪𝑪𝑬𝑺𝑺𝑭𝑼𝑳𝑳𝒀!* ✨\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Plan: {order['plan']}\n"
            f"🆔 UID: `{target_uid}`\n"
            f"⏰ Expiry: {user['planExpiry']}\n"
            f"💰 Remaining Balance: Rs. {user['balance']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛠️ *Koi problem ho toh admin (@Xenon_ask9) ko message karna.*"
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
        parts = data.split('_')
        region = parts[1]
        uid = parts[2]
        
        bot.answer_callback_query(call.id, f"Connecting to API for {region.upper()}...")
        load_msg = bot.send_message(call.message.chat.id, "⏳ *[ 1/2 ] Connecting to API & Sending Likes...*", parse_mode='Markdown')
        
        api_url = f"https://auto-like-eight.vercel.app/like?uid={uid}&server_name={region}&key=JSJDN"
        try:
            res = requests.get(api_url, timeout=15)
            res_data = res.json()
            
            text_out = f"✅ *LIKE API RESPONSE SUCCESS!* 🎉\n━━━━━━━━━━━━━━━━━━━\n"
            if isinstance(res_data, dict):
                for k, v in res_data.items():
                    text_out += f"• *{k.capitalize()}*: `{v}`\n"
            else:
                text_out += f"Response: `{res_data}`\n"
            text_out += f"━━━━━━━━━━━━━━━━━━━\n🌐 Server: `{region.upper()}`\n🆔 UID: `{uid}`"
            
            bot.edit_message_text(text_out, call.message.chat.id, load_msg.message_id, parse_mode='Markdown')
        except Exception as e:
            bot.edit_message_text(f"❌ API Error / Response failed:\n`{str(e)}`", call.message.chat.id, load_msg.message_id, parse_mode='Markdown')
        return

    if data == 'admin_create_redeem':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'CREATE_REDEEM_CODE'}
            bot.send_message(user_id, "🎁 Naya **Redeem Code** text/name bhejein (jaise `FREE10`):")
    elif data == 'admin_auto_like':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'AUTO_LIKE_UID'}
            bot.send_message(user_id, "🤖 Auto Like ke liye target **UID** bhejein:")
    elif data == 'admin_view_auto':
        if user_id == ADMIN_ID:
            if not auto_like_jobs:
                bot.answer_callback_query(call.id, "⚠️ Koi active auto like job set nahi hai!", show_alert=True)
            else:
                text_auto = "📊 *ACTIVE AUTO LIKE JOBS (5 PM)* ⚡\n━━━━━━━━━━━━━━━━━━━\n"
                for uid, info in auto_like_jobs.items():
                    text_auto += f"🆔 UID: `{uid}`\n🌐 Region: `{info['region'].upper()}`\n📈 Today Sent Likes: `{info['count_today']}`\n📅 Date: `{info['last_date']}`\n━━━━━━━━━━━━━━━━━━━\n"
                bot.send_message(user_id, text_auto, parse_mode='Markdown')
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
            pending_state[user_id] = 'SET_REFER'
            bot.send_message(user_id, "🎁 Naya referral bonus amount (Rs.) number me bhejein:")
    elif data == 'admin_broadcast':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'BROADCAST_MSG'
            bot.send_message(user_id, "📢 Broadcast message bhejein:")
    elif data == 'admin_send_msg':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'SEND_MSG_UID'}
            bot.send_message(user_id, "🆔 Us user ki Telegram Numeric ID bhejein jisko message bhejna hai:")
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
        now = time.time()
        one_day = 24 * 60 * 60
        if now - user['lastDemoClaim'] < one_day:
            hours_left = int((one_day - (now - user['lastDemoClaim'])) / 3600) + 1
            bot.answer_callback_query(call.id, f"Aap ye Demo Plan 1 din me sirf 1 bar le sakte hain! {hours_left} ghante bache hain.", show_alert=True)
            return
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
            "⚠️ *𝑪𝑪 𝑺𝑻𝑶𝑹𝑬 𝑹𝑼𝑳𝑬𝑺 & 𝑰𝑵𝑺𝑻𝑹𝑼𝑪𝑻𝑰𝑶𝑵𝑺* 🛒\n"
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
            "⚠️ *𝑪𝑪 𝑺𝑻𝑶𝑹𝑬 𝑹𝑼𝑳𝑬𝑺 & 𝑰𝑵𝑺𝑻𝑹𝑼𝑪𝑻𝑰𝑶𝑵𝑺* 🛒\n"
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
                f"✅ *𝑪𝑪 𝑺𝑻𝑶𝑹𝑬 𝑶𝑹𝑫𝑬𝑹 𝑺𝑼𝑪𝑪𝑬𝑺𝑺𝑭𝑼𝑳𝑳𝒀!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: Rs. 100 CC Plan (2k)\n"
                f"💼 Remaining Balance: Rs. {user['balance']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *10 minute me card yahin bot pe mil jayega!* 🚀\n"
                f"🛠️ *Koi problem ho toh admin (@Xenon_ask9) ko message karna.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')

            try:
                bot.send_message(
                    ADMIN_ID,
                    f"🚨 *𝑵𝒂𝒚𝒂 𝑪𝑪 𝑺𝒕𝒐𝒓𝒆 𝑷𝒖𝒓𝒄𝒉𝒂𝒔𝒆!* 🛒\n\n"
                    f"👤 *Name:* {call.from_user.first_name}\n"
                    f"🆔 *User ID:* `{user_id}`\n"
                    f"🔗 *Username:* @{call.from_user.username or 'None'}\n"
                    f"📦 *Plan:* Rs. 100 CC Plan (2k)\n"
                    f"💰 *Price Paid:* Rs. 100",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ Low Balance! Rs. 100 chahiye.", show_alert=True)
    elif data == 'confirm_cc_199':
        user = get_user(user_id)
        if user['balance'] >= 199:
            user['balance'] -= 199
            
            success_text = (
                f"✅ *𝑪𝑪 𝑺𝑻𝑶𝑹𝑬 𝑶𝑹𝑫𝑬𝑹 𝑺𝑼𝑪𝑪𝑬𝑺𝑺𝑭𝑼𝑳𝑳𝒀!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: Rs. 199 CC Plan (5k)\n"
                f"💼 Remaining Balance: Rs. {user['balance']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *10 minute me card yahin bot pe mil jayega!* 🚀\n"
                f"🛠️ *Koi problem ho toh admin (@Xenon_ask9) ko message karna.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')

            try:
                bot.send_message(
                    ADMIN_ID,
                    f"🚨 *𝑵𝒂𝒚𝒂 𝑪𝑪 𝑺𝒕𝒐𝒓𝒆 𝑷𝒖𝒓𝒄𝒉𝒂𝒔𝒆!* 🛒\n\n"
                    f"👤 *Name:* {call.from_user.first_name}\n"
                    f"🆔 *User ID:* `{user_id}`\n"
                    f"🔗 *Username:* @{call.from_user.username or 'None'}\n"
                    f"📦 *Plan:* Rs. 199 CC Plan (5k)\n"
                    f"💰 *Price Paid:* Rs. 199",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ Low Balance! Rs. 199 chahiye.", show_alert=True)

# Background Thread for 5:00 PM Daily Auto Like Trigger
def auto_like_scheduler():
    while True:
        now = datetime.datetime.now()
        if now.hour == 17 and now.minute == 0:
            today_str = str(datetime.date.today())
            for uid, info in auto_like_jobs.items():
                if info['last_date'] != today_str:
                    info['count_today'] = 0
                    info['last_date'] = today_str
                
                api_url = f"https://auto-like-eight.vercel.app/like?uid={uid}&server_name={info['region']}&key=JSJDN"
                try:
                    res = requests.get(api_url, timeout=15)
                    res_data = res.json()
                    info['count_today'] += 1
                    
                    bot.send_message(
                        ADMIN_ID,
                        f"🤖 *AUTO LIKE 5 PM TRIGGERED!* ⚡\n━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 UID: `{uid}`\n🌐 Region: `{info['region'].upper()}`\n"
                        f"📈 Total Sent Today: `{info['count_today']}`\n"
                        f"📦 Response: `{res_data}`",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    bot.send_message(
                        ADMIN_ID,
                        f"❌ Auto Like API Error for UID `{uid}`:\n`{str(e)}`",
                        parse_mode='Markdown'
                    )
            time.sleep(60)
        else:
            time.sleep(30)

if __name__ == '__main__':
    t = threading.Thread(target=auto_like_scheduler)
    t.daemon = True
    t.start()
    
    print("Python Telegram Bot is running with Fixes...")
    bot.infinity_polling()

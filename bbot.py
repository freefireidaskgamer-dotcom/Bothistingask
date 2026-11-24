# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import datetime
import requests
import threading
import html
import os
import random
import string

TOKEN = os.getenv('BOT_TOKEN', '9031674115:AAHpSd-U31B9GTgY4lyAstorXa_OxSEEUhY').strip()
if not TOKEN:
    raise RuntimeError(
        "Set BOT_TOKEN environment variable with a NEW BotFather token."
    )

bot = telebot.TeleBot(TOKEN)

LIKE_API_URL = os.getenv('LIKE_API_URL', 'https://ijapi.vercel.app/like').strip()

ADMIN_ID = 7161571409
ADMIN_USERNAME = "@xenonask9"

IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

GIF_FILES = {
    'welcome': 'gifs/welcome_pulse.gif',
    'plan': 'gifs/plan_badge.gif',
    'guild': 'gifs/guild_glory.gif',
    'report': 'gifs/daily_report.gif',
}

bot_settings = {
    'requiredChannels': ['@eraningwithask', '@eraningwithask9', '@askkkk2', '@botlikeproof'],
    'referralBonus': 5,
    'upiId': 'sima6241@ptaxis',
    'customAutoRunTime': None,  # Optional HH:MM (24-hr IST) set by Admin for extra AutoLikes run
}

users = {}
pending_deposits = {}
pending_state = {}
pending_uid = {}
pending_guild_order = {}
guild_orders = {}
redeem_codes = {}
plan_progress = {}  # Active/historical plans tracking by user_id
scheduler_lock = threading.Lock()

AUTO_REACTIONS = ["♥️", "😂", "👍", "🥳", "💋", "❤️", "😍"]


def now_ist():
    return datetime.datetime.now(IST_TZ).replace(tzinfo=None)


def send_gif_if_exists(chat_id, gif_key, caption=None, reply_markup=None):
    path = GIF_FILES.get(gif_key)
    if path and os.path.exists(path):
        try:
            with open(path, 'rb') as gf:
                bot.send_animation(
                    chat_id,
                    gf,
                    caption=caption,
                    parse_mode='Markdown' if caption else None,
                    reply_markup=reply_markup
                )
            return True
        except Exception:
            pass
    if caption:
        bot.send_message(chat_id, caption, parse_mode='Markdown', reply_markup=reply_markup)
    return False


def generate_unique_10_digit_alnum_id():
    while True:
        letters = random.choices(string.ascii_uppercase, k=4)
        digits = random.choices(string.digits, k=6)
        combined = letters + digits
        random.shuffle(combined)
        oid = "".join(combined)
        if oid not in guild_orders:
            return oid


def send_auto_reaction(message):
    if not message or not hasattr(message, "chat") or not hasattr(message, "message_id"):
        return
    # Direct TeleBot / Telegram Bot API setMessageReaction call with fallback emojis
    candidates = ["❤️", "👍", "😂", "🥳", "😍", "🔥", "🎉", "💯"]
    random.shuffle(candidates)
    for emoji in candidates:
        try:
            bot.set_message_reaction(
                message.chat.id,
                message.message_id,
                [types.ReactionTypeEmoji(emoji)],
                is_big=False,
            )
            return
        except Exception:
            try:
                telebot.apihelper._get_req_session().post(
                    f"https://api.telegram.org/bot{TOKEN}/setMessageReaction",
                    json={
                        "chat_id": message.chat.id,
                        "message_id": message.message_id,
                        "reaction": [{"type": "emoji", "emoji": emoji}],
                        "is_big": False,
                    },
                    timeout=10,
                )
                return
            except Exception:
                continue


GUILD_INFO_API_URL = os.getenv('GUILD_INFO_API_URL', 'https://infoask8-bi3j.vercel.app/info').strip()


def _deep_find_guild_dict(obj):
    if isinstance(obj, dict):
        keys_l = {str(k).lower(): v for k, v in obj.items()}
        if any(k in keys_l for k in ("guildname", "guild_name", "clanname", "clan_name", "guildid", "guild_id", "clanid", "clan_id")):
            return obj
        for sub_key in ("guild", "guildinfo", "guild_info", "guilddetails", "guild_details", "clan", "claninfo", "clan_info", "data", "result", "info"):
            if sub_key in keys_l and isinstance(keys_l[sub_key], (dict, list)):
                found = _deep_find_guild_dict(keys_l[sub_key])
                if found:
                    return found
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = _deep_find_guild_dict(v)
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_guild_dict(item)
            if found:
                return found
    return None


def fetch_guild_details_by_game_uid(game_uid, region="ind", timeout=25):
    try:
        resp = requests.get(
            GUILD_INFO_API_URL,
            params={"uid": str(game_uid).strip(), "region": str(region).strip().lower() or "ind"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        raise RuntimeError("Game UID galat hai ya Guild Info API response nahi de rahi.")

    g_dict = _deep_find_guild_dict(data) or (data if isinstance(data, dict) else {})
    guild_name = _find_value(g_dict, ["GuildName", "guild_name", "guildName", "ClanName", "clan_name", "name"])
    guild_id = _find_value(g_dict, ["GuildID", "guild_id", "guildId", "ClanID", "clan_id", "id"])
    guild_level = _find_value(g_dict, ["GuildLevel", "guild_level", "guildLevel", "ClanLevel", "clan_level", "level"])
    guild_leader = _find_value(g_dict, ["GuildLeader", "guild_leader", "leaderName", "leader_name", "Leader", "captain"])
    guild_capacity = _find_value(g_dict, ["GuildCapacity", "guild_capacity", "capacity", "maxMembers", "max_members"])
    guild_members = _find_value(g_dict, ["GuildMember", "guild_member", "GuildMembers", "guild_members", "members", "memberCount", "member_count"])
    guild_glory = _find_value(g_dict, ["GuildGlory", "guild_glory", "glory", "points"])

    if not guild_name and not guild_id and isinstance(data, dict):
        guild_name = _find_value(data, ["GuildName", "guild_name", "ClanName", "clan_name"])
        guild_id = _find_value(data, ["GuildID", "guild_id", "ClanID", "clan_id"])

    if not guild_name and not guild_id:
        raise RuntimeError("Is Game UID ki guild details nahi mili.")

    lines = []
    if guild_name is not None:
        lines.append(f"🏰 *𝗚𝘂𝗶𝗹𝗱 𝗡𝗮𝗺𝗲:* `{guild_name}`")
    if guild_id is not None:
        lines.append(f"🆔 *𝗚𝘂𝗶𝗹𝗱 𝗜𝗗:* `{guild_id}`")
    if guild_level is not None:
        lines.append(f"⭐ *𝗚𝘂𝗶𝗹𝗱 𝗟𝗲𝘃𝗲𝗹:* `{guild_level}`")
    if guild_leader is not None:
        lines.append(f"👑 *𝗚𝘂𝗶𝗹𝗱 𝗟𝗲𝗮𝗱𝗲𝗿:* `{guild_leader}`")
    if guild_members is not None or guild_capacity is not None:
        m_txt = f"{guild_members}/{guild_capacity}" if (guild_members is not None and guild_capacity is not None) else str(guild_members if guild_members is not None else guild_capacity)
        lines.append(f"👥 *𝗠𝗲𝗺𝗯𝗲𝗿𝘀:* `{m_txt}`")
    if guild_glory is not None:
        lines.append(f"✨ *𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆:* `{guild_glory}`")

    formatted_block = "\n".join(lines)
    return {
        "guild_name": str(guild_name) if guild_name is not None else "N/A",
        "guild_id": str(guild_id) if guild_id is not None else "N/A",
        "formatted_block": formatted_block,
    }


def get_user(user_id):
    user_id = int(user_id)
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'referrals': 0,
            'activePlan': 'None',
            'planExpiry': 'N/A',
            'lastDemoClaim': 0,
            'lastDailyBonusDate': None,
            'refPlanClaimed': False,
            'referred': False,
            'referredBy': None,
            'referralBonusAwarded': 0,
            'referralPenaltyApplied': False,
            'notifiedAdmin': False,
            'username': 'None',
            'history': []
        }
    else:
        users[user_id].setdefault('lastDailyBonusDate', None)
        users[user_id].setdefault('referredBy', None)
        users[user_id].setdefault('referralBonusAwarded', 0)
        users[user_id].setdefault('referralPenaltyApplied', False)
        users[user_id].setdefault('username', 'None')
        users[user_id].setdefault('history', [])
    return users[user_id]


def call_like_api(uid, region="ind", timeout=25):
    url = LIKE_API_URL.strip()
    if not url:
        raise ValueError("API URL set nahi hai ya UID galat hai.")
    try:
        response = requests.get(
            url,
            params={"uid": str(uid).strip(), "region": str(region).strip().lower() or "ind"},
            timeout=timeout
        )
        response.raise_for_status()
    except requests.RequestException:
        raise RuntimeError("UID galat hai ya API response nahi de rahi.")

    try:
        data = response.json()
    except ValueError:
        data = {"raw_response": response.text.strip()}

    if not isinstance(data, dict):
        return {"response": data}

    err_val = str(_find_value(data, ["error", "err", "message", "msg"]) or "").lower()
    if any(w in err_val for w in ["not found", "invalid", "error", "wrong", "failed", "ban"]):
        raise RuntimeError("UID galat hai ya player nahi mila.")

    return data


def _find_value(data, keys):
    if not isinstance(data, dict):
        return None
    lower_map = {str(k).lower(): v for k, v in data.items()}
    for k in keys:
        kl = k.lower()
        if kl in lower_map and lower_map[kl] not in (None, ""):
            return lower_map[kl]
    return None


def _to_int(val):
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip()
        if s.lstrip("-").isdigit():
            return int(s)
        return int(float(s))
    except Exception:
        return None


def parse_like_api_metrics(uid, region, data):
    nickname = _find_value(data, ["PlayerNickname", "nickname", "name", "username"]) or "Unknown"
    level = _find_value(data, ["Level", "level", "lvl"]) or "N/A"
    res_uid = _find_value(data, ["UID", "uid"]) or str(uid)
    res_region = _find_value(data, ["Region", "region"]) or str(region).upper()

    given_raw = _find_value(data, ["LikesGivenByAPI", "likes_given", "likesGiven", "added", "likes_added"])
    before_raw = _find_value(data, ["LikesbeforeCommand", "likes_before", "before_likes", "previous_likes", "likesBefore"])
    after_raw = _find_value(data, ["LikesafterCommand", "likes_after", "after_likes", "final_likes", "likesAfter", "likes"])

    given_int = _to_int(given_raw)
    before_int = _to_int(before_raw)
    after_int = _to_int(after_raw)

    if given_int is None and before_int is not None and after_int is not None:
        given_int = max(0, after_int - before_int)
    if after_int is None and before_int is not None and given_int is not None:
        after_int = before_int + given_int
    if before_int is None and after_int is not None and given_int is not None:
        before_int = max(0, after_int - given_int)

    if given_int is None:
        given_int = 0

    return {
        "nickname": str(nickname),
        "level": str(level),
        "uid": str(res_uid),
        "region": str(res_region).upper(),
        "given": given_int,
        "before": before_int,
        "after": after_int,
        "raw": data
    }


def format_styled_id_info(uid, region, data):
    m = parse_like_api_metrics(uid, region, data)
    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━╮",
        "   🎮 𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗜𝗗 𝗜𝗡𝗙𝗢",
        "╰━━━━━━━━━━━━━━━━━━━━╯",
        "",
        f"👤 𝗡𝗮𝗺𝗲 : `{m['nickname']}`",
        f"❤️ 𝗟𝗶𝗸𝗲𝘀 : `{m['after'] if m['after'] is not None else 'N/A'}`",
        f"⭐ 𝗟𝗲𝘃𝗲𝗹 : `{m['level']}`",
        f"🆔 𝗨𝗜𝗗 : `{m['uid']}`",
        f"🌍 𝗥𝗲𝗴𝗶𝗼𝗻 : `{m['region']}`",
        "",
        "━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)


def format_styled_sent_like(uid, region, data):
    m = parse_like_api_metrics(uid, region, data)
    before_str = f"{m['before']:,}" if m['before'] is not None else "N/A"
    after_str = f"{m['after']:,}" if m['after'] is not None else "N/A"
    given_str = f"+{m['given']:,}" if m['given'] > 0 else "0"
    status_line = "✅ 𝗟𝗜𝗞𝗘𝗦 𝗦𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!" if m['given'] > 0 else "⚠️ 𝗡𝗢 𝗡𝗘𝗪 𝗟𝗜𝗞𝗘𝗦 𝗔𝗗𝗗𝗘𝗗 (𝗠𝗔𝗫 / 𝗖𝗢𝗢𝗟𝗗𝗢𝗪𝗡)"

    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━╮",
        "   ❤️ 𝗦𝗘𝗡𝗧 𝗟𝗜𝗞𝗘 𝗥𝗘𝗣𝗢𝗥𝗧",
        "╰━━━━━━━━━━━━━━━━━━━━╯",
        "",
        f"👤 𝗡𝗮𝗺𝗲 : `{m['nickname']}`",
        f"🆔 𝗨𝗜𝗗 : `{m['uid']}`",
        f"🌍 𝗥𝗲𝗴𝗶𝗼𝗻 : `{m['region']}`",
        f"⭐ 𝗟𝗲𝘃𝗲𝗹 : `{m['level']}`",
        "",
        f"🎁 𝗕𝗲𝗳𝗼𝗿𝗲 𝗟𝗶𝗸𝗲𝘀 : `{before_str}`",
        f"➕ 𝗟𝗶𝗸𝗲𝘀 𝗚𝗶𝘃𝗲𝗻 : `{given_str}`",
        f"💭 𝗔𝗳𝘁𝗲𝗿 𝗟𝗶𝗸𝗲𝘀 : `{after_str}`",
        "",
        "━━━━━━━━━━━━━━━━━━━",
        status_line,
        "━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)


def get_left_channels(user_id):
    left = []
    for channel in bot_settings['requiredChannels']:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                left.append(channel)
        except Exception:
            left.append(channel)
    return left


def check_membership(user_id):
    return len(get_left_channels(user_id)) == 0


def check_and_apply_referral_leave_penalty(referred_user_id):
    referred_user_id = int(referred_user_id)
    ref_usr = get_user(referred_user_id)
    referrer_id = ref_usr.get('referredBy')
    if not referrer_id:
        return False
    if ref_usr.get('referralPenaltyApplied'):
        return False

    left_channels = get_left_channels(referred_user_id)
    if len(left_channels) >= 2:
        ref_usr['referralPenaltyApplied'] = True
        referrer = get_user(referrer_id)
        cut_amount = int(ref_usr.get('referralBonusAwarded') or bot_settings['referralBonus'])
        referrer['balance'] = max(0, int(referrer.get('balance', 0)) - cut_amount)
        referrer['referrals'] = max(0, int(referrer.get('referrals', 0)) - 1)

        ref_display = f"@{ref_usr['username']}" if ref_usr.get('username') and ref_usr['username'] != 'None' else f"`{referred_user_id}`"
        try:
            bot.send_message(
                referrer_id,
                f"⚠️ *𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗕𝗼𝗻𝘂𝘀 𝗖𝘂𝘁 𝗛𝗼 𝗚𝗮𝘆𝗮!* ✂️\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *𝗥𝗲𝗳𝗲𝗿𝗿𝗲𝗱 𝗨𝘀𝗲𝗿:* {ref_display} (`{referred_user_id}`)\n"
                f"📢 *𝗟𝗲𝗳𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:* `{len(left_channels)}` ({', '.join(left_channels)})\n"
                f"💸 *𝗖𝘂𝘁 𝗔𝗺𝗼𝘂𝗻𝘁:* `Rs. {cut_amount}`\n"
                f"💼 *𝗡𝗲𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲:* `Rs. {referrer['balance']}`\n"
                f"━━━━━━━━━━━━━━━━━━━",
                parse_mode='Markdown'
            )
        except Exception:
            pass
        return True
    return False


def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀', '🏰 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆')
    markup.row('🔍 𝗜𝗗 𝗜𝗻𝗳𝗼', '📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻')
    markup.row('🎁 𝗗𝗮𝗶𝗹𝘆 𝗕𝗼𝗻𝘂𝘀', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)')
    markup.row('🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲', '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲')
    markup.row('🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻', '👤 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮')
    markup.row('📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻')
    if user_id == ADMIN_ID:
        markup.row('👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹')
    return markup


def activate_user_plan(
    cust_id,
    target_uid,
    plan_name,
    total_likes_target,
    days=None,
    daily_cap=None,
    price_paid=0,
    username='None',
    region='ind',
    send_initial_like=True,
    now_dt=None,
    is_demo=False,
    fetch_uid_info_only=False
):
    cust_id = int(cust_id)
    total_likes_target = max(1, int(total_likes_target))
    now = now_dt or now_ist()

    if days is not None:
        expiry = now + datetime.timedelta(days=max(1, int(days)))
    else:
        est_days = max(7, (total_likes_target // 200) + 15)
        expiry = now + datetime.timedelta(days=est_days)

    usr = get_user(cust_id)
    usr['activePlan'] = plan_name
    usr['planExpiry'] = expiry.strftime('%Y-%m-%d %H:%M:%S')

    delivered_real = 0
    player_name = "Unknown"
    player_level = "N/A"
    player_region = str(region).upper()
    likes_before_val = None
    likes_after_val = None
    api_status_text = "Pending"
    refunded_amount = 0

    try:
        api_data = call_like_api(target_uid, region=region, timeout=25)
        m = parse_like_api_metrics(target_uid, region, api_data)
        player_name = m['nickname']
        player_level = m['level']
        player_region = m['region']
        likes_before_val = m['before']
        likes_after_val = m['after']

        if send_initial_like and not fetch_uid_info_only:
            real_given = max(0, int(m['given']))
            delivered_real = min(total_likes_target, real_given)
            api_status_text = f"+{real_given} Real Likes"

            if is_demo and real_given < 50 and price_paid > 0:
                usr['balance'] += price_paid
                refunded_amount = price_paid
                api_status_text = f"+{real_given} Likes (<50) -> Rs. {refunded_amount} Refunded"
        else:
            api_status_text = "UID Verified"
    except Exception:
        raise RuntimeError("UID galat hai ya API response nahi de rahi.")

    remaining_likes = max(0, total_likes_target - delivered_real)
    today_str = now.strftime('%Y-%m-%d')

    if delivered_real > 0:
        usr['history'].append({'date': today_str, 'delivered': delivered_real})
        if len(usr['history']) > 5:
            usr['history'].pop(0)

    is_completed = remaining_likes <= 0
    if is_completed:
        usr['activePlan'] = 'Completed'

    plan_progress[cust_id] = {
        'uid': str(target_uid),
        'region': player_region,
        'plan': plan_name,
        'days': int(days) if days is not None else None,
        'daily_cap': int(daily_cap) if daily_cap is not None else None,
        'total_likes': total_likes_target,
        'delivered_total': delivered_real,
        'start_date': now,
        'expiry': expiry,
        'last_fixed_run_date': today_str if (send_initial_like and not fetch_uid_info_only) else None,
        'last_custom_run_key': None,
        'player_name': player_name,
        'player_level': player_level,
        'likes_before': likes_before_val,
        'likes_after': likes_after_val,
        'telegram_id': cust_id,
        'username': username or 'None',
        'price_paid': price_paid,
        'status': 'Completed' if is_completed else 'Active'
    }

    return {
        'expiry': expiry,
        'total_likes': total_likes_target,
        'delivered_real': delivered_real,
        'remaining_likes': remaining_likes,
        'api_status_text': api_status_text,
        'player_name': player_name,
        'player_level': player_level,
        'player_region': player_region,
        'likes_before': likes_before_val,
        'likes_after': likes_after_val,
        'completed': is_completed,
        'refunded_amount': refunded_amount
    }


def cancel_user_plan(target_user_id):
    target_user_id = int(target_user_id)
    removed_plan = plan_progress.pop(target_user_id, None)
    usr = get_user(target_user_id)
    prev_plan_name = usr.get('activePlan', 'None')
    usr['activePlan'] = 'Cancelled'
    usr['planExpiry'] = 'Cancelled'
    if removed_plan and removed_plan.get('plan'):
        prev_plan_name = removed_plan['plan']
    return {
        'removed': removed_plan is not None,
        'plan_name': prev_plan_name,
        'uid': removed_plan.get('uid', 'N/A') if removed_plan else 'N/A'
    }


@bot.message_handler(commands=['start'])
def start_command(message):
    send_auto_reaction(message)
    user_id = message.from_user.id
    user = get_user(user_id)
    if message.from_user.username:
        user['username'] = message.from_user.username

    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        try:
            referrer_id = int(payload)
            if referrer_id in users and not user['referred'] and referrer_id != user_id:
                user['referred'] = True
                user['referredBy'] = referrer_id
                bonus_val = int(bot_settings['referralBonus'])
                user['referralBonusAwarded'] = bonus_val
                referrer = get_user(referrer_id)
                referrer['referrals'] += 1
                referrer['balance'] += bonus_val
                bot.send_message(
                    referrer_id,
                    f"🎉 *𝗡𝗮𝘆𝗮 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗠𝗶𝗹𝗮!* ✨\n\n💰 *Bonus Added:* Rs. {bonus_val}",
                    parse_mode='Markdown'
                )
        except ValueError:
            pass

    if user_id != ADMIN_ID and not check_membership(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in bot_settings['requiredChannels']:
            markup.add(types.InlineKeyboardButton(f"📢 𝗝𝗼𝗶𝗻 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 𝗠𝗮𝗶𝗻 𝗖𝗵𝗲𝗰𝗸 𝗞𝗮𝗿 𝗟𝗶𝘆𝗮", callback_data='verify_join'))
        bot.send_message(
            user_id,
            "⚠️ *𝗣𝗲𝗵𝗹𝗲 𝗛𝗮𝗺𝗮𝗿𝗲 𝗦𝗮𝗯𝗵𝗶 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗝𝗼𝗶𝗻 𝗞𝗮𝗿𝗲𝗶𝗻!* 📢\n\n𝗕𝗼𝘁 𝘂𝘀𝗲 𝗸𝗮𝗿𝗻𝗲 𝗸𝗲 𝗹𝗶𝘆𝗲 𝘀𝗮𝗯𝗵𝗶 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗷𝗼𝗶𝗻 𝗸𝗮𝗿𝗻𝗮 𝘇𝗮𝗿𝗼𝗼𝗿𝗶 𝗵𝗮𝗶.",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    send_dashboard(message, user_id)


@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join_callback(call):
    user_id = call.from_user.id
    if call.from_user.username:
        get_user(user_id)['username'] = call.from_user.username

    if check_membership(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_dashboard(call.message, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ 𝗔𝗮𝗽𝗻𝗲 𝗮𝗯𝗵𝗶 𝘁𝗮𝗸 𝘀𝗮𝗯𝗵𝗶 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗷𝗼𝗶𝗻 𝗡𝗮𝗵𝗶 𝗞𝗶𝘆𝗮!", show_alert=True)


def send_dashboard(message, user_id):
    user = get_user(user_id)

    if not user.get('notifiedAdmin', False):
        user['notifiedAdmin'] = True
        try:
            first_name = message.from_user.first_name or 'User'
            username = f"@{message.from_user.username}" if message.from_user.username else 'None'
            bot.send_message(
                ADMIN_ID,
                f"🚨 *𝗡𝗮𝘆𝗮 𝗕𝗮𝗻𝗱𝗮 𝗕𝗼𝘁 𝗠𝗲 𝗔𝗮𝘆𝗮 𝗛𝗮𝗶!* 🔥\n\n"
                f"👤 *𝗡𝗮𝗺𝗲:* {first_name}\n"
                f"🆔 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
                f"🔗 *𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:* {username}",
                parse_mode='Markdown'
            )
        except Exception:
            pass

    chat_id = message.chat.id if hasattr(message, 'chat') else message
    text = (
        f"⚡ *𝗙𝗫 𝗟𝗜𝗞𝗘𝗦 & 𝗣𝗔𝗡𝗘𝗟 𝗕𝗢𝗧* ⚡🔥\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
        f"💰 *𝗕𝗮𝗹𝗮𝗻𝗰𝗲:* `Rs. {user['balance']}`\n"
        f"📦 *𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻:* {user['activePlan']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 𝗡𝗲𝗲𝗰𝗵𝗲 𝗱𝗶𝘆𝗲 𝗴𝗮𝘆𝗲 𝗯𝘂𝘁𝘁𝗼𝗻𝘀 𝘀𝗲 𝗼𝗽𝘁𝗶𝗼𝗻 𝗰𝗵𝘂𝗻𝗲𝗶𝗻: 🚀"
    )
    send_gif_if_exists(chat_id, 'welcome', caption=text, reply_markup=main_menu_keyboard(user_id))


def execute_api_like_run_for_plan(cust_id, now, trigger_mode="fixed", custom_hhmm=None):
    """Calls Like API for an active plan user, updates remaining likes, and sends the exact AutoLikes Daily Run Completed message."""
    with scheduler_lock:
        if cust_id not in plan_progress:
            return
        p = plan_progress[cust_id]
        if p.get('status') != 'Active':
            return

        remaining_before = max(0, int(p['total_likes']) - int(p.get('delivered_total', 0)))
        if remaining_before <= 0:
            p['status'] = 'Completed'
            get_user(cust_id)['activePlan'] = 'Completed'
            return

        if p.get('days') is not None and p.get('expiry') and now >= p['expiry']:
            p['status'] = 'Expired'
            get_user(cust_id)['activePlan'] = 'Expired'
            return

        today_str = now.date().isoformat()
        if trigger_mode == "fixed":
            if p.get('last_fixed_run_date') == today_str:
                return
            p['last_fixed_run_date'] = today_str
        else:
            run_key = f"{today_str}_{custom_hhmm}"
            if p.get('last_custom_run_key') == run_key:
                return
            p['last_custom_run_key'] = run_key

        uid = p['uid']
        region = p.get('region', 'ind').lower()
        real_given = 0
        before_val = p.get('likes_after') if p.get('likes_after') is not None else p.get('likes_before')
        after_val = before_val
        player_name = p.get('player_name', 'Unknown')

        try:
            api_data = call_like_api(uid, region=region, timeout=25)
            m = parse_like_api_metrics(uid, region, api_data)
            player_name = m['nickname'] or player_name
            if m['before'] is not None:
                before_val = m['before']
            if m['after'] is not None:
                after_val = m['after']
            real_given = max(0, int(m['given']))
        except Exception:
            real_given = 0

        counted_likes = min(remaining_before, real_given)
        p['player_name'] = player_name
        p['likes_before'] = before_val
        p['likes_after'] = after_val
        p['delivered_total'] = int(p.get('delivered_total', 0)) + counted_likes

        remaining_after = max(0, int(p['total_likes']) - int(p['delivered_total']))
        if remaining_after <= 0:
            p['status'] = 'Completed'
            get_user(cust_id)['activePlan'] = 'Completed'

        usr = get_user(cust_id)
        usr['history'].append({'date': today_str, 'delivered': counted_likes})
        if len(usr['history']) > 5:
            usr['history'].pop(0)

        next_run_dt = (now + datetime.timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
        next_run_str = next_run_dt.strftime('%d %b %Y, %I:%M %p IST')

        prev_str = f"{before_val:,}" if isinstance(before_val, int) else "N/A"
        final_str = f"{after_val:,}" if isinstance(after_val, int) else "N/A"
        status_footer = (
            "⚡ Yᴏᴜʀ AᴜᴛᴏLɪᴋᴇꜱ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Iꜱ Aᴄᴛɪᴠᴇ."
            if p['status'] == 'Active'
            else "✅ Yᴏᴜʀ AᴜᴛᴏLɪᴋᴇꜱ Pʟᴀɴ Iꜱ Cᴏᴍᴘʟᴇᴛᴇᴅ."
        )

        report_msg = (
            "♥️ AᴜᴛᴏLɪᴋᴇꜱ Dᴀɪʟʏ Rᴜɴ Cᴏᴍᴘʟᴇᴛᴇᴅ\n\n"
            f"💐 Nᴀᴍᴇ: {player_name}\n"
            f"👁 Uɪᴅ: {uid}\n"
            f"🆔 Rᴇɢɪᴏɴ: {region.upper()}\n\n"
            f"🎁 Pʀᴇᴠɪᴏᴜs Lɪᴋᴇs: {prev_str}\n"
            f"➕ Lɪᴋᴇs Aᴅᴅᴇᴅ: {counted_likes:,}\n"
            f"💭 Fɪɴᴀʟ Lɪᴋᴇs: {final_str}\n"
            f"❤️ Lɪᴋᴇs Rᴇᴍᴀɪɴɪɴɢ: {remaining_after:,}\n\n"
            f"⏰ Nᴇxᴛ Rᴜɴ: {next_run_str}\n\n"
            f"{status_footer}"
        )
        send_gif_if_exists(cust_id, 'report', caption=report_msg)


def referral_leave_monitor_loop():
    while True:
        try:
            for uid, udata in list(users.items()):
                if udata.get('referredBy') and not udata.get('referralPenaltyApplied'):
                    check_and_apply_referral_leave_penalty(uid)
        except Exception:
            pass
        time.sleep(60)


def auto_like_scheduler_loop():
    """Runs fixed 05:00 AM IST AutoLikes AND any custom time set by Admin in IST."""
    while True:
        now = now_ist()
        current_hhmm = now.strftime('%H:%M')
        custom_hhmm = bot_settings.get('customAutoRunTime')

        # 1. Fixed 05:00 AM IST run
        if current_hhmm == "05:00":
            for cust_id, p in list(plan_progress.items()):
                if p.get('status') == 'Active':
                    execute_api_like_run_for_plan(cust_id, now, trigger_mode="fixed")

        # 2. Separate Admin-configured custom time run (calls API for all active plan users & sends report)
        if custom_hhmm and current_hhmm == custom_hhmm:
            for cust_id, p in list(plan_progress.items()):
                if p.get('status') == 'Active':
                    execute_api_like_run_for_plan(cust_id, now, trigger_mode="custom", custom_hhmm=custom_hhmm)

        time.sleep(15)


def html_escape(value):
    return html.escape(str(value), quote=True)


def run_daily_bonus_animation(user_id):
    today_str = now_ist().date().isoformat()
    usr = get_user(user_id)

    if usr.get('lastDailyBonusDate') == today_str:
        bot.send_message(
            user_id,
            "⏳ *𝗗𝗮𝗶𝗹𝘆 𝗕𝗼𝗻𝘂𝘀 𝗔𝗮𝗷 𝗞𝗲 𝗟𝗶𝘆𝗲 𝗖𝗹𝗮𝗶𝗺 𝗛𝗼 𝗖𝗵𝘂𝗸𝗮 𝗛𝗮𝗶!*\n\n𝗔𝗮𝗽 𝗮𝗴𝗹𝗮 𝗯𝗼𝗻𝘂𝘀 *𝗞𝗮𝗹* 𝗹𝗲 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻.",
            parse_mode='Markdown'
        )
        return

    anim_msg = bot.send_message(
        user_id,
        "✨ *𝗗𝗔𝗜𝗟𝗬 𝗕𝗢𝗡𝗨𝗦 𝗦𝗣𝗜𝗡 / 𝗨𝗡𝗟𝗢𝗖𝗞* ✨\n\n🎰 `『 ● ○ ○ 』` 𝗟𝘂𝗰𝗸 𝗰𝗵𝗲𝗰𝗸 𝗵𝗼 𝗿𝗮𝗵𝗮 𝗵𝗮𝗶...",
        parse_mode='Markdown'
    )
    frames = [
        "✨ *𝗗𝗔𝗜𝗟𝗬 𝗕𝗢𝗡𝗨𝗦 𝗦𝗣𝗜𝗡 / 𝗨𝗡𝗟𝗢𝗖𝗞* ✨\n\n🎰 `『 ✦ ● ○ 』` 𝗕𝗼𝗻𝘂𝘀 𝗱𝗵𝗼𝗼𝗻𝗱𝗮 𝗷𝗮 𝗿𝗮𝗵𝗮 𝗵𝗮𝗶...",
        "✨ *𝗗𝗔𝗜𝗟𝗬 𝗕𝗢𝗡𝗨𝗦 𝗦𝗣𝗜𝗡 / 𝗨𝗡𝗟𝗢𝗖𝗞* ✨\n\n🎰 `『 ✦ ✦ ● 』` 𝗥𝗲𝘄𝗮𝗿𝗱 𝘁𝗮𝗶𝘆𝗮𝗿 𝗵𝗼 𝗿𝗮𝗵𝗮 𝗵𝗮𝗶...",
        "✨ *𝗗𝗔𝗜𝗟𝗬 𝗕𝗢𝗡𝗨𝗦 𝗦𝗣𝗜𝗡 / 𝗨𝗡𝗟𝗢𝗖𝗞* ✨\n\n🎰 `『 ✦ ✦ ✦ 』` 𝗕𝗼𝗻𝘂𝘀 𝗺𝗶𝗹 𝗴𝗮𝘆𝗮!"
    ]
    for fr in frames:
        time.sleep(0.55)
        try:
            bot.edit_message_text(fr, user_id, anim_msg.message_id, parse_mode='Markdown')
        except Exception:
            pass

    bonus_amt = random.choices([1, 2, 3], weights=[75, 17, 8], k=1)[0]
    usr['lastDailyBonusDate'] = today_str
    usr['balance'] += bonus_amt

    final_txt = (
        f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
        f"   🎁 𝗗𝗔𝗜𝗟𝗬 𝗕𝗢𝗡𝗨𝗦 𝗖𝗟𝗔𝗜𝗠𝗘𝗗\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"🎉 𝗔𝗮𝗽𝗸𝗼 𝗠𝗶𝗹𝗮 : `Rs. {bonus_amt}`\n"
        f"💼 𝗡𝗲𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 : `Rs. {usr['balance']}`\n"
        f"📅 𝗔𝗴𝗹𝗮 𝗕𝗼𝗻𝘂𝘀 : `𝗞𝗮𝗹 𝗺𝗶𝗹𝗲𝗴𝗮`\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot.edit_message_text(final_txt, user_id, anim_msg.message_id, parse_mode='Markdown')
    except Exception:
        bot.send_message(user_id, final_txt, parse_mode='Markdown')


@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
def handle_all_messages(message):
    global LIKE_API_URL
    send_auto_reaction(message)

    if message.content_type != 'text':
        return

    user_id = message.from_user.id
    text = message.text or ""

    user = get_user(user_id)
    if message.from_user.username:
        user['username'] = message.from_user.username

    if user_id != ADMIN_ID and user.get('referredBy') and not user.get('referralPenaltyApplied'):
        check_and_apply_referral_leave_penalty(user_id)

    menu_buttons = [
        '👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹', '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)', '💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀',
        '🏰 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆', '🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲', '👤 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮',
        '🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻', '📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻', '🔍 𝗜𝗗 𝗜𝗻𝗳𝗼',
        '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲', '📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻', '🎁 𝗗𝗮𝗶𝗹𝘆 𝗕𝗼𝗻𝘂𝘀'
    ]

    if text in menu_buttons:
        pending_state.pop(user_id, None)
        pending_uid.pop(user_id, None)
        pending_guild_order.pop(user_id, None)

    state = pending_state.get(user_id)

    if text == '🏰 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏰 𝗥𝘀. 𝟵𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 (𝟰 𝗕𝗼𝘁𝘀 | 𝟮,𝟱𝟯,𝟱𝟬𝟬)", callback_data='guild_plan_99'))
        markup.add(types.InlineKeyboardButton("👑 𝗥𝘀. 𝟭𝟰𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 (𝟳,𝟮𝟭,𝟵𝟬𝟬)", callback_data='guild_plan_149'))
        guild_txt = (
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "   🏰 𝗚𝗨𝗜𝗟𝗗 𝗚𝗟𝗢𝗥𝗬 𝗦𝗧𝗢𝗥𝗘\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "1️⃣ *𝗥𝘀. 𝟵𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 𝗣𝗹𝗮𝗻*\n"
            "   • 🤖 𝗕𝗼𝘁𝘀: `4 Bots`\n"
            "   • 🏆 𝗧𝗼𝘁𝗮𝗹 𝗚𝗹𝗼𝗿𝘆: `2,53,500`\n\n"
            "2️⃣ *𝗥𝘀. 𝟭𝟰𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 𝗣𝗹𝗮𝗻*\n"
            "   • 🏆 𝗧𝗼𝘁𝗮𝗹 𝗚𝗹𝗼𝗿𝘆: `7,21,900`\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 𝗔𝗽𝗻𝗮 𝗽𝗹𝗮𝗻 𝘀𝗲𝗹𝗲𝗰𝘁 𝗸𝗮𝗿𝗲𝗶𝗻:"
        )
        send_gif_if_exists(user_id, 'guild', caption=guild_txt, reply_markup=markup)
        return

    if user_id in pending_guild_order:
        g_order = pending_guild_order[user_id]
        g_step = g_order.get('step', 'WAITING_GAME_UID')
        inp = text.strip()

        if g_step == 'WAITING_GAME_UID':
            if not inp.isdigit():
                bot.send_message(user_id, "❌ *Game UID galat hai!* Kripya sirf numbers mein apna **Game UID** bhejein:", parse_mode='Markdown')
                return
            wait_g = bot.send_message(user_id, "⏳ *Guild details fetch ho rahi hain...*", parse_mode='Markdown')
            try:
                g_info = fetch_guild_details_by_game_uid(inp, region='ind', timeout=25)
            except Exception:
                try:
                    bot.edit_message_text(
                        "❌ *Game UID galat hai ya guild details nahi mili!* Sahi **Game UID** bhejein:",
                        user_id, wait_g.message_id, parse_mode='Markdown'
                    )
                except Exception:
                    bot.send_message(user_id, "❌ *Game UID galat hai ya guild details nahi mili!* Sahi **Game UID** bhejein:", parse_mode='Markdown')
                return

            g_order['game_uid'] = inp
            g_order['guild_details_block'] = g_info['formatted_block']
            g_order['step'] = 'WAITING_GUILD_UID'

            prompt_guild_uid = (
                f"{g_info['formatted_block']}\n\n"
                f"🏰 *Ab apna **Guild UID** bhejein:*"
            )
            try:
                bot.edit_message_text(prompt_guild_uid, user_id, wait_g.message_id, parse_mode='Markdown')
            except Exception:
                bot.send_message(user_id, prompt_guild_uid, parse_mode='Markdown')
            return

        if g_step == 'WAITING_GUILD_UID':
            pending_guild_order.pop(user_id, None)
            guild_uid = inp
            if not guild_uid.isdigit():
                bot.send_message(user_id, "❌ *𝗚𝘂𝗶𝗹𝗱 𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗞𝗿𝗶𝗽𝘆𝗮 𝘀𝗶𝗿𝗳 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗺𝗲𝗶𝗻 𝗚𝘂𝗶𝗹𝗱 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.", parse_mode='Markdown')
                return

            if user['balance'] < g_order['price']:
                bot.send_message(
                    user_id,
                    f"❌ *𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲!* 𝗜𝘀 𝗽𝗹𝗮𝗻 𝗸𝗲 𝗹𝗶𝘆𝗲 `Rs. {g_order['price']}` 𝗰𝗵𝗮𝗵𝗶𝘆𝗲. 𝗔𝗽𝗸𝗮 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 `Rs. {user['balance']}` 𝗵𝗮𝗶.",
                    parse_mode='Markdown'
                )
                return

            user['balance'] -= g_order['price']
            order_id_10 = generate_unique_10_digit_alnum_id()
            u_tag = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "User")
            guild_details_block = g_order.get('guild_details_block', '')

            guild_orders[order_id_10] = {
                'order_id': order_id_10,
                'user_id': user_id,
                'username': u_tag,
                'game_uid': g_order.get('game_uid'),
                'guild_uid': guild_uid,
                'guild_details_block': guild_details_block,
                'plan': g_order['plan'],
                'bots': g_order['bots'],
                'glory': g_order['glory'],
                'price': g_order['price'],
                'status': 'Pending',
                'created_at': now_ist().strftime('%Y-%m-%d %H:%M:%S')
            }

            bots_line = f"🤖 *𝗕𝗼𝘁𝘀:* `{g_order['bots']}`\n" if g_order.get('bots') else ""
            g_det_section = f"\n{guild_details_block}\n" if guild_details_block else "\n"
            pending_msg = (
                f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                f"   ⏳ 𝗚𝗨𝗜𝗟𝗗 𝗢𝗥𝗗𝗘𝗥 𝗣𝗘𝗡𝗗𝗜𝗡𝗚\n"
                f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"📌 *𝗧𝘂𝗺𝗵𝗮𝗿𝗮 𝗼𝗿𝗱𝗲𝗿 𝗽𝗲𝗻𝗱𝗶𝗻𝗴 𝗺𝗲 𝗵𝗮𝗶, 𝗮𝗱𝗺𝗶𝗻 𝘀𝗲 𝗯𝗼𝗹 𝗸𝗮𝗿 𝗯𝗼𝘁 𝗮𝗱𝗱 𝗸𝗮𝗿𝘄𝗮 𝗹𝗼!*\n\n"
                f"🆔 *𝗨𝘀𝗲𝗿 / 𝗢𝗿𝗱𝗲𝗿 𝗜𝗗:* `{order_id_10}`\n"
                f"🏰 *𝗚𝘂𝗶𝗹𝗱 𝗨𝗜𝗗:* `{guild_uid}`"
                f"{g_det_section}"
                f"📦 *𝗣𝗹𝗮𝗻:* *{g_order['plan']}*\n"
                f"{bots_line}"
                f"🏆 *𝗚𝗹𝗼𝗿𝘆:* `{g_order['glory']}`\n"
                f"💰 *𝗣𝗮𝗶𝗱:* `Rs. {g_order['price']}`\n"
                f"💼 *𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗕𝗮𝗹𝗮𝗻𝗰𝗲:* `Rs. {user['balance']}`\n"
                f"👑 *𝗔𝗱𝗺𝗶𝗻:* {ADMIN_USERNAME}\n\n"
                f"📋 *𝗨𝗽𝗮𝗿 𝗱𝗶 𝗴𝗮𝘆𝗶 10-𝗰𝗵𝗮𝗿𝗮𝗰𝘁𝗲𝗿 𝗜𝗗 (`{order_id_10}`) 𝗰𝗼𝗽𝘆 𝗸𝗮𝗿𝗸𝗲 𝗮𝗱𝗺𝗶𝗻 𝗸𝗼 𝗯𝗵𝗲𝗷 𝗱𝗲𝗶𝗻.*\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, pending_msg, parse_mode='Markdown')

            try:
                bot.send_message(
                    ADMIN_ID,
                    f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                    f"   🏰 𝗡𝗔𝗬𝗔 𝗚𝗨𝗜𝗟𝗗 𝗚𝗟𝗢𝗥𝗬 𝗢𝗥𝗗𝗘𝗥\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"🆔 *10-𝗖𝗵𝗮𝗿 𝗜𝗗:* `{order_id_10}`\n"
                    f"👤 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
                    f"🔗 *𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:* {u_tag}\n"
                    f"🏰 *𝗚𝘂𝗶𝗹𝗱 𝗨𝗜𝗗:* `{guild_uid}`"
                    f"{g_det_section}"
                    f"📦 *𝗣𝗹𝗮𝗻:* *{g_order['plan']}*\n"
                    f"{bots_line}"
                    f"🏆 *𝗚𝗹𝗼𝗿𝘆:* `{g_order['glory']}`\n"
                    f"💰 *𝗔𝗺𝗼𝘂𝗻𝘁:* `Rs. {g_order['price']}`\n"
                    f"━━━━━━━━━━━━━━━━━━━",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            return

    if text == '🎁 𝗗𝗮𝗶𝗹𝘆 𝗕𝗼𝗻𝘂𝘀':
        run_daily_bonus_animation(user_id)
        return

    if text == '📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻':
        p = plan_progress.get(user_id)
        if not p and user['activePlan'] == 'None':
            bot.send_message(
                user_id,
                "📦 *𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻:* 𝗔𝗮𝗽𝗸𝗮 𝗸𝗼𝗶 𝗯𝗵𝗶 𝗮𝗰𝘁𝗶𝘃𝗲 𝗽𝗹𝗮𝗻 𝗻𝗮𝗵𝗶 𝗵𝗮𝗶. 𝗣𝗲𝗵𝗹𝗲 💖 *𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀* 𝘀𝗲 𝗽𝗹𝗮𝗻 𝗹𝗲𝗶𝗻.",
                parse_mode='Markdown'
            )
            return

        now = now_ist()
        if p:
            delivered_val = int(p.get('delivered_total', 0))
            total_val = int(p.get('total_likes', 0))
            remaining_val = max(0, total_val - delivered_val)
            days_left = max(0, (p['expiry'] - now).days) if p.get('expiry') else 0
            plan_details = (
                f"• 𝗣𝗹𝗮𝗻 𝗡𝗮𝗺𝗲: *{p['plan']}*\n"
                f"• 𝗦𝘁𝗮𝘁𝘂𝘀: *{p.get('status', 'Active')}*\n"
                f"• 𝗧𝗮𝗿𝗴𝗲𝘁 𝗨𝗜𝗗: `{p['uid']}`\n"
                f"• 𝗧𝗼𝘁𝗮𝗹 𝗣𝗹𝗮𝗻 𝗟𝗶𝗸𝗲𝘀: *{total_val:,}*\n"
                f"• 𝗥𝗲𝗮𝗹 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗲𝗱: *{delivered_val:,}*\n"
                f"• 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗟𝗶𝗸𝗲𝘀: *{remaining_val:,}*\n"
                f"• 𝗗𝗮𝘆𝘀 𝗟𝗲𝗳𝘁: *{days_left} 𝗗𝗮𝘆𝘀*\n"
                f"• 𝗘𝘅𝗽𝗶𝗿𝘆 𝗗𝗮𝘁𝗲: *{p['expiry'].strftime('%Y-%m-%d %H:%M:%S')}*"
            )
        else:
            plan_details = (
                f"• 𝗣𝗹𝗮𝗻 𝗡𝗮𝗺𝗲: *{user['activePlan']}*\n"
                f"• 𝗘𝘅𝗽𝗶𝗿𝘆 𝗗𝗮𝘁𝗲: *{user['planExpiry']}*"
            )

        history_text = ""
        if user['history']:
            history_text = "\n\n📊 *𝗟𝗮𝘀𝘁 𝟱 𝗗𝗮𝘆𝘀 𝗥𝗲𝗮𝗹 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝘆:*\n"
            for h in user['history'][-5:]:
                history_text += f"• `{h['date']}`: *{h['delivered']:,}* 𝗹𝗶𝗸𝗲𝘀\n"

        bot.send_message(
            user_id,
            f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
            f"   📦 𝗬𝗢𝗨𝗥 𝗔𝗖𝗧𝗜𝗩𝗘 𝗣𝗟𝗔𝗡\n"
            f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"{plan_details}"
            f"{history_text}\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if text == '🎁 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲':
        pending_state[user_id] = {'step': 'WAITING_FOR_REDEEM_CODE'}
        bot.send_message(
            user_id,
            "🎁 *𝗥𝗘𝗘𝗗𝗘𝗠 𝗖𝗢𝗗𝗘 𝗦𝗬𝗦𝗧𝗘𝗠* ⚡\n\n✍️ 𝗔𝗽𝗻𝗮 𝗥𝗲𝗲𝗱𝗲𝗺 𝗖𝗼𝗱𝗲 𝘆𝗮𝗵𝗮𝗻 𝘁𝘆𝗽𝗲 𝗸𝗮𝗿𝗸𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:",
            parse_mode='Markdown'
        )
        return

    if isinstance(state, dict) and state.get('step') == 'WAITING_FOR_REDEEM_CODE':
        code_input = text.strip()
        pending_state.pop(user_id, None)

        if code_input not in redeem_codes:
            bot.send_message(user_id, "❌ *𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲!* 𝗬𝗲𝗵 𝗰𝗼𝗱𝗲 𝗴𝗮𝗹𝗮𝘁 𝘆𝗮 𝗲𝘅𝗶𝘀𝘁 𝗻𝗮𝗵𝗶 𝗸𝗮𝗿𝘁𝗮.", parse_mode='Markdown')
            return

        r_data = redeem_codes[code_input]
        if time.time() > r_data['expiry_time']:
            bot.send_message(user_id, "❌ *𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲 𝗘𝘅𝗽𝗶𝗿𝗲𝗱!* 𝗜𝘀 𝗰𝗼𝗱𝗲 𝗸𝗶 𝘁𝗶𝗺𝗲 𝗹𝗶𝗺𝗶𝘁 𝗸𝗵𝗮𝘁𝗮𝗺 𝗵𝗼 𝗰𝗵𝘂𝗸𝗶 𝗵𝗮𝗶.", parse_mode='Markdown')
            return

        if len(r_data['used_by']) >= r_data['max_uses']:
            bot.send_message(user_id, "❌ *𝗖𝗼𝗱𝗲 𝗟𝗶𝗺𝗶𝘁 𝗥𝗲𝗮𝗰𝗵𝗲𝗱!* 𝗜𝘀 𝗰𝗼𝗱𝗲 𝗸𝗲 𝘀𝗮𝗮𝗿𝗲 𝘂𝘀𝗲𝘀 𝗽𝗼𝗼𝗿𝗲 𝗵𝗼 𝗰𝗵𝘂𝗸𝗲 𝗵𝗮𝗶𝗻.", parse_mode='Markdown')
            return

        if user_id in r_data['used_by']:
            bot.send_message(user_id, "❌ *𝗔𝗮𝗽 𝘆𝗲𝗵 𝗰𝗼𝗱𝗲 𝗽𝗲𝗵𝗹𝗲 𝗵𝗶 𝗿𝗲𝗱𝗲𝗲𝗺 𝗸𝗮𝗿 𝗰𝗵𝘂𝗸𝗲 𝗵𝗮𝗶𝗻!*", parse_mode='Markdown')
            return

        r_data['used_by'].add(user_id)
        amount = r_data['amount']
        user['balance'] += amount

        bot.send_message(
            user_id,
            f"✅ *𝗥𝗘𝗗𝗘𝗘𝗠 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟!* 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 𝗖𝗼𝗱𝗲: `{code_input}`\n"
            f"💰 𝗔𝗱𝗱𝗲𝗱: `Rs. {amount}`\n"
            f"💼 𝗡𝗲𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: `Rs. {user['balance']}`\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )

        try:
            u_name = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "User")
            bot.send_message(
                ADMIN_ID,
                f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                f"   🎁 𝗥𝗘𝗗𝗘𝗘𝗠 𝗖𝗢𝗗𝗘 𝗥𝗘𝗗𝗘𝗘𝗠𝗘𝗗\n"
                f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"👤 𝗨𝘀𝗲𝗿 𝗜𝗗 : `{user_id}`\n"
                f"🔗 𝗨𝘀𝗲𝗿 : {u_name}\n"
                f"🎟 𝗖𝗼𝗱𝗲 : `{code_input}`\n"
                f"💰 𝗔𝗺𝗼𝘂𝗻𝘁 : `Rs. {amount}`\n"
                f"💼 𝗨𝘀𝗲𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 : `Rs. {user['balance']}`\n"
                f"━━━━━━━━━━━━━━━━━━━",
                parse_mode='Markdown'
            )
        except Exception:
            pass
        return

    if text == '🔍 𝗜𝗗 𝗜𝗻𝗳𝗼' or (isinstance(state, dict) and state.get('step') == 'WAITING_FOR_UID'):
        if not isinstance(state, dict) or state.get('step') != 'WAITING_FOR_UID':
            pending_state[user_id] = {'step': 'WAITING_FOR_UID'}
            bot.send_message(
                user_id,
                "🔍 *𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗜𝗗 𝗜𝗡𝗙𝗢*\n\n𝗔𝗽𝗻𝗮 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `4232090116`):",
                parse_mode='Markdown'
            )
            return
        parts = text.strip().split()
        pending_state.pop(user_id, None)
        if not parts or not parts[0].isdigit():
            bot.send_message(user_id, "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗨𝗜𝗗 𝘀𝗶𝗿𝗳 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗺𝗲𝗶𝗻 𝗵𝗼𝗻𝗮 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", parse_mode='Markdown')
            return
        uid = parts[0]
        region = parts[1].lower() if len(parts) > 1 else "ind"
        loading = bot.send_message(user_id, "⏳ *𝗜𝗗 𝗶𝗻𝗳𝗼 𝗳𝗲𝘁𝗰𝗵 𝗵𝗼 𝗿𝗮𝗵𝗶 𝗵𝗮𝗶...*", parse_mode='Markdown')
        try:
            api_data = call_like_api(uid, region=region, timeout=25)
            formatted = format_styled_id_info(uid, region, api_data)
            bot.edit_message_text(formatted, user_id, loading.message_id, parse_mode='Markdown')
        except Exception:
            bot.edit_message_text(
                "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗞𝗿𝗶𝗽𝘆𝗮 𝘀𝗮𝗵𝗶 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.",
                user_id, loading.message_id, parse_mode='Markdown'
            )
        return

    if text == '👑 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹' and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("❤️ 𝗦𝗲𝗻𝘁 𝗟𝗶𝗸𝗲", callback_data='admin_sent_like'),
            types.InlineKeyboardButton("📦 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻", callback_data='admin_set_active_plan')
        )
        markup.row(
            types.InlineKeyboardButton("🚫 𝗣𝗹𝗮𝗻 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data='admin_cancel_plan'),
            types.InlineKeyboardButton("🕒 𝗦𝗲𝘁 𝗧𝗶𝗺𝗲", callback_data='admin_set_time')
        )
        markup.row(
            types.InlineKeyboardButton("🔗 𝗖𝗵𝗮𝗻𝗴𝗲 / 𝗔𝗱𝗱 𝗔𝗣𝗜", callback_data='admin_set_api'),
            types.InlineKeyboardButton("📊 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻𝘀 & 𝗨𝗜𝗗𝘀", callback_data='admin_view_plans')
        )
        markup.row(
            types.InlineKeyboardButton("💰 𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", callback_data='admin_add_balance'),
            types.InlineKeyboardButton("📢 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_add_channel')
        )
        markup.row(
            types.InlineKeyboardButton("❌ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", callback_data='admin_remove_channel'),
            types.InlineKeyboardButton("🎁 𝗦𝗲𝘁 𝗥𝗲𝗳𝗲𝗿 𝗕𝗼𝗻𝘂𝘀", callback_data='admin_set_refer')
        )
        markup.row(
            types.InlineKeyboardButton("🎁 𝗖𝗿𝗲𝗮𝘁𝗲 𝗥𝗲𝗱𝗲𝗲𝗺", callback_data='admin_create_redeem'),
            types.InlineKeyboardButton("✉️ 𝗣𝗲𝗿𝘀𝗼𝗻𝗮𝗹 𝗠𝗲𝘀𝘀𝗮𝗴𝗲", callback_data='admin_personal_msg')
        )
        markup.row(
            types.InlineKeyboardButton("📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", callback_data='admin_broadcast')
        )
        active_cnt = sum(1 for p in plan_progress.values() if p.get('status') == 'Active')
        custom_t_disp = bot_settings.get('customAutoRunTime') or 'Not Set'
        bot.send_message(
            user_id,
            f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
            f"   👑 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟\n"
            f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"• 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻𝘀: `{active_cnt}` (𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗰𝗼𝗿𝗱𝘀: `{len(plan_progress)}`)\n"
            f"• 𝗙𝗶𝘅𝗲𝗱 𝗔𝘂𝘁𝗼𝗟𝗶𝗸𝗲 𝗧𝗶𝗺𝗲: `05:00 AM IST`\n"
            f"• 𝗖𝘂𝘀𝘁𝗼𝗺 𝗔𝘂𝘁𝗼𝗟𝗶𝗸𝗲 𝗧𝗶𝗺𝗲: `{custom_t_disp} IST`\n"
            f"• 𝗚𝘂𝗶𝗹𝗱 𝗢𝗿𝗱𝗲𝗿𝘀: `{len(guild_orders)}`\n"
            f"• 𝗟𝗶𝗸𝗲 𝗔𝗣𝗜: `{LIKE_API_URL}`\n"
            f"• 𝗥𝗲𝗳𝗲𝗿 𝗕𝗼𝗻𝘂𝘀: `Rs. {bot_settings['referralBonus']}`\n"
            f"• 𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲𝘀: `{len(redeem_codes)}`\n"
            f"• 𝗨𝗣𝗜 𝗜𝗗: `{bot_settings['upiId']}`\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    if text == '💳 𝗔𝗱𝗱 𝗠𝗼𝗻𝗲𝘆 (𝗨𝗣𝗜)':
        pending_state[user_id] = {'step': 'WAITING_FOR_AMOUNT'}
        bot.send_message(user_id, "💳 *𝗔𝗗𝗗 𝗠𝗢𝗡𝗘𝗬 (𝗨𝗣𝗜)* 💰\n\n✍️ 𝗞𝗶𝘁𝗻𝗮 𝗮𝗺𝗼𝘂𝗻𝘁 𝗮𝗱𝗱 𝗸𝗮𝗿𝗻𝗮 𝗵𝗮𝗶? 𝗡𝘂𝗺𝗯𝗲𝗿 𝘁𝘆𝗽𝗲 𝗸𝗮𝗿𝗸𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:", parse_mode='Markdown')
        return

    if text == '💖 𝗕𝘂𝘆 𝗟𝗶𝗸𝗲 / 𝗣𝗹𝗮𝗻𝘀':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 𝗕𝘂𝘆 𝗥𝘀. 𝟲 𝗗𝗲𝗺𝗼 𝗣𝗹𝗮𝗻 (𝟮𝟮𝟬 𝗟𝗶𝗸𝗲𝘀)", callback_data='buy_demo'))
        markup.add(types.InlineKeyboardButton("🔥 𝗕𝘂𝘆 𝗥𝘀. 𝟱𝟵 𝗣𝗹𝗮𝗻 (𝟯,𝟯𝟬𝟬 𝗟𝗶𝗸𝗲𝘀)", callback_data='buy_59'))
        markup.add(types.InlineKeyboardButton("🔥 𝗕𝘂𝘆 𝗥𝘀. 𝟭𝟭𝟬 𝗣𝗹𝗮𝗻 (𝟲,𝟲𝟬𝟬 𝗟𝗶𝗸𝗲𝘀)", callback_data='buy_110'))
        markup.add(types.InlineKeyboardButton("🔓 𝟭𝟬 𝗥𝗲𝗳𝘀 𝗨𝗻𝗹𝗼𝗰𝗸 𝗣𝗹𝗮𝗻 (𝟭,𝟱𝟰𝟬 𝗟𝗶𝗸𝗲𝘀)", callback_data='buy_ref_unlock'))
        plans_txt = (
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "   💖 𝗦𝗘𝗟𝗘𝗖𝗧 𝗟𝗜𝗞𝗘 𝗣𝗟𝗔𝗡𝗦\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "0️⃣ *𝗥𝘀. 𝟲 𝗗𝗲𝗺𝗼 𝗣𝗹𝗮𝗻*\n   • 𝗗𝗮𝗶𝗹𝘆 `220` 𝗥𝗲𝗮𝗹 𝗔𝗣𝗜 𝗟𝗶𝗸𝗲𝘀 ⚡\n\n"
            "1️⃣ *𝗥𝘀. 𝟱𝟵 𝗣𝗹𝗮𝗻*\n   • `3,300` 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗮𝗹 𝗔𝗣𝗜 𝗟𝗶𝗸𝗲𝘀 ✨\n\n"
            "2️⃣ *𝗥𝘀. 𝟭𝟭𝟬 𝗣𝗹𝗮𝗻*\n   • `6,600` 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗮𝗹 𝗔𝗣𝗜 𝗟𝗶𝗸𝗲𝘀 🌟\n\n"
            "3️⃣ *𝟭𝟬 𝗥𝗲𝗳𝘀 𝗨𝗻𝗹𝗼𝗰𝗸 𝗣𝗹𝗮𝗻*\n   • `1,540` 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗮𝗹 𝗔𝗣𝗜 𝗟𝗶𝗸𝗲𝘀 🔓\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        send_gif_if_exists(user_id, 'plan', caption=plans_txt, reply_markup=markup)
        return

    if text == '🛒 𝗖𝗖 𝗦𝘁𝗼𝗿𝗲':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 𝗕𝘂𝘆 𝗥𝘀. 𝟭𝟬𝟬 𝗖𝗖 𝗣𝗹𝗮𝗻 (𝟮𝗸)", callback_data='buy_cc_100'))
        markup.add(types.InlineKeyboardButton("🛒 𝗕𝘂𝘆 𝗥𝘀. 𝟭𝟵𝟵 𝗖𝗖 𝗣𝗹𝗮𝗻 (𝟱𝗸)", callback_data='buy_cc_199'))
        bot.send_message(
            user_id,
            "🛒 *𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗖𝗖 𝗦𝗧𝗢𝗥𝗘* 🛍️\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ *𝗥𝘀. 𝟭𝟬𝟬 𝗖𝗖 𝗣𝗹𝗮𝗻*\n   • 𝗖𝗖 𝗖𝗮𝗿𝗱 / 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 (𝟮𝗸) 💳\n\n"
            "2️⃣ *𝗥𝘀. 𝟭𝟵𝟵 𝗖𝗖 𝗣𝗹𝗮𝗻*\n   • 𝗖𝗖 𝗖𝗮𝗿𝗱 / 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 (𝟱𝗸) 💎\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 𝗣𝗹𝗮𝗻 𝘀𝗲𝗹𝗲𝗰𝘁 𝗸𝗮𝗿𝗻𝗲 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗻𝗲𝗲𝗰𝗵𝗲 𝘁𝗮𝗽 𝗸𝗮𝗿𝗲𝗶𝗻:",
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
            f"💼 *𝗬𝗢𝗨𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘* 👤\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📛 *𝗡𝗮𝗺𝗲:* {first_name}\n"
            f"🆔 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
            f"🔗 *𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:* {username}\n"
            f"💰 *𝗕𝗮𝗹𝗮𝗻𝗰𝗲:* `Rs. {user['balance']}`\n"
            f"📦 *𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻:* {user['activePlan']}\n"
            f"⏰ *𝗘𝘅𝗽𝗶𝗿𝘆:* `{user['planExpiry']}`\n"
            f"👥 *𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹𝘀:* `{user['referrals']}/10`\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )
        return

    if text == '🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻':
        username = bot.get_me().username
        link = f"https://t.me/{username}?start={user_id}"
        user = get_user(user_id)
        bot.send_message(
            user_id,
            f"🎁 *𝗥𝗘𝗙𝗘𝗥 & 𝗘𝗔𝗥𝗡* 🌟\n\n"
            f"𝗛𝗮𝗿 𝗷𝗼𝗶𝗻 𝗽𝗮𝗿 𝗺𝗶𝗹𝗲𝗻𝗴𝗲 *𝗥𝘀. {bot_settings['referralBonus']}*! ✨\n"
            f"👥 𝗔𝗮𝗽𝗸𝗲 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹𝘀: `{user['referrals']}/10`\n\n"
            f"🔗 *𝗟𝗶𝗻𝗸:*\n`{link}`",
            parse_mode='Markdown'
        )
        return

    if text == '📞 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻':
        username = f"@{message.from_user.username}" if message.from_user.username else 'None'
        bot.send_message(
            user_id,
            f"📞 *𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗔𝗗𝗠𝗜𝗡* 🛠️\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *𝗔𝗮𝗽𝗸𝗶 𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
            f"🔗 *𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:* {username}\n"
            f"⚠️ *𝗣𝗿𝗼𝗯𝗹𝗲𝗺 𝗗𝗲𝘁𝗮𝗶𝗹𝘀:* 𝗞𝗼𝗶 𝗯𝗵𝗶 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝗵𝗼 𝘁𝗼𝗵 𝘀𝗲𝗲𝗱𝗵𝗲 𝗔𝗱𝗺𝗶𝗻 𝗸𝗼 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗸𝗮𝗿𝗲𝗶𝗻!\n"
            f"👉 *𝗔𝗱𝗺𝗶𝗻 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗜𝗗:* {ADMIN_USERNAME}\n"
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
            bot.send_message(user_id, f"✅ 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗮𝗱𝗱𝗲𝗱: {ch}")
            return
        if state == 'REMOVE_CHANNEL':
            ch = text.strip()
            if ch in bot_settings['requiredChannels']:
                bot_settings['requiredChannels'].remove(ch)
                bot.send_message(user_id, f"❌ 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗿𝗲𝗺𝗼𝘃𝗲𝗱: {ch}")
            else:
                bot.send_message(user_id, "⚠️ 𝗬𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗹𝗶𝘀𝘁 𝗺𝗲 𝗻𝗮𝗵𝗶 𝗺𝗶𝗹𝗮!")
            pending_state.pop(user_id, None)
            return
        if state == 'SET_REFER_BONUS':
            try:
                new_bonus = int(text.strip())
                if new_bonus < 0:
                    raise ValueError()
                bot_settings['referralBonus'] = new_bonus
                pending_state.pop(user_id, None)
                bot.send_message(user_id, f"✅ 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗯𝗼𝗻𝘂𝘀 𝘂𝗽𝗱𝗮𝘁𝗲𝗱: *Rs. {bot_settings['referralBonus']}*", parse_mode='Markdown')
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗮𝗺𝗼𝘂𝗻𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return
        if state == 'BROADCAST_MSG':
            pending_state.pop(user_id, None)
            for uid in users:
                try:
                    bot.send_message(uid, f"📢 *𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁:*\n\n{text}", parse_mode='Markdown')
                except Exception:
                    pass
            bot.send_message(user_id, "✅ 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝘀𝗲𝗻𝘁!")
            return

    if user_id == ADMIN_ID and isinstance(state, dict):
        step = state.get('step')

        if step == 'ADMIN_SET_CUSTOM_TIME':
            raw_t = text.strip()
            pending_state.pop(user_id, None)
            if raw_t.lower() in ('off', 'clear', 'disable', 'none', '0'):
                bot_settings['customAutoRunTime'] = None
                bot.send_message(
                    user_id,
                    "✅ *𝗖𝘂𝘀𝘁𝗼𝗺 𝗔𝘂𝘁𝗼𝗟𝗶𝗸𝗲 𝗧𝗶𝗺𝗲 𝗖𝗹𝗲𝗮𝗿 𝗞𝗮𝗿 𝗗𝗶𝘆𝗮 𝗚𝗮𝘆𝗮!* (Fixed `05:00 AM IST` chalta rahega)",
                    parse_mode='Markdown'
                )
                return

            parsed_time = None
            for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p", "%H"):
                try:
                    dt_t = datetime.datetime.strptime(raw_t.upper(), fmt)
                    parsed_time = dt_t.strftime("%H:%M")
                    break
                except ValueError:
                    continue
            if not parsed_time:
                bot.send_message(
                    user_id,
                    "❌ *𝗧𝗶𝗺𝗲 𝗳𝗼𝗿𝗺𝗮𝘁 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗞𝗿𝗶𝗽𝘆𝗮 `16:00` 𝘆𝗮 `04:00 PM` 𝗳𝗼𝗿𝗺𝗮𝘁 𝗺𝗲𝗶𝗻 𝘁𝗶𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝘆𝗮 `off` 𝗹𝗶𝗸𝗵𝗲𝗶𝗻):",
                    parse_mode='Markdown'
                )
                return
            bot_settings['customAutoRunTime'] = parsed_time
            bot.send_message(
                user_id,
                f"✅ *𝗖𝘂𝘀𝘁𝗼𝗺 𝗔𝘂𝘁𝗼𝗟𝗶𝗸𝗲 𝗧𝗶𝗺𝗲 𝗦𝗲𝘁!* 🕒\n\n"
                f"• 𝗙𝗶𝘅𝗲𝗱 𝗗𝗮𝗶𝗹𝘆 𝗥𝘂𝗻: `05:00 AM IST`\n"
                f"• 𝗦𝗲𝘁 𝗖𝘂𝘀𝘁𝗼𝗺 𝗥𝘂𝗻: `{parsed_time} IST`\n"
                f"• 𝗜𝘀 𝘁𝗶𝗺𝗲 𝗽𝗮𝗿 **𝗔𝗣𝗜 𝘀𝗮𝗯𝗵𝗶 𝗮𝗰𝘁𝗶𝘃𝗲 𝗽𝗹𝗮𝗻 𝘄𝗮𝗹𝗲 𝘂𝘀𝗲𝗿𝘀 𝗸𝗼 𝗹𝗶𝗸𝗲 𝗯𝗵𝗲𝗷𝗲𝗴𝗶** 𝗮𝘂𝗿 𝘂𝗻𝗸𝗼 `AᴜᴛᴏLɪᴋᴇꜱ Dᴀɪʟʏ Rᴜɴ Cᴏᴍᴘʟᴇᴛᴇᴅ` 𝗸𝗮 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗯𝗵𝗶 𝗺𝗶𝗹𝗲𝗴𝗮!",
                parse_mode='Markdown'
            )
            return

        if step == 'ADMIN_SET_API_URL':
            new_url = text.strip()
            pending_state.pop(user_id, None)
            if not (new_url.startswith("http://") or new_url.startswith("https://")):
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗔𝗣𝗜 𝗨𝗥𝗟 𝗱𝗮𝗮𝗹𝗲𝗶𝗻 (`https://...` 𝘀𝗲 𝘀𝗵𝘂𝗿𝘂 𝗵𝗼𝗻𝗮 𝗰𝗵𝗮𝗵𝗶𝘆𝗲).")
                return
            LIKE_API_URL = new_url
            bot.send_message(
                user_id,
                f"✅ *𝗟𝗜𝗞𝗘 𝗔𝗣𝗜 𝗨𝗣𝗗𝗔𝗧𝗘𝗗!* 🔗\n\n𝗡𝗲𝘄 𝗔𝗣𝗜 𝗨𝗥𝗟:\n`{LIKE_API_URL}`",
                parse_mode='Markdown'
            )
            return

        if step == 'ADMIN_SENT_LIKE_INPUT':
            parts = text.strip().split()
            pending_state.pop(user_id, None)
            if not parts or not parts[0].isdigit():
                bot.send_message(user_id, "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗦𝗮𝗵𝗶 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.")
                return
            target_ff_uid = parts[0]
            region = parts[1].lower() if len(parts) > 1 else "ind"
            wait_msg = bot.send_message(user_id, f"⏳ 𝗨𝗜𝗗 `{target_ff_uid}` (`{region.upper()}`) 𝗽𝗮𝗿 𝗹𝗶𝗸𝗲 𝗯𝗵𝗲𝗷𝗮 𝗷𝗮 𝗿𝗮𝗵𝗮 𝗵𝗮𝗶...", parse_mode='Markdown')
            try:
                api_res = call_like_api(target_ff_uid, region=region, timeout=25)
                formatted_res = format_styled_sent_like(target_ff_uid, region, api_res)
                bot.edit_message_text(formatted_res, user_id, wait_msg.message_id, parse_mode='Markdown')
            except Exception:
                bot.edit_message_text(
                    "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗞𝗿𝗶𝗽𝘆𝗮 𝘀𝗮𝗵𝗶 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.",
                    user_id, wait_msg.message_id, parse_mode='Markdown'
                )
            return

        if step == 'ADMIN_PLAN_USER_ID':
            if not text.strip().isdigit():
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗡𝘂𝗺𝗲𝗿𝗶𝗰 𝗨𝘀𝗲𝗿 𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
                return
            state['target_user_id'] = int(text.strip())
            state['step'] = 'ADMIN_PLAN_FF_UID'
            bot.send_message(user_id, "🎮 𝗦𝘁𝗲𝗽 𝟮/𝟯: 𝗔𝗯 **𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗** 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:", parse_mode='Markdown')
            return

        if step == 'ADMIN_PLAN_FF_UID':
            if not text.strip().isdigit():
                bot.send_message(user_id, "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗦𝗮𝗵𝗶 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
                return
            state['ff_uid'] = text.strip()
            state['step'] = 'ADMIN_PLAN_TOTAL_LIKES'
            bot.send_message(
                user_id,
                "❤️ 𝗦𝘁𝗲𝗽 𝟯/𝟯: **𝗞𝗶𝘁𝗻𝗮 𝗧𝗼𝘁𝗮𝗹 𝗟𝗶𝗸𝗲** 𝗱𝗲𝗻𝗮 𝗵𝗮𝗶? (𝗡𝘂𝗺𝗯𝗲𝗿 𝗺𝗲𝗶𝗻 𝗱𝗮𝗮𝗹𝗲𝗶𝗻, 𝗷𝗮𝗶𝘀𝗲 `2000` 𝘆𝗮 `5000` — 𝗷𝗮𝗯 𝘁𝗮𝗸 𝗽𝘂𝗿𝗮 𝗻𝗮𝗵𝗶 𝗵𝗼𝘁𝗮 𝘁𝗮𝗯 𝘁𝗮𝗸 𝗺𝗶𝗹𝗲𝗴𝗮):",
                parse_mode='Markdown'
            )
            return

        if step == 'ADMIN_PLAN_TOTAL_LIKES':
            try:
                total_likes_target = int(text.strip().replace(",", ""))
                if total_likes_target <= 0:
                    raise ValueError()
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝘁𝗼𝘁𝗮𝗹 𝗹𝗶𝗸𝗲𝘀 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲𝗶𝗻 𝗱𝗮𝗮𝗹𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `2000`):")
                return

            target_user_id = state['target_user_id']
            ff_uid = state['ff_uid']
            pending_state.pop(user_id, None)

            plan_label = f"𝗧𝗮𝗿𝗴𝗲𝘁 𝗟𝗶𝗸𝗲 𝗣𝗹𝗮𝗻 ({total_likes_target:,} 𝗟𝗶𝗸𝗲𝘀)"
            try:
                info = activate_user_plan(
                    cust_id=target_user_id,
                    target_uid=ff_uid,
                    plan_name=plan_label,
                    total_likes_target=total_likes_target,
                    days=None,
                    daily_cap=None,
                    price_paid=0,
                    username='None',
                    region='ind',
                    send_initial_like=False,
                    fetch_uid_info_only=True
                )
            except Exception:
                bot.send_message(
                    user_id,
                    "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗜𝘀 𝗨𝗜𝗗 𝗸𝗶 𝗱𝗲𝘁𝗮𝗶𝗹𝘀 𝗻𝗮𝗵𝗶 𝗺𝗶𝗹 𝗽𝗮𝘆𝗶𝗻, 𝗽𝗹𝗮𝗻 𝘀𝗲𝘁 𝗻𝗮𝗵𝗶 𝗵𝘂𝗮.",
                    parse_mode='Markdown'
                )
                return

            likes_display = f"{info['likes_after']:,}" if isinstance(info['likes_after'], int) else "N/A"
            admin_confirm = (
                f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                f"   ✅ 𝗔𝗖𝗧𝗜𝗩𝗘 𝗣𝗟𝗔𝗡 𝗦𝗘𝗧\n"
                f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"👤 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗨𝘀𝗲𝗿 𝗜𝗗 : `{target_user_id}`\n"
                f"🎮 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 : `{ff_uid}`\n"
                f"💐 𝗡𝗮𝗺𝗲 : `{info['player_name']}`\n"
                f"⭐ 𝗟𝗲𝘃𝗲𝗹 : `{info['player_level']}`\n"
                f"❤️ 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗟𝗶𝗸𝗲𝘀 : `{likes_display}`\n"
                f"🌍 𝗥𝗲𝗴𝗶𝗼𝗻 : `{info['player_region']}`\n\n"
                f"💖 𝗧𝗼𝘁𝗮𝗹 𝗟𝗶𝗸𝗲 𝗧𝗮𝗿𝗴𝗲𝘁 : `{info['total_likes']:,}`\n"
                f"❤️ 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗟𝗶𝗸𝗲𝘀 : `{info['remaining_likes']:,}`\n"
                f"⏰ 𝗩𝗮𝗹𝗶𝗱 𝗨𝗻𝘁𝗶𝗹 : `{info['expiry'].strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, admin_confirm, parse_mode='Markdown')

            try:
                user_notify = (
                    f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                    f"   🎉 𝗣𝗟𝗔𝗡 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"📦 𝗣𝗹𝗮𝗻 : *{plan_label}*\n"
                    f"💐 𝗡𝗮𝗺𝗲 : `{info['player_name']}`\n"
                    f"🎮 𝗨𝗜𝗗 : `{ff_uid}`\n"
                    f"💖 𝗧𝗼𝘁𝗮𝗹 𝗟𝗶𝗸𝗲𝘀 : `{info['total_likes']:,}`\n"
                    f"❤️ 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗟𝗶𝗸𝗲𝘀 : `{info['remaining_likes']:,}`\n\n"
                    f"📌 𝗝𝗮𝗯 𝘁𝗮𝗸 𝘁𝗼𝘁𝗮𝗹 𝗹𝗶𝗸𝗲𝘀 𝗽𝘂𝗿𝗲 𝗻𝗮𝗵𝗶 𝗵𝗼𝘁𝗲, 𝘁𝗮𝗯 𝘁𝗮𝗸 𝗹𝗶𝗸𝗲𝘀 𝗺𝗶𝗹𝘁𝗲 𝗿𝗮𝗵𝗲𝗻𝗴𝗲 𝗮𝘂𝗿 𝗿𝗼𝘇 𝘀𝘂𝗯𝗮𝗵 𝟱:𝟬𝟬 𝗔𝗠 𝗿𝗲𝗽𝗼𝗿𝘁 𝗮𝗮𝘆𝗲𝗴𝗮."
                )
                bot.send_message(target_user_id, user_notify, parse_mode='Markdown')
            except Exception:
                pass
            return

        if step == 'ADMIN_CANCEL_PLAN_USER_ID':
            if not text.strip().isdigit():
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗡𝘂𝗺𝗲𝗿𝗶𝗰 𝗨𝘀𝗲𝗿 𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
                return
            target_uid_tg = int(text.strip())
            pending_state.pop(user_id, None)

            p = plan_progress.get(target_uid_tg)
            u_rec = get_user(target_uid_tg)

            if not p and u_rec.get('activePlan') in ('None', 'Cancelled', 'Completed', 'Expired'):
                bot.send_message(
                    user_id,
                    f"⚠️ 𝗨𝘀𝗲𝗿 `{target_uid_tg}` 𝗸𝗮 𝗸𝗼𝗶 𝗮𝗰𝘁𝗶𝘃𝗲 𝗽𝗹𝗮𝗻 𝗻𝗮𝗵𝗶 𝗵𝗮𝗶 (𝗦𝘁𝗮𝘁𝘂𝘀: `{u_rec.get('activePlan')}`).",
                    parse_mode='Markdown'
                )
                return

            if p:
                rem = max(0, int(p['total_likes']) - int(p.get('delivered_total', 0)))
                info_txt = (
                    f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                    f"   📦 𝗨𝗦𝗘𝗥 𝗣𝗟𝗔𝗡 𝗗𝗘𝗧𝗔𝗜𝗟𝗦\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"👤 𝗨𝘀𝗲𝗿 𝗜𝗗 : `{target_uid_tg}`\n"
                    f"🎮 𝗙𝗙 𝗨𝗜𝗗 : `{p['uid']}`\n"
                    f"📦 𝗣𝗹𝗮𝗻 : *{p['plan']}*\n"
                    f"📊 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗲𝗱 / 𝗧𝗼𝘁𝗮𝗹 : `{int(p.get('delivered_total', 0)):,} / {int(p['total_likes']):,}`\n"
                    f"❤️ 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 : `{rem:,}`\n"
                    f"📌 𝗦𝘁𝗮𝘁𝘂𝘀 : `{p.get('status', 'Active')}`\n\n"
                    f"👇 𝗣𝗹𝗮𝗻 𝗰𝗮𝗻𝗰𝗲𝗹 𝗸𝗮𝗿𝗻𝗲 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗻𝗲𝗲𝗰𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗱𝗮𝗯𝗮𝗲𝗶𝗻:"
                )
            else:
                info_txt = (
                    f"📦 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{target_uid_tg}`\n"
                    f"• *𝗣𝗹𝗮𝗻:* *{u_rec.get('activePlan')}*\n"
                    f"• *𝗘𝘅𝗽𝗶𝗿𝘆:* `{u_rec.get('planExpiry')}`\n\n"
                    f"👇 𝗣𝗹𝗮𝗻 𝗰𝗮𝗻𝗰𝗲𝗹 𝗸𝗮𝗿𝗻𝗲 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗻𝗲𝗲𝗰𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗱𝗮𝗯𝗮𝗲𝗶𝗻:"
                )

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚫 𝗖𝗮𝗻𝗰𝗲𝗹 𝗣𝗹𝗮𝗻", callback_data=f"do_cancel_plan_{target_uid_tg}"))
            bot.send_message(user_id, info_txt, parse_mode='Markdown', reply_markup=markup)
            return

        if step == 'CREATE_REDEEM_CODE':
            state['code'] = text.strip()
            state['step'] = 'CREATE_REDE_AMOUNT'
            bot.send_message(user_id, "💰 𝗔𝗯 𝗶𝘀 𝗰𝗼𝗱𝗲 𝗽𝗮𝗿 𝗺𝗶𝗹𝗻𝗲 𝘄𝗮𝗹𝗮 **𝗔𝗺𝗼𝘂𝗻𝘁 (𝗥𝘀.)** 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:", parse_mode='Markdown')
            return
        elif step == 'CREATE_REDE_AMOUNT':
            try:
                amount = float(text.strip())
                if amount <= 0:
                    raise ValueError()
                state['amount'] = amount
                state['step'] = 'CREATE_REDEEM_MAX_USERS'
                bot.send_message(user_id, "👥 𝗞𝗶𝘁𝗻𝗲 **𝗨𝘀𝗲𝗿𝘀** 𝘆𝗲 𝗰𝗼𝗱𝗲 𝘂𝘀𝗲 𝗸𝗮𝗿 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻? (𝗠𝗮𝘅 𝘂𝘀𝗲𝘀):", parse_mode='Markdown')
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗮𝗺𝗼𝘂𝗻𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return
        elif step == 'CREATE_REDEEM_MAX_USERS':
            try:
                max_uses = int(text.strip())
                if max_uses <= 0:
                    raise ValueError()
                state['max_uses'] = max_uses
                state['step'] = 'CREATE_REDEEM_HOURS'
                bot.send_message(user_id, "⏰ 𝗞𝗶𝘁𝗻𝗲 **𝗚𝗵𝗮𝗻𝘁𝗲 (𝗛𝗼𝘂𝗿𝘀)** 𝘁𝗮𝗸 𝘆𝗲 𝗰𝗼𝗱𝗲 𝘃𝗮𝗹𝗶𝗱 𝗿𝗮𝗵𝗲𝗴𝗮?", parse_mode='Markdown')
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗹𝗶𝗺𝗶𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return
        elif step == 'CREATE_REDEEM_HOURS':
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
                bot.send_message(
                    user_id,
                    f"✅ *𝗥𝗘𝗗𝗘𝗘𝗠 𝗖𝗢𝗗𝗘 𝗖𝗥𝗘𝗔𝗧𝗘𝗗!* 🎉\n━━━━━━━━━━━━━━━━━━━\n🎁 𝗖𝗼𝗱𝗲: `{code}`\n💰 𝗔𝗺𝗼𝘂𝗻𝘁: `Rs. {amount}`\n👥 𝗠𝗮𝘅 𝗨𝘀𝗲𝗿𝘀: `{max_uses}`\n⏰ 𝗩𝗮𝗹𝗶𝗱: `{hours} 𝗛𝗼𝘂𝗿𝘀`\n━━━━━━━━━━━━━━━━━━━",
                    parse_mode='Markdown'
                )
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗵𝗼𝘂𝗿𝘀 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return

        if step == 'ADD_BAL_UID':
            try:
                target_uid = int(text)
                pending_state[user_id] = {'step': 'ADD_BAL_AMOUNT', 'targetUid': target_uid}
                bot.send_message(user_id, "✍️ 𝗞𝗶𝘁𝗻𝗮 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝗮𝗱𝗱 𝗸𝗮𝗿𝗻𝗮 𝗵𝗮𝗶? 𝗔𝗺𝗼𝘂𝗻𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗨𝘀𝗲𝗿 𝗜𝗗 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return

        if step == 'ADD_BAL_AMOUNT':
            try:
                amount = int(text)
                target_uid = state['targetUid']
                pending_state.pop(user_id, None)

                target_user = get_user(target_uid)
                target_user['balance'] += amount

                bot.send_message(user_id, f"✅ 𝗨𝘀𝗲𝗿 `{target_uid}` 𝗸𝗲 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗺𝗲 *𝗥𝘀. {amount}* 𝗮𝗱𝗱 𝗵𝗼 𝗴𝗮𝘆𝗮! 𝗡𝗲𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: *𝗥𝘀. {target_user['balance']}*", parse_mode='Markdown')
                try:
                    bot.send_message(target_uid, f"🎉 *𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗔𝗱𝗱𝗲𝗱 𝗯𝘆 𝗔𝗱𝗺𝗶𝗻!* ✨\n\n💰 𝗔𝗮𝗽𝗸𝗲 𝘄𝗮𝗹𝗹𝗲𝘁 𝗺𝗲 *𝗥𝘀. {amount}* 𝗮𝗱𝗱 𝗵𝗼 𝗴𝗮𝘆𝗮 𝗵𝗮𝗶!\n💼 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: *𝗥𝘀. {target_user['balance']}*", parse_mode='Markdown')
                except Exception:
                    pass
            except ValueError:
                bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗮𝗺𝗼𝘂𝗻𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return

        if step == 'PERSONAL_MSG_UID':
            state['target_id'] = text.strip()
            state['step'] = 'PERSONAL_MSG_TEXT'
            bot.send_message(user_id, "✍️ 𝗔𝗯 𝘄𝗼𝗵 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝘁𝘆𝗽𝗲 𝗸𝗮𝗿𝗲𝗶𝗻 𝗷𝗼 𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗼 𝗯𝗵𝗲𝗷𝗻𝗮 𝗵𝗮𝗶:")
            return

        if step == 'PERSONAL_MSG_TEXT':
            target_str = state['target_id']
            msg_content = text
            pending_state.pop(user_id, None)
            try:
                target_id = int(target_str)
                bot.send_message(target_id, f"💬 *𝗔𝗱𝗺𝗶𝗻 𝗠𝗲𝘀𝘀𝗮𝗴𝗲:*\n\n{msg_content}", parse_mode='Markdown')
                bot.send_message(user_id, f"✅ 𝗠𝗲𝘀𝘀𝗮𝗴𝗲 𝘀𝗲𝗻𝘁 𝘁𝗼 `{target_id}`!")
            except Exception as e:
                bot.send_message(user_id, f"❌ 𝗠𝗲𝘀𝘀𝗮𝗴𝗲 𝗱𝗲𝗹𝗶𝘃𝗲𝗿𝘆 𝗳𝗮𝗶𝗹𝗲𝗱: `{str(e)}`", parse_mode='Markdown')
            return

    if isinstance(state, dict) and state.get('step') == 'WAITING_FOR_AMOUNT':
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(user_id, "❌ 𝗦𝗮𝗵𝗶 𝗮𝗺𝗼𝘂𝗻𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝗺𝗲 𝗱𝗮𝗮𝗹𝗲𝗶𝗻:")
            return
        pending_state[user_id] = {'step': 'WAITING_FOR_UTR', 'amount': amount}

        instructions = (
            f"💳 *𝗣𝗔𝗬𝗠𝗘𝗡𝗧 & 𝗨𝗧𝗥 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡𝗦* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"1️⃣ *𝗨𝗣𝗜 𝗜𝗗:* `{bot_settings['upiId']}`\n"
            f"2️⃣ *𝗔𝗺𝗼𝘂𝗻𝘁:* `Rs. {amount}`\n\n"
            f"📲 *𝗞𝗮𝗶𝘀𝗲 𝗽𝗮𝘆 𝗸𝗮𝗿𝗲𝗶𝗻?*\n"
            f"• 𝗨𝗽𝗮𝗿 𝗱𝗶 𝗴𝗮𝘆𝗶 𝗨𝗣𝗜 𝗜𝗗 𝗽𝗮𝗿 𝗲𝘅𝗮𝗰𝘁 *𝗥𝘀. {amount}* 𝗽𝗮𝘆 𝗸𝗮𝗿𝗲𝗶𝗻.\n"
            f"• 𝟭𝟮-𝗱𝗶𝗴𝗶𝘁 𝗨𝗧𝗥 / 𝗧𝗿𝗮𝗻𝘀𝗮𝗰𝘁𝗶𝗼𝗻 𝗜𝗗 𝗻𝗲𝗲𝗰𝗵𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.\n\n"
            f"⏳ *𝗔𝗽𝗻𝗮 𝗨𝗧𝗥 𝗻𝗲𝗲𝗰𝗵𝗲 𝘁𝘆𝗽𝗲 𝗸𝗮𝗿𝗸𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:*"
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

        bot.send_message(user_id, "⏳ *𝗨𝗧𝗥 𝗿𝗲𝗰𝗲𝗶𝘃𝗲𝗱! 𝗔𝗱𝗺𝗶𝗻 𝘃𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗸𝗲 𝗯𝗮𝗮𝗱 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝗮𝗱𝗱 𝗵𝗼𝗴𝗮.*", parse_mode='Markdown')

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲", callback_data=f"approve_{dep_id}"),
            types.InlineKeyboardButton("❌ 𝗥𝗲𝗷𝗲𝗰𝘁", callback_data=f"reject_{dep_id}")
        )
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 *𝗡𝗮𝘆𝗮 𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗥𝗲𝗾𝘂𝗲𝘀𝘁* 💳\n\n"
                f"👤 𝗡𝗮𝗺𝗲: {first_name}\n"
                f"🆔 𝗨𝘀𝗲𝗿 𝗜𝗗: `{user_id}`\n"
                f"🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: {username}\n"
                f"💰 𝗔𝗺𝗼𝘂𝗻𝘁: `Rs. {amount}`\n"
                f"🔢 𝗨𝗧𝗥: `{utr}`",
                parse_mode='Markdown',
                reply_markup=markup
            )
        except Exception:
            pass
        return

    if user_id in pending_uid:
        order = pending_uid.pop(user_id)
        user = get_user(user_id)
        target_uid = text.strip()

        if not target_uid.isdigit():
            bot.send_message(user_id, "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗨𝗜𝗗 𝘀𝗶𝗿𝗳 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗺𝗲𝗶𝗻 𝗵𝗼𝗻𝗮 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", parse_mode='Markdown')
            return

        now = now_ist()
        load_msg = bot.send_message(user_id, "⏳ *𝗢𝗿𝗱𝗲𝗿 𝗽𝗿𝗼𝗰𝗲𝘀𝘀 𝗵𝗼 𝗿𝗮𝗵𝗮 𝗵𝗮𝗶 𝗮𝘂𝗿 𝗔𝗣𝗜 𝘀𝗲 𝗹𝗶𝗸𝗲𝘀 𝗯𝗵𝗲𝗷𝗲 𝗷𝗮 𝗿𝗮𝗵𝗲 𝗵𝗮𝗶𝗻...*", parse_mode='Markdown')

        if order['price'] > 0:
            user['balance'] -= order['price']
        if order['price'] == 6:
            user['lastDemoClaim'] = time.time()
        if order.get('isRefPlan'):
            user['refPlanClaimed'] = True

        total_target = int(order['total_likes'])
        try:
            info = activate_user_plan(
                cust_id=user_id,
                target_uid=target_uid,
                plan_name=order['plan'],
                total_likes_target=total_target,
                days=order.get('days'),
                daily_cap=order.get('daily_cap'),
                price_paid=order['price'],
                username=message.from_user.username or 'None',
                region='ind',
                send_initial_like=True,
                now_dt=now,
                is_demo=bool(order.get('isDemo', False))
            )
        except Exception:
            if order['price'] > 0:
                user['balance'] += order['price']
            if order.get('isRefPlan'):
                user['refPlanClaimed'] = False
            user['activePlan'] = 'None'
            user['planExpiry'] = 'N/A'
            plan_progress.pop(user_id, None)
            try:
                bot.edit_message_text(
                    "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗔𝗮𝗽𝗸𝗮 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝘄𝗮𝗽𝗮𝘀 𝗮𝗱𝗱 𝗸𝗮𝗿 𝗱𝗶𝘆𝗮 𝗴𝗮𝘆𝗮 𝗵𝗮𝗶.",
                    user_id, load_msg.message_id, parse_mode='Markdown'
                )
            except Exception:
                bot.send_message(user_id, "❌ *𝗨𝗜𝗗 𝗴𝗮𝗹𝗮𝘁 𝗵𝗮𝗶!* 𝗔𝗮𝗽𝗸𝗮 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝘄𝗮𝗽𝗮𝘀 𝗮𝗱𝗱 𝗸𝗮𝗿 𝗱𝗶𝘆𝗮 𝗴𝗮𝘆𝗮 𝗵𝗮𝗶.", parse_mode='Markdown')
            return

        before_txt = f"{info['likes_before']:,}" if isinstance(info['likes_before'], int) else "N/A"
        after_txt = f"{info['likes_after']:,}" if isinstance(info['likes_after'], int) else "N/A"
        refund_line = f"💸 𝗥𝗲𝗳𝘂𝗻𝗱𝗲𝗱 : `Rs. {info['refunded_amount']}`\n" if info.get('refunded_amount', 0) > 0 else ""

        success_text = (
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "   ✅ 𝗣𝗟𝗔𝗡 𝗢𝗥𝗗𝗘𝗥 𝗥𝗘𝗣𝗢𝗥𝗧\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"👤 𝗡𝗮𝗺𝗲 : `{info['player_name']}`\n"
            f"⭐ 𝗟𝗲𝘃𝗲𝗹 : `{info['player_level']}`\n"
            f"🆔 𝗨𝗜𝗗 : `{target_uid}`\n\n"
            f"🎁 𝗕𝗲𝗳𝗼𝗿𝗲 𝗟𝗶𝗸𝗲𝘀 : `{before_txt}`\n"
            f"💭 𝗔𝗳𝘁𝗲𝗿 𝗟𝗶𝗸𝗲𝘀 : `{after_txt}`\n"
            f"📡 𝗔𝗣𝗜 𝗥𝗲𝘀𝘂𝗹𝘁 : `{info['api_status_text']}`\n"
            f"{refund_line}\n"
            f"📦 𝗣𝗹𝗮𝗻 : *{order['plan']}*\n"
            f"💖 𝗧𝗼𝘁𝗮𝗹 𝗣𝗹𝗮𝗻 𝗟𝗶𝗸𝗲𝘀 : `{info['total_likes']:,}`\n"
            f"❤️ 𝗥𝗲𝗮𝗹 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗲𝗱 : `{info['delivered_real']:,}`\n"
            f"💎 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗟𝗶𝗸𝗲𝘀 : `{info['remaining_likes']:,}`\n"
            f"💰 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 : `Rs. {user['balance']}`\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        try:
            bot.edit_message_text(success_text, user_id, load_msg.message_id, parse_mode='Markdown')
        except Exception:
            bot.send_message(user_id, success_text, parse_mode='Markdown')

        try:
            bot.send_message(
                ADMIN_ID,
                f"🚨 *𝗡𝗮𝘆𝗮 𝗣𝗹𝗮𝗻 𝗣𝘂𝗿𝗰𝗵𝗮𝘀𝗲 / 𝗨𝗻𝗹𝗼𝗰𝗸!* 🛒\n\n"
                f"👤 *𝗡𝗮𝗺𝗲:* {message.from_user.first_name}\n"
                f"🆔 *𝗨𝘀𝗲𝗿 𝗜𝗗:* `{user_id}`\n"
                f"🔗 *𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:* @{message.from_user.username or 'None'}\n"
                f"📦 *𝗣𝗹𝗮𝗻:* *{order['plan']}*\n"
                f"💰 *𝗣𝗮𝗶𝗱:* `Rs. {order['price']}`\n"
                f"🎮 *𝗨𝗜𝗗:* `{target_uid}` (`{info['player_name']}`)\n"
                f"❤️ *𝗥𝗲𝗮𝗹 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗲𝗱 / 𝗥𝗲𝗺:* `{info['delivered_real']:,} / {info['remaining_likes']:,}`",
                parse_mode='Markdown'
            )
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if call.from_user.username:
        get_user(user_id)['username'] = call.from_user.username

    if data.startswith('dl_'):
        bot.answer_callback_query(call.id, "𝗜𝗗 𝗜𝗻𝗳𝗼 𝗺𝗲𝗶𝗻 𝗨𝗜𝗗 𝗱𝗶𝗿𝗲𝗰𝘁 𝗯𝗵𝗲𝗷𝗲𝗶𝗻.")
        return

    if data == 'guild_plan_99':
        user = get_user(user_id)
        if user['balance'] < 99:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟵𝟵 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
            return
        pending_guild_order[user_id] = {
            'step': 'WAITING_GAME_UID',
            'plan': '𝗥𝘀. 𝟵𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 𝗣𝗹𝗮𝗻',
            'price': 99,
            'bots': '4 Bots',
            'glory': '2,53,500'
        }
        bot.send_message(user_id, "🎮 *Apna **Game UID** bhejein:*", parse_mode='Markdown')
        return

    if data == 'guild_plan_149':
        user = get_user(user_id)
        if user['balance'] < 149:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟭𝟰𝟵 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
            return
        pending_guild_order[user_id] = {
            'step': 'WAITING_GAME_UID',
            'plan': '𝗥𝘀. 𝟭𝟰𝟵 𝗚𝘂𝗶𝗹𝗱 𝗚𝗹𝗼𝗿𝘆 𝗣𝗹𝗮𝗻',
            'price': 149,
            'bots': None,
            'glory': '7,21,900'
        }
        bot.send_message(user_id, "🎮 *Apna **Game UID** bhejein:*", parse_mode='Markdown')
        return

    if data == 'admin_set_time':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADMIN_SET_CUSTOM_TIME'}
            cur_t = bot_settings.get('customAutoRunTime') or 'Not Set'
            bot.send_message(
                user_id,
                f"🕒 *𝗦𝗘𝗧 𝗖𝗨𝗦𝗧𝗢𝗠 𝗔𝗨𝗧𝗢𝗟𝗜𝗞𝗘 𝗧𝗜𝗠𝗘 (𝗜𝗦𝗧)* ⏰\n\n"
                f"• 𝗙𝗶𝘅𝗲𝗱 𝗗𝗮𝗶𝗹𝘆 𝗥𝘂𝗻: `05:00 AM IST`\n"
                f"• 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗖𝘂𝘀𝘁𝗼𝗺 𝗧𝗶𝗺𝗲: `{cur_t}`\n\n"
                f"✍️ 𝗡𝗮𝘆𝗮 𝘁𝗶𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `16:00` 𝘆𝗮 `04:00 PM` — 𝗶𝘀 𝘁𝗶𝗺𝗲 𝗽𝗮𝗿 **𝗔𝗣𝗜 𝘀𝗮𝗯𝗵𝗶 𝗮𝗰𝘁𝗶𝘃𝗲 𝗽𝗹𝗮𝗻 𝘄𝗮𝗹𝗲 𝘂𝘀𝗲𝗿𝘀 𝗸𝗼 𝗹𝗶𝗸𝗲 𝗱𝗲𝗴𝗶** 𝗮𝘂𝗿 𝘂𝗻𝗸𝗼 `AᴜᴛᴏLɪᴋᴇꜱ Dᴀɪʟʏ Rᴜɴ Cᴏᴍᴘʟᴇᴛᴇᴅ` 𝗸𝗮 𝗿𝗲𝗽𝗼𝗿𝘁 𝗺𝗶𝗹𝗲𝗴𝗮, 𝘆𝗮 `off` 𝗹𝗶𝗸𝗵𝗲𝗶𝗻):",
                parse_mode='Markdown'
            )
    elif data == 'admin_sent_like':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADMIN_SENT_LIKE_INPUT'}
            bot.send_message(
                user_id,
                "❤️ *𝗦𝗘𝗡𝗧 𝗟𝗜𝗞𝗘* ⚡\n\n𝗝𝗶𝘀 𝗨𝗜𝗗 𝗽𝗮𝗿 𝗹𝗶𝗸𝗲 𝗯𝗵𝗲𝗷𝗻𝗮 𝗵𝗮𝗶 𝘂𝘀𝗸𝗮 **𝗨𝗜𝗗** 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `4232090116` 𝘆𝗮 `4232090116 ind`):",
                parse_mode='Markdown'
            )
    elif data == 'admin_set_active_plan':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADMIN_PLAN_USER_ID'}
            bot.send_message(
                user_id,
                "📦 *𝗔𝗖𝗧𝗜𝗩𝗘 𝗣𝗟𝗔𝗡 𝗦𝗘𝗧𝗨𝗣* 🛠️\n\n𝗦𝘁𝗲𝗽 𝟭/𝟯: 𝗝𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗮 𝗽𝗹𝗮𝗻 𝗮𝗰𝘁𝗶𝘃𝗲 𝗸𝗮𝗿𝗻𝗮 𝗵𝗮𝗶 𝘂𝘀𝗸𝗶 **𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗨𝘀𝗲𝗿 𝗜𝗗** 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:",
                parse_mode='Markdown'
            )
    elif data == 'admin_cancel_plan':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADMIN_CANCEL_PLAN_USER_ID'}
            bot.send_message(
                user_id,
                "🚫 *𝗣𝗟𝗔𝗡 𝗖𝗔𝗡𝗖𝗘𝗟* 🛠️\n\n𝗝𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗮 𝗽𝗹𝗮𝗻 𝗰𝗮𝗻𝗰𝗲𝗹 𝗸𝗮𝗿𝗻𝗮 𝗵𝗮𝗶 𝘂𝘀𝗸𝗶 **𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗨𝘀𝗲𝗿 𝗜𝗗** 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:",
                parse_mode='Markdown'
            )
    elif data.startswith('do_cancel_plan_'):
        if user_id == ADMIN_ID:
            try:
                target_tg = int(data.replace('do_cancel_plan_', '').strip())
            except ValueError:
                bot.answer_callback_query(call.id, "❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗨𝘀𝗲𝗿 𝗜𝗗", show_alert=True)
                return
            res = cancel_user_plan(target_tg)
            try:
                bot.edit_message_text(
                    f"🚫 *𝗣𝗟𝗔𝗡 𝗖𝗔𝗡𝗖𝗘𝗟𝗟𝗘𝗗!* ✅\n\n"
                    f"👤 𝗨𝘀𝗲𝗿 𝗜𝗗 : `{target_tg}`\n"
                    f"🎮 𝗙𝗙 𝗨𝗜𝗗 : `{res['uid']}`\n"
                    f"📦 𝗣𝗹𝗮𝗻 : *{res['plan_name']}*\n"
                    f"📌 𝗔𝗯 𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗼 𝗹𝗶𝗸𝗲 𝗺𝗶𝗹𝗻𝗮 𝗯𝗮𝗻𝗱 𝗵𝗼 𝗴𝗮𝘆𝗮 𝗵𝗮𝗶.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            try:
                bot.send_message(
                    target_tg,
                    f"🚫 *𝗔𝗮𝗽𝗸𝗮 𝗟𝗶𝗸𝗲 𝗣𝗹𝗮𝗻 𝗖𝗮𝗻𝗰𝗲𝗹 𝗞𝗮𝗿 𝗗𝗶𝘆𝗮 𝗚𝗮𝘆𝗮 𝗛𝗮𝗶!* ⚠️\n\n"
                    f"📦 𝗣𝗹𝗮𝗻 : *{res['plan_name']}*\n"
                    f"🎮 𝗨𝗜𝗗 : `{res['uid']}`\n"
                    f"ℹ️ 𝗞𝗶𝘀𝗶 𝘀𝗮𝘄𝗮𝗹 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗔𝗱𝗺𝗶𝗻 𝘀𝗲 𝘀𝗮𝗺𝗽𝗮𝗿𝗸 𝗸𝗮𝗿𝗲𝗶𝗻.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ Plan Cancelled!")
    elif data == 'admin_set_api':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADMIN_SET_API_URL'}
            bot.send_message(
                user_id,
                f"🔗 *𝗖𝗛𝗔𝗡𝗚𝗘 / 𝗔𝗗𝗗 𝗟𝗜𝗞𝗘 𝗔𝗣𝗜* ⚡\n\n𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗔𝗣𝗜:\n`{LIKE_API_URL}`\n\n✍️ 𝗡𝗮𝘆𝗮 𝗔𝗣𝗜 𝗨𝗥𝗟 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `https://ijapi.vercel.app/like`):",
                parse_mode='Markdown'
            )
    elif data == 'admin_create_redeem':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'CREATE_REDEEM_CODE'}
            bot.send_message(user_id, "🎁 𝗡𝗮𝘆𝗮 **𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲** 𝘁𝗲𝘅𝘁/𝗻𝗮𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `FREE10`):", parse_mode='Markdown')
    elif data == 'admin_add_channel':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'ADD_CHANNEL'
            bot.send_message(user_id, "📢 𝗡𝗮𝘆𝗮 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻 (𝗷𝗮𝗶𝘀𝗲 `@newchannel`):", parse_mode='Markdown')
    elif data == 'admin_remove_channel':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'REMOVE_CHANNEL'
            ch_list = "\n".join(bot_settings['requiredChannels'])
            bot.send_message(user_id, f"❌ 𝗝𝗼 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗵𝗮𝘁𝗮𝗻𝗮 𝗵𝗮𝗶 𝘂𝘀𝗸𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:\n\n𝗔𝗰𝘁𝗶𝘃𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:\n{ch_list}", parse_mode='Markdown')
    elif data == 'admin_add_balance':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'ADD_BAL_UID'}
            bot.send_message(user_id, "🆔 𝗝𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗲 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗺𝗲 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝗮𝗱𝗱 𝗸𝗮𝗿𝗻𝗮 𝗵𝗮𝗶, 𝘂𝘀𝗸𝗶 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗡𝘂𝗺𝗲𝗿𝗶𝗰 𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
    elif data == 'admin_set_refer':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'SET_REFER_BONUS'
            bot.send_message(user_id, f"🎁 𝗡𝗮𝘆𝗮 𝗿𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗯𝗼𝗻𝘂𝘀 𝗮𝗺𝗼𝘂𝗻𝘁 (𝗥𝘀.) 𝗱𝗮𝗮𝗹𝗲𝗶𝗻 (𝗖𝘂𝗿𝗿𝗲𝗻𝘁: `Rs. {bot_settings['referralBonus']}`):", parse_mode='Markdown')
    elif data == 'admin_personal_msg':
        if user_id == ADMIN_ID:
            pending_state[user_id] = {'step': 'PERSONAL_MSG_UID'}
            bot.send_message(user_id, "🆔 𝗝𝗶𝘀 𝘂𝘀𝗲𝗿 𝗸𝗼 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗯𝗵𝗲𝗷𝗻𝗮 𝗵𝗮𝗶, 𝘂𝘀𝗸𝗶 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗡𝘂𝗺𝗲𝗿𝗶𝗰 𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
    elif data == 'admin_view_plans':
        if user_id == ADMIN_ID:
            if not plan_progress:
                bot.answer_callback_query(call.id, "⚠️ 𝗞𝗼𝗶 𝗯𝗵𝗶 𝗽𝗹𝗮𝗻 𝗿𝗲𝗰𝗼𝗿𝗱 𝗻𝗮𝗵𝗶 𝗵𝗮𝗶!", show_alert=True)
            else:
                chunks = []
                header = "📊 *𝗔𝗟𝗟 𝗣𝗟𝗔𝗡𝗦 & 𝗨𝗜𝗗𝘀 𝗟𝗜𝗦𝗧* 📋\n━━━━━━━━━━━━━━━━━━━\n"
                cur = header
                for cust_id, p in plan_progress.items():
                    deliv = int(p.get('delivered_total', 0))
                    tot = int(p.get('total_likes', 0))
                    rem = max(0, tot - deliv)
                    entry = (
                        f"👤 𝗨𝘀𝗲𝗿 𝗜𝗗 : `{cust_id}`\n"
                        f"🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲 : @{p['username']}\n"
                        f"🎮 𝗙𝗙 𝗨𝗜𝗗 : `{p['uid']}`\n"
                        f"💐 𝗡𝗮𝗺𝗲 : `{p.get('player_name', 'Unknown')}`\n"
                        f"📦 𝗣𝗹𝗮𝗻 : *{p['plan']}*\n"
                        f"❤️ 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗲𝗱 / 𝗥𝗲𝗺 : `{deliv:,} / {rem:,}` (𝗧𝗼𝘁𝗮𝗹: `{tot:,}`)\n"
                        f"📌 𝗦𝘁𝗮𝘁𝘂𝘀 : `{p.get('status', 'Active')}`\n"
                        f"⏰ 𝗘𝘅𝗽𝗶𝗿𝘆 : `{p['expiry'].strftime('%Y-%m-%d %H:%M:%S')}`\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                    )
                    if len(cur) + len(entry) > 3800:
                        chunks.append(cur)
                        cur = header + entry
                    else:
                        cur += entry
                chunks.append(cur)
                for ch_msg in chunks:
                    bot.send_message(user_id, ch_msg, parse_mode='Markdown')
    elif data == 'admin_broadcast':
        if user_id == ADMIN_ID:
            pending_state[user_id] = 'BROADCAST_MSG'
            bot.send_message(user_id, "📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:")
    elif data.startswith('approve_'):
        if user_id == ADMIN_ID:
            dep_id = data.split('_', 1)[1]
            dep = pending_deposits.pop(dep_id, None)
            if dep:
                user = get_user(dep['userId'])
                user['balance'] += dep['amount']
                try:
                    bot.edit_message_text(f"✅ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱! `Rs. {dep['amount']}` 𝗮𝗱𝗱𝗲𝗱 𝗳𝗼𝗿 `{dep['userId']}`.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                    bot.send_message(dep['userId'], f"🎉 *𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱!* ✨\n\n💰 `Rs. {dep['amount']}` 𝘄𝗮𝗹𝗹𝗲𝘁 𝗺𝗲 𝗮𝗱𝗱 𝗵𝗼 𝗴𝗮𝘆𝗲 𝗵𝗮𝗶𝗻!", parse_mode='Markdown')
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "⚠️ 𝗣𝗲𝗵𝗹𝗲 𝗵𝗶 𝗽𝗿𝗼𝗰𝗲𝘀𝘀 𝗵𝗼 𝗰𝗵𝘂𝗸𝗶 𝗵𝗮𝗶.", show_alert=True)
    elif data.startswith('reject_'):
        if user_id == ADMIN_ID:
            dep_id = data.split('_', 1)[1]
            dep = pending_deposits.pop(dep_id, None)
            if dep:
                try:
                    bot.edit_message_text(f"❌ 𝗥𝗲𝗷𝗲𝗰𝘁𝗲𝗱 𝗽𝗮𝘆𝗺𝗲𝗻𝘁 𝗳𝗼𝗿 `{dep['userId']}`.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                    bot.send_message(dep['userId'], f"❌ *𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗥𝗲𝗷𝗲𝗰𝘁𝗲𝗱!* ⚠️\n\n𝗨𝗧𝗥 𝘃𝗲𝗿𝗶𝗳𝘆 𝗻𝗮𝗵𝗶 𝗵𝗼 𝗽𝗮𝘆𝗮.", parse_mode='Markdown')
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "⚠️ 𝗣𝗲𝗵𝗹𝗲 𝗵𝗶 𝗽𝗿𝗼𝗰𝗲𝘀𝘀 𝗵𝗼 𝗰𝗵𝘂𝗸𝗶 𝗵𝗮𝗶.", show_alert=True)
    elif data == 'buy_demo':
        user = get_user(user_id)
        if user['balance'] >= 6:
            pending_uid[user_id] = {'plan': '𝗥𝘀. 𝟲 𝗗𝗲𝗺𝗼 𝗣𝗹𝗮𝗻', 'price': 6, 'total_likes': 220, 'days': 1, 'isDemo': True}
            bot.send_message(user_id, "🎮 *𝗔𝗽𝗻𝗮 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟲 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
    elif data == 'buy_59':
        user = get_user(user_id)
        if user['balance'] >= 59:
            pending_uid[user_id] = {'plan': '𝗥𝘀. 𝟱𝟵 𝗣𝗹𝗮𝗻 (𝟯,𝟯𝟬𝟬 𝗟𝗶𝗸𝗲𝘀)', 'price': 59, 'total_likes': 3300, 'days': 15}
            bot.send_message(user_id, "🎮 *𝗔𝗽𝗻𝗮 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟱𝟵 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
    elif data == 'buy_110':
        user = get_user(user_id)
        if user['balance'] >= 110:
            pending_uid[user_id] = {'plan': '𝗥𝘀. 𝟭𝟭𝟬 𝗣𝗹𝗮𝗻 (𝟲,𝟲𝟬𝟬 𝗟𝗶𝗸𝗲𝘀)', 'price': 110, 'total_likes': 6600, 'days': 30}
            bot.send_message(user_id, "🎮 *𝗔𝗽𝗻𝗮 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟭𝟭𝟬 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
    elif data == 'buy_ref_unlock':
        user = get_user(user_id)
        if user['refPlanClaimed']:
            bot.answer_callback_query(call.id, "❌ 𝗔𝗮𝗽 𝘆𝗲 𝗿𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝘂𝗻𝗹𝗼𝗰𝗸 𝗽𝗹𝗮𝗻 𝗽𝗲𝗵𝗹𝗲 𝗵𝗶 𝗰𝗹𝗮𝗶𝗺 𝗸𝗮𝗿 𝗰𝗵𝘂𝗸𝗲 𝗵𝗮𝗶𝗻!", show_alert=True)
            return
        if user['referrals'] >= 10:
            pending_uid[user_id] = {'plan': '𝟭𝟬 𝗥𝗲𝗳𝘀 𝗨𝗻𝗹𝗼𝗰𝗸 𝗣𝗹𝗮𝗻 (𝟭,𝟱𝟰𝟬 𝗟𝗶𝗸𝗲𝘀)', 'price': 0, 'total_likes': 1540, 'days': 7, 'isRefPlan': True}
            bot.send_message(user_id, "🎮 *𝗕𝗮𝗱𝗵𝗮𝗶 𝗵𝗼! 𝗣𝗹𝗮𝗻 𝘂𝗻𝗹𝗼𝗰𝗸𝗲𝗱. 𝗔𝗽𝗻𝗮 𝗙𝗿𝗲𝗲 𝗙𝗶𝗿𝗲 𝗨𝗜𝗗 𝗯𝗵𝗲𝗷𝗲𝗶𝗻:*", parse_mode='Markdown')
        else:
            needed = 10 - user['referrals']
            bot.answer_callback_query(call.id, f"❌ 𝗣𝗹𝗮𝗻 𝗹𝗼𝗰𝗸𝗲𝗱! {needed} 𝗮𝘂𝗿 𝗿𝗲𝗳𝗲𝗿𝗿𝗮𝗹𝘀 𝗰𝗵𝗮𝗵𝗶𝘆𝗲 (𝗧𝗼𝘁𝗮𝗹 𝟭𝟬).", show_alert=True)
    elif data == 'buy_cc_100':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ 𝗜 𝗔𝗴𝗿𝗲𝗲 & 𝗣𝗮𝘆 𝗥𝘀. 𝟭𝟬𝟬", callback_data='confirm_cc_100'))
        bot.send_message(
            user_id,
            "⚠️ *𝗖𝗖 𝗦𝗧𝗢𝗥𝗘 𝗥𝗨𝗟𝗘𝗦 & 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡𝗦* 🛒\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ 𝗡𝗮𝘆𝗮 𝗚𝗺𝗮𝗶𝗹 𝗯𝗮𝗻𝗮𝗸𝗮𝗿 𝗰𝗮𝗿𝗱 𝗮𝗱𝗱 𝗸𝗮𝗿 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻.\n"
            "2️⃣ 𝗖𝗮𝗿𝗱 𝟮𝟬 𝗺𝗶𝗻𝘂𝘁𝗲 𝗺𝗲 𝗲𝘅𝗽𝗶𝗿𝗲 𝗵𝗼𝗴𝗮, 𝘂𝘀𝘀𝗲 𝗽𝗲𝗵𝗹𝗲 𝘂𝘀𝗲 𝗸𝗮𝗿 𝗹𝗲𝗶𝗻.\n"
            "3️⃣ 𝗔𝗺𝗼𝘂𝗻𝘁: `Rs. 100`\n"
            "4️⃣ 𝗣𝗿𝗼𝗼𝗳 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗰𝗵𝗲𝗰𝗸 𝗸𝗮𝗿𝗲𝗶𝗻: https://t.me/eraningwithask\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 𝗡𝗶𝗰𝗵𝗲 𝗱𝗶𝘆𝗲 𝗴𝗮𝘆𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗽𝗮𝗿 𝗰𝗹𝗶𝗰𝗸 𝗸𝗮𝗿𝗲𝗶𝗻:",
            parse_mode='Markdown',
            reply_markup=markup
        )
    elif data == 'buy_cc_199':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ 𝗜 𝗔𝗴𝗿𝗲𝗲 & 𝗣𝗮𝘆 𝗥𝘀. 𝟭𝟵𝟵", callback_data='confirm_cc_199'))
        bot.send_message(
            user_id,
            "⚠️ *𝗖𝗖 𝗦𝗧𝗢𝗥𝗘 𝗥𝗨𝗟𝗘𝗦 & 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡𝗦* ✨\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ 𝗡𝗮𝘆𝗮 𝗚𝗺𝗮𝗶𝗹 𝗯𝗮𝗻𝗮𝗸𝗮𝗿 𝗰𝗮𝗿𝗱 𝗮𝗱𝗱 𝗸𝗮𝗿 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻.\n"
            "2️⃣ 𝗖𝗮𝗿𝗱 𝟮𝟬 𝗺𝗶𝗻𝘂𝘁𝗲 𝗺𝗲 𝗲𝘅𝗽𝗶𝗿𝗲 𝗵𝗼𝗴𝗮, 𝘂𝘀𝘀𝗲 𝗽𝗲𝗵𝗹𝗲 𝘂𝘀𝗲 𝗸𝗮𝗿 𝗹𝗲𝗶𝗻.\n"
            "3️⃣ 𝗔𝗺𝗼𝘂𝗻𝘁: `Rs. 199`\n"
            "4️⃣ 𝗣𝗿𝗼𝗼𝗳 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗰𝗵𝗲𝗰𝗸 𝗸𝗮𝗿𝗲𝗶𝗻: https://t.me/eraningwithask\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👇 𝗡𝗶𝗰𝗵𝗲 𝗱𝗶𝘆𝗲 𝗴𝗮𝘆𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗽𝗮𝗿 𝗰𝗹𝗶𝗰𝗸 𝗸𝗮𝗿𝗲𝗶𝗻:",
            parse_mode='Markdown',
            reply_markup=markup
        )
    elif data == 'confirm_cc_100':
        user = get_user(user_id)
        if user['balance'] >= 100:
            user['balance'] -= 100
            success_text = (
                f"✅ *𝗖𝗖 𝗦𝗧𝗢𝗥𝗘 𝗢𝗥𝗗𝗘𝗥 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 𝗣𝗹𝗮𝗻: *𝗥𝘀. 𝟭𝟬𝟬 𝗖𝗖 𝗣𝗹𝗮𝗻 (𝟮𝗸)*\n"
                f"💼 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: `Rs. {user['balance']}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *𝟭𝟬 𝗺𝗶𝗻𝘂𝘁𝗲 𝗺𝗲 𝗰𝗮𝗿𝗱 𝘆𝗮𝗵𝗶𝗻 𝗯𝗼𝘁 𝗽𝗲 𝗺𝗶𝗹 𝗷𝗮𝘆𝗲𝗴𝗮!* 🚀\n"
                f"🛠️ *𝗞𝗼𝗶 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝗵𝗼 𝘁𝗼𝗵 𝗮𝗱𝗺𝗶𝗻 ({ADMIN_USERNAME}) 𝗸𝗼 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗸𝗮𝗿𝗻𝗮.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟭𝟬𝟬 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)
    elif data == 'confirm_cc_199':
        user = get_user(user_id)
        if user['balance'] >= 199:
            user['balance'] -= 199
            success_text = (
                f"✅ *𝗖𝗖 𝗦𝗧𝗢𝗥𝗘 𝗢𝗥𝗗𝗘𝗥 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 𝗣𝗹𝗮𝗻: *𝗥𝘀. 𝟭𝟵𝟵 𝗖𝗖 𝗣𝗹𝗮𝗻 (𝟱𝗸)*\n"
                f"💼 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: `Rs. {user['balance']}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ *𝟭𝟬 𝗺𝗶𝗻𝘂𝘁𝗲 𝗺𝗲 𝗰𝗮𝗿𝗱 𝘆𝗮𝗵𝗶𝗻 𝗯𝗼𝘁 𝗽𝗲 𝗺𝗶𝗹 𝗷𝗮𝘆𝗲𝗴𝗮!* 🚀\n"
                f"🛠️ *𝗞𝗼𝗶 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝗵𝗼 𝘁𝗼𝗵 𝗮𝗱𝗺𝗶𝗻 ({ADMIN_USERNAME}) 𝗸𝗼 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗸𝗮𝗿𝗻𝗮.*"
            )
            bot.send_message(user_id, success_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ 𝗟𝗼𝘄 𝗕𝗮𝗹𝗮𝗻𝗰𝗲! 𝗥𝘀. 𝟭𝟵𝟵 𝗰𝗵𝗮𝗵𝗶𝘆𝗲.", show_alert=True)


if __name__ == '__main__':
    print("Python Telegram Bot is running...")
    threading.Thread(target=auto_like_scheduler_loop, daemon=True).start()
    threading.Thread(target=referral_leave_monitor_loop, daemon=True).start()
    bot.infinity_polling(allowed_updates=["message", "callback_query", "message_reaction"])

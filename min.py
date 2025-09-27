# bot.py
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from datetime import datetime

TOKEN = "7340433651:AAEw1lIb38lMuj4s2UvdOTf9XwQkduxDowE"
ADMIN_ID = 7752032178
CHANNEL_ID = "@dev_spacce"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================== DATA ========================
users = {}               # {user_id: full_name}
connections = {}         # {user_id: partner_id}
pending_connections = {} # {target_id: [waiting_user_ids]}
awaiting_help = set()    # yordam so'rovi kutilayotganlar
blocked_users = set()    # bloklangan foydalanuvchilar
# chat_history: {user_id: [ {"partner": partner_id, "type":"text/photo/video/audio", "content":..., "date":iso} ]}
chat_history = {}

# ======================== EMOJIS ========================
EMOJI_WAVE = "👋"
EMOJI_CHECK = "✅"
EMOJI_MESSAGE = "💬"
EMOJI_WARNING = "⚠️"
EMOJI_END = "✖️"
EMOJI_HELP = "🆘"
EMOJI_RULE = "📜"
EMOJI_AD = "📢"
EMOJI_CHANNEL = "📌"
EMOJI_USER = "👤"
EMOJI_CAMERA = "🖼️"
EMOJI_VIDEO = "🎥"
EMOJI_AUDIO = "🎵"

# ======================== KEYBOARDS ========================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=f"{EMOJI_HELP} Yordam", callback_data="help"),
        InlineKeyboardButton(text=f"{EMOJI_RULE} Qollanma", callback_data="manual")
    )
    return kb.as_markup()

end_chat_button = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJI_END} Suhbatni tugatish", callback_data="end_chat")]]
)

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="Foydalanuvchilar", callback_data="admin_users"),
        InlineKeyboardButton(text="Kuzatuv", callback_data="admin_watch")
    )
    kb.row(
        InlineKeyboardButton(text="Reklama yuborish", callback_data="admin_ad"),
        InlineKeyboardButton(text="Bloklash", callback_data="admin_block")
    )
    return kb.as_markup()

# ======================== HELPERS ========================
def now_iso(dt=None):
    return (dt or datetime.utcnow()).isoformat(sep=' ', timespec='seconds')

def store_chat(sender_id, partner_id, typ, content):
    entry = {"partner": partner_id, "type": typ, "content": content, "date": now_iso()}
    chat_history.setdefault(sender_id, []).append(entry)
    # also mirrored for partner (so admin sees both sides)
    mirror = {"partner": sender_id, "type": typ, "content": content, "date": now_iso()}
    chat_history.setdefault(partner_id, []).append(mirror)

# ======================== /start ========================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or message.from_user.username or str(user_id)

    if user_id in blocked_users:
        await message.answer(f"{EMOJI_WARNING} Siz bloklangansiz. Botdan foydalana olmaysiz.")
        return

    # Kanal a'zoligini tekshirish
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["left", "kicked"]:
            raise Exception("Kanalga a'zo emas")
    except Exception:
        await message.answer(f"{EMOJI_CHANNEL} Botdan foydalanish uchun kanalimizga a'zo bo‘ling: {CHANNEL_ID}")
        return

    users[user_id] = full_name

    # Pending connection bo'lsa avtomatik ulash
    if user_id in pending_connections:
        for waiting_user in list(pending_connections[user_id]):
            if waiting_user not in connections and user_id not in connections:
                connections[user_id] = waiting_user
                connections[waiting_user] = user_id
                await bot.send_message(user_id, f"{EMOJI_CHECK} Siz *{users.get(waiting_user, waiting_user)}* bilan avtomatik ulandingiz!", parse_mode="Markdown", reply_markup=end_chat_button)
                await bot.send_message(waiting_user, f"{EMOJI_CHECK} Siz *{full_name}* bilan avtomatik ulandingiz!", parse_mode="Markdown", reply_markup=end_chat_button)
            # remove waiting_user from list anyway
            try:
                pending_connections[user_id].remove(waiting_user)
            except ValueError:
                pass
        if not pending_connections[user_id]:
            del pending_connections[user_id]

    # Admin panel
    if user_id == ADMIN_ID:
        await message.answer("⚙️ Admin panel", reply_markup=admin_menu())

    # Friendly start message (meaningful)
    start_text = (
        f"{EMOJI_WAVE} Salom *{full_name}*!\n\n"
        "Bu bot orqali siz boshqa foydalanuvchilar bilan anonim va xuddi shunday muloqot qilishingiz mumkin.\n"
        "ID yuboring yoki kim bilan bog‘lanmoqchi ekaningizni yozing.\n\n"
        "Hurmatni unutmang — spam qilmaslik tavsiya etiladi."
    )
    await message.answer(start_text, parse_mode="Markdown", reply_markup=main_menu())

# ======================== CALLBACKS (help/manual/end) ========================
@dp.callback_query(lambda c: c.data == "help")
async def help_cb(call: types.CallbackQuery):
    await call.message.answer(f"{EMOJI_HELP} Iltimos, kerakli yordamni yozing (matn yoki media). Adminga jo‘natiladi.")
    awaiting_help.add(call.from_user.id)
    await call.answer()

@dp.callback_query(lambda c: c.data == "manual")
async def manual_cb(call: types.CallbackQuery):
    guide = (
        "📜 *Qollanma:*\n"
        "• ID yuborib ulaning.\n"
        "• /stop — suhbatni tugatadi.\n"
        "• Matn, rasm, video, audio yuborish mumkin.\n"
        "• Kerak bo‘lsa /yordam orqali admin bilan bog‘laning."
    )
    await call.message.answer(guide, parse_mode="Markdown")
    await call.answer()

@dp.callback_query(lambda c: c.data == "end_chat")
async def end_chat_cb(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in connections:
        partner = connections.pop(user_id)
        connections.pop(partner, None)
        await call.message.edit_text(f"{EMOJI_END} Suhbat tugatildi.")
        await bot.send_message(partner, f"{EMOJI_END} {users.get(user_id, user_id)} suhbatni tugatdi.")
        await call.answer("Suhbat tugatildi")
    else:
        await call.answer("Siz hali hech kim bilan ulanmagansiz", show_alert=True)

# ======================== ADMIN CALLBACK (users/watch/ad/block & admin->user msg) ========================
@dp.callback_query(lambda c: c.data.startswith("admin"))
async def admin_cb(call: types.CallbackQuery):
    data = call.data
    # list users with buttons to message via bot
    if data == "admin_users":
        if not users:
            await call.message.answer("Hozircha foydalanuvchilar yo‘q.")
            await call.answer()
            return
        kb = InlineKeyboardBuilder()
        for uid, name in users.items():
            # button: admin send message via bot to uid
            kb.row(InlineKeyboardButton(text=f"{name} — {uid}", callback_data=f"admin_msg_{uid}"))
        await call.message.answer("Foydalanuvchilar (bosib, admin orqali xabar yuborish mumkin):", reply_markup=kb.as_markup())
        await call.answer()
        return

    # admin watch: iterate chat_history and send content (text+media) to admin
    if data == "admin_watch":
        if not chat_history:
            await call.message.answer("Hozircha hech qanday chat yo‘q.")
            await call.answer()
            return

        await call.message.answer("📊 Kuzatuv: barcha chat yozuvlari yuborilmoqda... (media fayllar ham ko‘rinadi)")
        # iterate in chronological-ish order per user; to avoid duplicates we will collect tuples (sender, entry)
        sent = 0
        for sender_id, entries in chat_history.items():
            sender_name = users.get(sender_id, str(sender_id))
            for entry in entries:
                partner_id = entry.get("partner")
                partner_name = users.get(partner_id, str(partner_id))
                typ = entry.get("type")
                content = entry.get("content")
                date = entry.get("date", "")
                header = f"👤 *{sender_name}* ↔ *{partner_name}*\n🕒 {date}\n"

                try:
                    if typ == "text":
                        await bot.send_message(ADMIN_ID, header + f"📩 {content}", parse_mode="Markdown")
                    elif typ == "photo":
                        # content is file_id
                        await bot.send_photo(ADMIN_ID, content, caption=header + f"{EMOJI_CAMERA} Rasm yuborildi")
                    elif typ == "video":
                        await bot.send_video(ADMIN_ID, content, caption=header + f"{EMOJI_VIDEO} Video yuborildi")
                    elif typ == "audio":
                        await bot.send_audio(ADMIN_ID, content, caption=header + f"{EMOJI_AUDIO} Audio yuborildi")
                    else:
                        await bot.send_message(ADMIN_ID, header + "📩 <Noma'lum turdagi xabar>")
                except Exception as e:
                    # in case sending media fails, still send a fallback text
                    await bot.send_message(ADMIN_ID, header + f"📩 (media jo'natishda xato: {e})")
                sent += 1

        await call.answer(f"Kuzatuv tugadi. {sent} yozuv yuborildi.")
        return

    # admin wants to send ad
    if data == "admin_ad":
        await call.message.answer("Reklama matnini yuboring, hamma foydalanuvchilarga jo‘natiladi.")
        awaiting_help.add(ADMIN_ID)
        await call.answer()
        return

    # admin block
    if data == "admin_block":
        await call.message.answer("Bloklash uchun foydalanuvchi ID sini yuboring.")
        handle_message.block_mode = True
        await call.answer()
        return

    # admin -> user message button pressed (callback like admin_msg_12345)
    if data.startswith("admin_msg_"):
        try:
            target = int(data.split("_")[-1])
            # set a temporary pointer so next admin message will be sent to this target
            handle_message.admin_reply_to = target
            await call.message.answer(f"✉️ Endi yozgan xabaringiz *{users.get(target, target)}* (ID: {target}) ga yuboriladi. Matn yuboring.", parse_mode="Markdown")
            await call.answer()
        except Exception:
            await call.answer("Xato ID", show_alert=True)
        return

# ======================== MESSAGE HANDLING ========================
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or message.from_user.username or str(user_id)
    text = (message.text or "").strip()

    if user_id in blocked_users:
        await message.answer(f"{EMOJI_WARNING} Siz bloklangansiz!")
        return

    # If admin is in "reply to user" mode (admin pressed a user button)
    if user_id == ADMIN_ID and hasattr(handle_message, "admin_reply_to"):
        target = getattr(handle_message, "admin_reply_to")
        # allow text or media as reply
        if message.text:
            try:
                await bot.send_message(target, f"✉️ Admindan:\n{message.text}")
                # store in chat_history
                store_chat(user_id, target, "text", message.text)
                await message.answer("✅ Xabar yuborildi.")
            except Exception as e:
                await message.answer(f"⚠️ Xatolik: {e}")
        elif message.photo:
            fid = message.photo[-1].file_id
            try:
                await bot.send_photo(target, fid, caption="✉️ Admindan: rasm")
                store_chat(user_id, target, "photo", fid)
                await message.answer("✅ Rasm yuborildi.")
            except Exception as e:
                await message.answer(f"⚠️ Xatolik: {e}")
        elif message.video:
            fid = message.video.file_id
            try:
                await bot.send_video(target, fid, caption="✉️ Admindan: video")
                store_chat(user_id, target, "video", fid)
                await message.answer("✅ Video yuborildi.")
            except Exception as e:
                await message.answer(f"⚠️ Xatolik: {e}")
        elif message.audio:
            fid = message.audio.file_id
            try:
                await bot.send_audio(target, fid, caption="✉️ Admindan: audio")
                store_chat(user_id, target, "audio", fid)
                await message.answer("✅ Audio yuborildi.")
            except Exception as e:
                await message.answer(f"⚠️ Xatolik: {e}")
        # clear admin_reply_to after sending
        delattr(handle_message, "admin_reply_to")
        return

    # awaiting_help: if user earlier pressed help or admin sending ad/block
    if user_id in awaiting_help:
        if user_id == ADMIN_ID:
            # if block_mode set, admin sent ID to block
            if getattr(handle_message, "block_mode", False) and text.isdigit():
                blocked_users.add(int(text))
                await message.answer(f"{EMOJI_WARNING} {text} bloklandi.")
                handle_message.block_mode = False
                awaiting_help.discard(user_id)
                return
            # otherwise treat admin message as advertisement to broadcast
            for uid in list(users.keys()):
                try:
                    await bot.send_message(uid, f"{EMOJI_AD} Reklama:\n\n{message.text}")
                except:
                    pass
            await message.answer("✅ Reklama yuborildi.")
            awaiting_help.discard(user_id)
            return
        else:
            # normal user sent help request (could be media)
            if message.text:
                await bot.send_message(ADMIN_ID, f"{EMOJI_HELP} Yordam so‘rashi: *{full_name}* (ID: {user_id})\n\n{message.text}", parse_mode="Markdown")
            elif message.photo:
                fid = message.photo[-1].file_id
                await bot.send_photo(ADMIN_ID, fid, caption=f"{EMOJI_HELP} Yordam so‘rashi: *{full_name}* (ID: {user_id})", parse_mode="Markdown")
            elif message.video:
                fid = message.video.file_id
                await bot.send_video(ADMIN_ID, fid, caption=f"{EMOJI_HELP} Yordam so‘rashi: *{full_name}* (ID: {user_id})", parse_mode="Markdown")
            elif message.audio:
                fid = message.audio.file_id
                await bot.send_audio(ADMIN_ID, fid, caption=f"{EMOJI_HELP} Yordam so‘rashi: *{full_name}* (ID: {user_id})", parse_mode="Markdown")
            await message.answer("✅ Yordam so‘rovingiz adminga jo‘natildi")
            awaiting_help.discard(user_id)
            return

    # ID orqali ulanish (connect)
    if text.isdigit():
        target_id = int(text)
        if target_id in blocked_users:
            await message.answer(f"{EMOJI_WARNING} Bu foydalanuvchi bloklangan.")
            return
        if user_id in connections:
            await message.answer(f"{EMOJI_WARNING} Siz allaqachon ulangan.")
            return
        if target_id in users:
            # connect immediately if target free
            if target_id not in connections:
                connections[user_id] = target_id
                connections[target_id] = user_id
                await message.answer(f"{EMOJI_CHECK} Siz *{users[target_id]}* bilan ulandingiz!", parse_mode="Markdown", reply_markup=end_chat_button)
                await bot.send_message(target_id, f"{EMOJI_CHECK} Siz *{full_name}* bilan ulandingiz!", parse_mode="Markdown", reply_markup=end_chat_button)
            else:
                await message.answer(f"{EMOJI_WARNING} Bu foydalanuvchi allaqachon ulangan.")
        else:
            # target hasn't started: add to pending so when they start they auto-connect
            pending_connections.setdefault(target_id, []).append(user_id)
            await message.answer("ℹ️ Foydalanuvchi hali /start bosmagan. U start bosganda avtomatik ulanadi.")
        return

    # If user is connected, forward text/media to partner and store
    if user_id in connections:
        partner = connections[user_id]
        if message.text:
            # forward plain text
            await bot.send_message(partner, f"{EMOJI_MESSAGE} *{full_name}* dan:\n\n{message.text}", parse_mode="Markdown")
            await message.answer("✅ Xabaringiz yuborildi")
            store_chat(user_id, partner, "text", message.text)
        elif message.photo:
            fid = message.photo[-1].file_id
            await bot.send_photo(partner, fid, caption=f"{EMOJI_MESSAGE} {full_name} dan")
            await message.answer("✅ Rasm yuborildi")
            store_chat(user_id, partner, "photo", fid)
        elif message.video:
            fid = message.video.file_id
            await bot.send_video(partner, fid, caption=f"{EMOJI_MESSAGE} {full_name} dan")
            await message.answer("✅ Video yuborildi")
            store_chat(user_id, partner, "video", fid)
        elif message.audio:
            fid = message.audio.file_id
            await bot.send_audio(partner, fid, caption=f"{EMOJI_MESSAGE} {full_name} dan")
            await message.answer("✅ Audio yuborildi")
            store_chat(user_id, partner, "audio", fid)
        else:
            await message.answer("⚠️ Qo‘llab-quvvatlanmaydigan xabar turi.")
        return

    # default fallback
    await message.answer("ℹ️ ID yuboring yoki main menu orqali ishlating.", reply_markup=main_menu())

# ======================== START POLLING ========================
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))

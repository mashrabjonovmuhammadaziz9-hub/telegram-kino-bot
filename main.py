import json
import os
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================================
# SOZLAMALAR
# ==========================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8423538916

MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"


# ==========================================================
# LOG
# ==========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==========================================================
# JSON BILAN ISHLASH
# ==========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        save_json(filename, default)
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        save_json(filename, default)
        return default


def save_json(filename, data):
    temp_file = filename + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temp_file, filename)


# ==========================================================
# USER
# ==========================================================

def save_user(user):
    if user is None:
        return

    users = load_json(USERS_FILE, {})

    users[str(user.id)] = {
        "id": user.id,
        "first_name": user.first_name or "",
        "username": user.username or ""
    }

    save_json(USERS_FILE, users)


# ==========================================================
# ADMIN TEKSHIRISH
# ==========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# ==========================================================
# ADMIN PANEL
# ==========================================================

def admin_panel():
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Kino qo'shish",
                callback_data="add_movie"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Kino o'chirish",
                callback_data="delete_movie"
            ),
            InlineKeyboardButton(
                "🎬 Kinolar",
                callback_data="movies"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="stats"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Xabar yuborish",
                callback_data="broadcast"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Yopish",
                callback_data="close"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ==========================================================
# /START
# ==========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    save_user(user)

    name = user.first_name or "do'stim"

    await update.message.reply_text(
        f"👋 Salom, {name}!\n\n"
        "🎬 Kino botga xush kelibsiz!\n\n"
        "🔢 Kino kodini yuboring.\n\n"
        "Masalan: 20"
    )


# ==========================================================
# /ADMIN
# ==========================================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "❌ Siz admin emassiz."
        )
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👑 ADMIN PANEL\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_panel()
    )


# ==========================================================
# /CANCEL
# ==========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_admin(update.effective_user.id):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Amal bekor qilindi.",
        reply_markup=admin_panel()
    )


# ==========================================================
# /ID
# ==========================================================

async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        f"🆔 Sizning ID:\n"
        f"{update.effective_user.id}"
    )


# ==========================================================
# ADMIN BUTTONLARI
# ==========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if not is_admin(query.from_user.id):
        await query.answer(
            "❌ Siz admin emassiz.",
            show_alert=True
        )
        return

    await query.answer()

    # ======================================================
    # KINO QO'SHISH
    # ======================================================

    if query.data == "add_movie":

        context.user_data.clear()
        context.user_data["state"] = "waiting_movie"

        await query.message.reply_text(
            "➕ KINO QO'SHISH\n\n"
            "1️⃣ Menga kino yuboring.\n\n"
            "Kinoni VIDEO yoki FILE sifatida "
            "yuborishingiz mumkin.\n\n"
            "❌ Bekor qilish: /cancel"
        )

    # ======================================================
    # KINO O'CHIRISH
    # ======================================================

    elif query.data == "delete_movie":

        context.user_data.clear()
        context.user_data["state"] = "delete_movie"

        await query.message.reply_text(
            "🗑 KINO O'CHIRISH\n\n"
            "Kino kodini yuboring.\n\n"
            "Masalan:\n"
            "20\n\n"
            "❌ Bekor qilish: /cancel"
        )

    # ======================================================
    # KINOLAR
    # ======================================================

    elif query.data == "movies":

        movies = load_json(MOVIES_FILE, {})

        if not movies:
            await query.message.reply_text(
                "🎬 Hozircha kino yo'q."
            )
            return

        text = "🎬 KINOLAR\n\n"

        for code, movie in movies.items():
            text += (
                f"🔢 {code} — "
                f"{movie.get('title', 'Nomsiz')}\n"
            )

        text += f"\n📦 Jami: {len(movies)} ta"

        if len(text) > 4000:
            text = text[:3950] + "\n..."

        await query.message.reply_text(text)

    # ======================================================
    # STATISTIKA
    # ======================================================

    elif query.data == "stats":

        users = load_json(USERS_FILE, {})
        movies = load_json(MOVIES_FILE, {})

        await query.message.reply_text(
            "📊 STATISTIKA\n\n"
            f"👥 Userlar: {len(users)}\n"
            f"🎬 Kinolar: {len(movies)}"
        )

    # ======================================================
    # BROADCAST
    # ======================================================

    elif query.data == "broadcast":

        context.user_data.clear()
        context.user_data["state"] = "broadcast"

        await query.message.reply_text(
            "📢 XABAR YUBORISH\n\n"
            "Hammaga yubormoqchi bo'lgan "
            "xabar/postni yuboring.\n\n"
            "Matn, rasm, video va fayl bo'lishi mumkin.\n\n"
            "❌ Bekor qilish: /cancel"
        )

    # ======================================================
    # CLOSE
    # ======================================================

    elif query.data == "close":

        context.user_data.clear()

        try:
            await query.message.delete()
        except TelegramError:
            pass


# ==========================================================
# MEDIA HANDLER
# ==========================================================

async def media_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    save_user(user)

    # Oddiy user
    if not is_admin(user.id):
        await update.message.reply_text(
            "🔢 Kino kodini yuboring."
        )
        return

    state = context.user_data.get("state")

    # ======================================================
    # BROADCAST MEDIA
    # ======================================================

    if state == "broadcast":
        await send_broadcast(update, context)
        return

    # ======================================================
    # KINO QABUL QILISH
    # ======================================================

    if state != "waiting_movie":

        await update.message.reply_text(
            "⚠️ Kino qo'shish uchun:\n\n"
            "/admin → ➕ Kino qo'shish"
        )

        return

    message = update.message

    file_id = None
    file_type = None

    # VIDEO
    if message.video:

        file_id = message.video.file_id
        file_type = "video"

    # DOCUMENT / FILE
    elif message.document:

        file_id = message.document.file_id
        file_type = "document"

    # ANIMATION
    elif message.animation:

        file_id = message.animation.file_id
        file_type = "animation"

    if not file_id:

        await message.reply_text(
            "❌ Bu faylni qabul qila olmadim.\n\n"
            "Kinoni video yoki file qilib yuboring."
        )

        return

    context.user_data["movie_file_id"] = file_id
    context.user_data["movie_file_type"] = file_type

    # Fayl nomini ham saqlaymiz
    if message.document:
        context.user_data["original_name"] = (
            message.document.file_name or ""
        )
    else:
        context.user_data["original_name"] = ""

    context.user_data["state"] = "waiting_title"

    await message.reply_text(
        "✅ KINO QABUL QILINDI!\n\n"
        "2️⃣ Endi kino nomini yozing.\n\n"
        "Masalan:\n"
        "Avatar"
    )


# ==========================================================
# TEXT HANDLER
# ==========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    save_user(user)

    text = update.message.text.strip()

    # ======================================================
    # ODDIY USER
    # ======================================================

    if not is_admin(user.id):
        await find_movie(update, text)
        return

    # ======================================================
    # ADMIN
    # ======================================================

    state = context.user_data.get("state")

    # KINO NOMI
    if state == "waiting_title":

        if not text:
            await update.message.reply_text(
                "❌ Kino nomini yozing."
            )
            return

        context.user_data["movie_title"] = text
        context.user_data["state"] = "waiting_code"

        await update.message.reply_text(
            f"🎬 Kino: {text}\n\n"
            "3️⃣ Endi kino kodini yuboring.\n\n"
            "Masalan:\n"
            "20"
        )

        return

    # KINO KODI
    if state == "waiting_code":

        await add_movie(
            update,
            context,
            text
        )

        return

    # DELETE
    if state == "delete_movie":

        await remove_movie(
            update,
            context,
            text
        )

        return

    # BROADCAST
    if state == "broadcast":

        await send_broadcast(
            update,
            context
        )

        return

    # Admin ham kino kodi yozishi mumkin
    await find_movie(update, text)


# ==========================================================
# KINO QO'SHISH
# ==========================================================

async def add_movie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    code
):
    code = code.strip().replace(" ", "")

    if not code:

        await update.message.reply_text(
            "❌ Kino kodi bo'sh bo'lmasin."
        )

        return

    if len(code) > 20:

        await update.message.reply_text(
            "❌ Kino kodi juda uzun.\n"
            "20 ta belgidan kam bo'lsin."
        )

        return

    title = context.user_data.get("movie_title")
    file_id = context.user_data.get("movie_file_id")
    file_type = context.user_data.get("movie_file_type")
    original_name = context.user_data.get(
        "original_name",
        ""
    )

    # Tekshiruv
    if not title or not file_id or not file_type:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Kino ma'lumotlari topilmadi.\n\n"
            "Qaytadan boshlang:\n"
            "/admin → ➕ Kino qo'shish"
        )

        return

    movies = load_json(MOVIES_FILE, {})

    # Kod mavjud
    if code in movies:

        await update.message.reply_text(
            f"❌ {code} kodi allaqachon mavjud.\n\n"
            f"🎬 {movies[code].get('title', 'Nomsiz')}\n\n"
            "Boshqa kod yuboring."
        )

        return

    # SAQLASH
    movies[code] = {
        "title": title,
        "file_id": file_id,
        "file_type": file_type,
        "original_name": original_name
    }

    try:

        save_json(
            MOVIES_FILE,
            movies
        )

    except Exception as error:

        logger.exception(error)

        await update.message.reply_text(
            f"❌ Saqlashda xato:\n{error}"
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ KINO QO'SHILDI!\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🎬 {title}\n"
        f"🔢 Kod: {code}\n\n"
        "Endi shu kodni yuborib tekshiring.",
        reply_markup=admin_panel()
    )


# ==========================================================
# KINO TOPISH
# ==========================================================

async def find_movie(
    update: Update,
    code
):
    code = code.strip().replace(" ", "")

    movies = load_json(
        MOVIES_FILE,
        {}
    )

    movie = movies.get(code)

    if movie is None:

        await update.message.reply_text(
            "❌ Kino topilmadi.\n\n"
            "🔢 Kodni tekshirib qayta yuboring."
        )

        return

    title = movie.get(
        "title",
        "Kino"
    )

    file_id = movie.get(
        "file_id"
    )

    file_type = movie.get(
        "file_type"
    )

    if not file_id:

        await update.message.reply_text(
            "❌ Bu kinoning fayli topilmadi."
        )

        return

    wait_message = await update.message.reply_text(
        f"🔎 {title} topildi!\n"
        "⏳ Yuborilmoqda..."
    )

    caption = (
        f"🎬 {title}\n\n"
        f"🔢 Kod: {code}"
    )

    try:

        # VIDEO
        if file_type == "video":

            await update.message.reply_video(
                video=file_id,
                caption=caption,
                supports_streaming=True
            )

        # DOCUMENT
        elif file_type == "document":

            await update.message.reply_document(
                document=file_id,
                caption=caption
            )

        # ANIMATION
        elif file_type == "animation":

            await update.message.reply_animation(
                animation=file_id,
                caption=caption
            )

        else:

            await wait_message.edit_text(
                "❌ Fayl turi noma'lum."
            )

            return

        try:
            await wait_message.delete()
        except TelegramError:
            pass

    except TelegramError as error:

        logger.exception(error)

        await wait_message.edit_text(
            "❌ Telegram kinoni yubora olmadi.\n\n"
            f"Xato: {error}"
        )

    except Exception as error:

        logger.exception(error)

        await wait_message.edit_text(
            "❌ Xatolik yuz berdi.\n\n"
            f"{error}"
        )


# ==========================================================
# KINO O'CHIRISH
# ==========================================================

async def remove_movie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    code
):
    code = code.strip().replace(" ", "")

    movies = load_json(
        MOVIES_FILE,
        {}
    )

    if code not in movies:

        await update.message.reply_text(
            f"❌ {code} kodli kino yo'q.\n\n"
            "Boshqa kod yuboring yoki /cancel."
        )

        return

    title = movies[code].get(
        "title",
        "Kino"
    )

    del movies[code]

    save_json(
        MOVIES_FILE,
        movies
    )

    context.user_data.clear()

    await update.message.reply_text(
        "🗑 KINO O'CHIRILDI\n\n"
        f"🎬 {title}\n"
        f"🔢 Kod: {code}",
        reply_markup=admin_panel()
    )


# ==========================================================
# BROADCAST
# ==========================================================

async def send_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    users = load_json(
        USERS_FILE,
        {}
    )

    if not users:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Hozircha user yo'q.",
            reply_markup=admin_panel()
        )

        return

    status = await update.message.reply_text(
        "📤 Xabar yuborish boshlandi...\n\n"
        f"👥 {len(users)} ta user"
    )

    success = 0
    failed = 0
    blocked = 0

    for user_id in list(users.keys()):

        try:

            await update.message.copy(
                chat_id=int(user_id)
            )

            success += 1

        except Forbidden:

            blocked += 1
            failed += 1

        except RetryAfter as error:

            await asyncio.sleep(
                error.retry_after
            )

            try:

                await update.message.copy(
                    chat_id=int(user_id)
                )

                success += 1

            except TelegramError:

                failed += 1

        except TelegramError as error:

            logger.warning(
                "User %s: %s",
                user_id,
                error
            )

            failed += 1

        await asyncio.sleep(0.05)

    context.user_data.clear()

    await status.edit_text(
        "📢 YUBORISH TUGADI\n\n"
        f"👥 Jami: {len(users)}\n"
        f"✅ Yuborildi: {success}\n"
        f"❌ Xato: {failed}\n"
        f"🚫 Bloklagan: {blocked}"
    )

    await update.message.reply_text(
        "👑 Admin panel:",
        reply_markup=admin_panel()
    )


# ==========================================================
# BOSHQA MEDIA
# ==========================================================

async def other_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    save_user(user)

    if (
        is_admin(user.id)
        and context.user_data.get("state") == "broadcast"
    ):

        await send_broadcast(
            update,
            context
        )

        return

    await update.message.reply_text(
        "🔢 Kino kodini yuboring."
    )


# ==========================================================
# ERROR HANDLER
# ==========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "BOT XATOSI",
        exc_info=context.error
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    print()
    print("=" * 50)
    print("🎬 KINO BOT")
    print("=" * 50)

    # TOKEN TEKSHIRISH
    if (
        not TOKEN
        or TOKEN == "YANGI_TOKENNI_SHU_YERGA_QOYING"
    ):

        print("❌ TOKEN KIRITILMAGAN!")
        return

    # JSON FAYLLARNI YARATISH
    load_json(
        MOVIES_FILE,
        {}
    )

    load_json(
        USERS_FILE,
        {}
    )

    # APPLICATION
    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # COMMANDS
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            get_id
        )
    )

    # BUTTON
    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # VIDEO / DOCUMENT / ANIMATION
    app.add_handler(
        MessageHandler(
            (
                filters.VIDEO
                | filters.Document.ALL
                | filters.ANIMATION
            )
            & ~filters.COMMAND,
            media_handler
        )
    )

    # TEXT
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )

    # PHOTO / AUDIO / VOICE / STICKER
    app.add_handler(
        MessageHandler(
            (
                filters.PHOTO
                | filters.AUDIO
                | filters.VOICE
                | filters.Sticker.ALL
            )
            & ~filters.COMMAND,
            other_handler
        )
    )

    # ERROR
    app.add_error_handler(
        error_handler
    )

    print("✅ Bot ishlayapti!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("💾 movies.json")
    print("👥 users.json")
    print("🛑 To'xtatish: CTRL + C")
    print("=" * 50)
    print()

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()
import os 
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from telegram.ext.filters import ChatType

# === Переменные ===
SUPABASE_URL = os.environ.get("SUPABASE_URL") + "/rest/v1/user_activity"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = -1002402728049
POLL_IMAGE_URL = "https://downloader.disk.yandex.ru/preview/f46882adbaf5b8f9163fc0de114dd82ce682b422e519148d329c6bafcf7e7ca8/681241e4/nvlDwn1H-Rprc95XbK3mq6aOyPYARFI-VLCmRy4uY0k3ZNHrdJULX5d7KdaFTAgfTOMuU-TcW2Hz5u5dbR50tg%3D%3D?uid=0&filename=photo_2025-04-30_14-28-54.jpg&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# === База данных ===
def insert_activity(data):
    response = requests.post(SUPABASE_URL, json=data, headers=HEADERS)
    if response.status_code >= 400:
        print("❌ Insert Error:", response.status_code, response.text)

def get_activity(user_id, post_id):
    params = {
        "user_id": f"eq.{user_id}",
        "post_id": f"eq.{post_id}"
    }
    response = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    return response.json() if response.status_code < 400 else []

def update_activity(user_id, post_id, update_data):
    url = f"{SUPABASE_URL}?user_id=eq.{user_id}&post_id=eq.{post_id}"
    response = requests.patch(url, headers=HEADERS, json=update_data)
    if response.status_code >= 400:
        print("❌ Update Error:", response.status_code, response.text)

def update_score(user_id, username, post_id, action_type, extra=None):
    existing = get_activity(user_id, post_id)
    now = datetime.now(ZoneInfo("Europe/Moscow")).isoformat()
    score_map = {"comment": 20, "poll": 10, "reaction": 10}

    # Определение поля-флага по типу действия
    flag_field = "reacted" if action_type == "reaction" else (
        "commented" if action_type == "comment" else "polled"
    )

    if existing:
        record = existing[0]
        if record.get(flag_field):
            print(f"⚠️ {action_type} уже учтён для user_id={user_id}, post_id={post_id}")
            return

        updates = {
            "date": now,
            flag_field: True,
            "score": record.get("score", 0) + score_map[action_type],
            "poll_option": extra.get("poll_option") if extra else None
        }
        update_activity(user_id, post_id, updates)
    else:
        insert_activity({
            "user_id": user_id,
            "username": username,
            "post_id": post_id,
            "reacted": action_type == "reaction",
            "commented": action_type == "comment",
            "polled": action_type == "poll",
            "score": score_map[action_type],
            "date": now,
            "poll_option": extra.get("poll_option") if extra else None,
            "action_type": action_type
        })

# === Комментарии ===
async def comment_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.reply_to_message:
        return

    parent = message.reply_to_message
    if parent.sender_chat and parent.sender_chat.id == CHANNEL_ID:
        user = update.effective_user
        update_score(
            user.id,
            user.username or user.full_name,
            parent.message_id,
            "comment",
            {"poll_option": message.text}
        )
        print(f"✅ Комментарий от {user.username} учтён")

# === Инлайн-опрос ===
ALLOWED_USERNAMES = ["Samrus91", "Lilya_Mukhutdinova", "EvgenijIsaev"]

async def poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user = update.effective_user
    if user.username not in ALLOWED_USERNAMES:
        await message.reply_text("❌ У тебя нет прав на создание опроса.")
        return

    parts = message.text.strip().split("\n")
    if len(parts) < 3:
        await message.reply_text("❗ Формат:\n/poll\nВопрос\nВариант 1\nВариант 2\n...")
        return

    question = parts[1]
    options = parts[2:]

    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"poll_{i}_{option}")]
        for i, option in enumerate(options)
    ]

    await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=POLL_IMAGE_URL,
        caption=f"📊<b>{question}</b>\n\nВыбери вариант ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# === Обработка ответа на опрос ===
async def poll_vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="❤️ Твой ответ принят! Учитывается только первый ответ!", show_alert=False)

    user = query.from_user
    data = query.data.split("_", 2)
    option = data[2] if len(data) > 2 else ""
    post_id = query.message.message_id

    update_score(
        user.id,
        user.username or user.full_name,
        post_id,
        "poll",
        {"poll_option": option}
    )
    print(f"📊 Голос от {user.username} за '{option}' учтён")

# === Автодобавление реакций ===
async def reaction_auto_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    message = update.channel_post

    if message.photo and message.caption and "Выбери вариант ниже:" in message.caption:
        return  # опрос — не добавляем реакцию

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 Очень полезно", callback_data=f"react_{message.message_id}_1")],
        [InlineKeyboardButton("👌 Возможно пригодится", callback_data=f"react_{message.message_id}_2")],
        [InlineKeyboardButton("👎 Не пригодилось", callback_data=f"react_{message.message_id}_3")]
    ])

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text="Насколько был полезен этот материал?",
        reply_markup=keyboard,
        reply_to_message_id=message.message_id
    )

# === Обработка реакции ===
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="❤️ Твой ответ принят! Учитывается только первый ответ!", show_alert=False)

    user = query.from_user
    parts = query.data.split("_")
    post_id = int(parts[1])
    reaction_text = {
        "1": "👍 Очень полезно",
        "2": "👌 Возможно пригодится",
        "3": "👎 Не пригодится"
    }.get(parts[2], "")

    update_score(
        user.id,
        user.username or user.full_name,
        post_id,
        "reaction",
        {"poll_option": reaction_text}
    )
    print(f"👍 Реакция от {user.username} учтена")

# === Запуск ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.REPLY, comment_listener))
    app.add_handler(MessageHandler(filters.TEXT & ChatType.PRIVATE, poll_handler))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"^react_"))
    app.add_handler(CallbackQueryHandler(poll_vote_handler, pattern=r"^poll_"))
    app.add_handler(MessageHandler(filters.ALL & filters.UpdateType.CHANNEL_POST, reaction_auto_add))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

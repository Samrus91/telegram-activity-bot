import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Получаем переменные окружения
SUPABASE_URL = os.environ.get("SUPABASE_URL") + "/rest/v1/user_activity"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Укажи свой ID канала
YOUR_CHANNEL_ID = -1002402728049  # Заменить на реальный ID

# Заголовки для работы с Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ➕ Добавление новой активности
def insert_activity(data):
    response = requests.post(SUPABASE_URL, json=data, headers=HEADERS)
    if response.status_code >= 400:
        print("❌ Insert Error:", response.status_code, response.text)
    return response.json()

# 🔍 Получение активности по user_id и post_id
def get_activity(user_id, post_id):
    params = {
        "user_id": f"eq.{user_id}",
        "post_id": f"eq.{post_id}"
    }
    response = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    if response.status_code >= 400:
        print("❌ Get Error:", response.status_code, response.text)
    return response.json()

# 🔄 Обновление записи
def update_activity(user_id, post_id, update_data):
    url = f"{SUPABASE_URL}?user_id=eq.{user_id}&post_id=eq.{post_id}"
    response = requests.patch(url, headers=HEADERS, json=update_data)
    if response.status_code >= 400:
        print("❌ Update Error:", response.status_code, response.text)
    return response.json()

# ⭐ Основная логика начисления баллов
def update_score(user_id, username, post_id, action_type):
    existing = get_activity(user_id, post_id)
    now = datetime.utcnow().isoformat()  # дата и время действия

    if existing:
        record = existing[0]
        reacted = record.get("reacted", False)
        commented = record.get("commented", False)
        score = record.get("score", 0)
        new_reacted = reacted
        new_commented = commented
        score_delta = 0

        if action_type == "reaction" and not reacted:
            new_reacted = True
            score_delta += 1
        elif action_type == "comment" and not commented:
            new_commented = True
            score_delta += 20

        if score_delta > 0:
            update_activity(user_id, post_id, {
                "reacted": new_reacted,
                "commented": new_commented,
                "score": score + score_delta,
                "date": now
            })
    else:
        score = 1 if action_type == "reaction" else 5
        insert_activity({
            "user_id": user_id,
            "username": username,
            "post_id": post_id,
            "reacted": action_type == "reaction",
            "commented": action_type == "comment",
            "score": score,
            "date": now
        })

# 👀 Отслеживание комментариев (reply на пост канала)
async def comment_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user

    if not message or not message.reply_to_message:
        return

    parent = message.reply_to_message
    post_id = parent.message_id
    user_id = user.id
    username = user.username or user.full_name

    # Проверяем, что комментарий к посту в канале
    if parent.sender_chat and parent.sender_chat.id == YOUR_CHANNEL_ID:
        update_score(user_id, username, post_id, "comment")
        print(f"✅ Комментарий от {username} учтён (post_id: {post_id})")

# 🚀 Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.REPLY, comment_listener))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

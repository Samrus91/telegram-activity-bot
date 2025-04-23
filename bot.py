import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Получаем переменные окружения
SUPABASE_URL = os.environ.get("SUPABASE_URL") + "/rest/v1/user_activity"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")

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
    return response.json()

# 🔍 Получение активности по user_id и post_id
def get_activity(user_id, post_id):
    params = {
        "user_id": f"eq.{user_id}",
        "post_id": f"eq.{post_id}"
    }
    response = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    return response.json()

# 🔄 Обновление записи
def update_activity(user_id, post_id, update_data):
    url = f"{SUPABASE_URL}?user_id=eq.{user_id}&post_id=eq.{post_id}"
    response = requests.patch(url, headers=HEADERS, json=update_data)
    return response.json()

# ⭐ Основная логика начисления баллов
def update_score(user_id, username, post_id, action_type):
    existing = get_activity(user_id, post_id)
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
            score_delta += 5

        if score_delta > 0:
            update_activity(user_id, post_id, {
                "reacted": new_reacted,
                "commented": new_commented,
                "score": score + score_delta
            })
    else:
        score = 1 if action_type == "reaction" else 5
        insert_activity({
            "user_id": user_id,
            "username": username,
            "post_id": post_id,
            "reacted": action_type == "reaction",
            "commented": action_type == "comment",
            "score": score
        })

# 🗣 Обработчик команды /commented (пример использования)
async def commented_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if not message:
        return

    user_id = user.id
    username = user.username or user.full_name
    post_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id

    update_score(user_id, username, post_id, "comment")

    await message.reply_text("Комментарий учтён! +5 баллов 😉")

# 🚀 Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчик команды
    app.add_handler(CommandHandler("commented", commented_handler))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

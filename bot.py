import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.ext.filters import ChatType

# === Настройки ===
SUPABASE_URL    = os.environ["SUPABASE_URL"] + "/rest/v1/user_activity"
SUPABASE_KEY    = os.environ["SUPABASE_KEY"]
BOT_TOKEN       = os.environ["BOT_TOKEN"]
CHANNEL_ID      = -1002402728049
ANOTHER_CHAT_ID = -1002516482222
POLL_IMAGE_URL  = "https://downloader.disk.yandex.ru/preview/f46882adbaf5b8f9163fc0de114dd82ce682b422e519148d329c6bafcf7e7ca8/681241e4/nvlDwn1H-Rprc95XbK3mq6aOyPYARFI-VLCmRy4uY0k3ZNHrdJULX5d7KdaFTAgfTOMuU-TcW2Hz5u5dbR50tg%3D%3D?uid=0&filename=photo_2025-04-30_14-28-54.jpg&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048"
ALLOWED_USERNAMES = {"Samrus91", "Lilya_Mukhutdinova", "EvgenijIsaev"}

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# === Supabase helper functions ===
def insert_activity(data: dict):
    r = requests.post(SUPABASE_URL, json=data, headers=HEADERS)
    if r.status_code >= 400:
        print("❌ Insert Error:", r.status_code, r.text)

def get_activity(username: str, post_id: int):
    params = {"username": f"eq.{username}", "post_id": f"eq.{post_id}"}
    r = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    return r.json() if r.ok else []

def get_total_score(username: str) -> int:
    params = {"username": f"eq.{username}"}
    r = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    if not r.ok:
        print("❌ Score Fetch Error:", r.status_code, r.text)
        return 0
    return sum(item.get("score", 0) for item in r.json())

def update_activity(username: str, post_id: int, data: dict):
    url = f"{SUPABASE_URL}?username=eq.{username}&post_id=eq.{post_id}"
    r = requests.patch(url, headers=HEADERS, json=data)
    if r.status_code >= 400:
        print("❌ Update Error:", r.status_code, r.text)

def update_score(user_id: int, username: str, post_id: int, action: str, extra: dict = None):
    now = datetime.now(ZoneInfo("Europe/Moscow")).isoformat()
    score_map = {"comment": 20, "poll": 10, "reaction": 10, "registration": 0}

    if action not in score_map:
        return

    if action == "poll":
        flag = "polled"
    elif action == "registration":
        flag = "registered"
    else:
        flag = f"{action}ed"

    updates = {
        "reacted": False,
        "commented": False,
        "polled": False,
        "registered": False,
        "date": now
    }

    updates[flag] = True

    if extra:
        updates.update(extra)

    existing = get_activity(username, post_id)
    if existing:
        rec = existing[0]
        if rec.get(flag):
            return
        if action != "registration":
            updates["score"] = score_map[action]
        update_activity(username, post_id, updates)
    else:
        updates["score"] = score_map[action] if action != "registration" else 0
        insert_activity({
            "user_id": user_id,
            "username": username,
            "post_id": post_id,
            "reacted": action == "reaction",
            "commented": action == "comment",
            "polled": action == "poll",
            "registered": action == "registration",
            "score": updates["score"],
            "date": now,
            "poll_option": extra.get("poll_option") if extra else None,
            "action_type": action,
        })
# === Обработчики действий ===
async def comment_listener(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    if not m or not m.reply_to_message:
        return
    parent = m.reply_to_message
    if parent.sender_chat and parent.sender_chat.id == CHANNEL_ID:
        u = update.effective_user
        update_score(
            user_id=u.id,
            username=u.username,
            post_id=parent.message_id,
            action="comment",
            extra={"poll_option": m.text}
        )

async def reaction_auto_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    txt = post.text or post.caption or ""
    
    if "#полезное" in txt:
        prompt = "Насколько был полезен этот материал?"
        btns = [
            [InlineKeyboardButton("👍 Очень полезно", callback_data=f"react_{post.message_id}_1")],
            [InlineKeyboardButton("👌 Возможно пригодится", callback_data=f"react_{post.message_id}_2")],
            [InlineKeyboardButton("👎 Не пригодилось", callback_data=f"react_{post.message_id}_3")],
        ]
    elif "#квиклерн" in txt:
        prompt = "Если хочешь принять участие, нажми кнопку ниже 👇"
        btns = [[InlineKeyboardButton("📝 Записаться", callback_data=f"register_{post.message_id}")]]
    else:
        return

    await ctx.bot.send_message(
        chat_id=CHANNEL_ID,
        text=prompt,
        reply_markup=InlineKeyboardMarkup(btns),
        reply_to_message_id=post.message_id
    )

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data

    if d == "get_exp":
        await q.answer()
        tot = get_total_score(q.from_user.username)
        return await q.message.reply_text(f"✨ У тебя {tot} EXP")

    if d.startswith("react_"):
        _, mid, choice = d.split("_", 2)
        emoji = {"1": "👍", "2": "👌", "3": "👎"}[choice]
        await q.answer("❤️ Твой ответ принят! Учитывается только первый ответ!", show_alert=True)
        update_score(
            user_id=q.from_user.id,
            username=q.from_user.username,
            post_id=int(mid),
            action="reaction",
            extra={"poll_option": emoji}
        )

    elif d.startswith("register_"):
        mid = int(d.split("_", 1)[1])
        await q.answer("✅ Ты записался! Скоро мы добавим тебя во встречу в календаре!", show_alert=True)
        update_score(
            user_id=q.from_user.id,
            username=q.from_user.username,
            post_id=mid,
            action="registration",
            extra={"poll_option": "Записался"}
        )
        mention = f"@{q.from_user.username}"
        try:
            origin_msg = await ctx.bot.forward_message(chat_id=q.from_user.id, from_chat_id=CHANNEL_ID, message_id=mid)
            preview = (origin_msg.text or origin_msg.caption or "")[:100].strip()
        except:
            preview = "..."
        link = f"https://t.me/c/{str(CHANNEL_ID)[4:]}/{mid}"
        await ctx.bot.send_message(
            ANOTHER_CHAT_ID,
            f"👤 Пользователь {mention} записался на вебинар\n📌 Пост: {preview}\n🔗 <a href=\"{link}\">Ссылка на пост</a>",
            parse_mode="HTML"
        )

async def poll_vote_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("❤️ Твой ответ принят! Учитывается только первый ответ!", show_alert=False)
    _, idx, opt = q.data.split("_", 2)
    update_score(
        user_id=q.from_user.id,
        username=q.from_user.username,
        post_id=q.message.message_id,
        action="poll",
        extra={"poll_option": opt}
    )
# === Админ: меню и опросы ===

async def admin_menu_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAMES:
        return

    kb = [
        [InlineKeyboardButton("📥 Создать опрос", callback_data="create_poll")],
        [InlineKeyboardButton("💠 EXP пользователей", callback_data="admin_score")],
        [InlineKeyboardButton("➕ Начислить EXP", callback_data="admin_addexp")]
    ]

    if update.message:
        await update.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(kb))
    elif update.callback_query:
        await update.callback_query.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(kb))

async def create_poll_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data["poll_stage"] = "awaiting_question"
    await update.callback_query.message.reply_text("📝 Введите текст вопроса для опроса:")

async def admin_text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAMES:
        return

    text = update.message.text.strip()
    add_stage = ctx.user_data.get("add_stage")
    poll_stage = ctx.user_data.get("poll_stage")

    print(f"📥 admin_text_router: add_stage={add_stage}, poll_stage={poll_stage}, text={text}")

    # === Режим начисления баллов ===
    if add_stage == "awaiting_text":
        try:
            *usernames, score_str = text.split()
            score = int(score_str)
            usernames = [u for u in usernames if not u.startswith("/") and u != "add"]
            now = datetime.now(ZoneInfo("Europe/Moscow")).isoformat()

            for username in usernames:
                insert_activity({
                    "user_id": 999999,
                    "username": username,
                    "post_id": 999999,
                    "reacted": False,
                    "commented": False,
                    "polled": False,
                    "registered": False,
                    "score": score,
                    "date": now,
                    "poll_option": "manual",
                    "action_type": "manual",
                })

            ctx.user_data.pop("add_stage", None)
            kb = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="admin_back")]]
            await update.message.reply_text(f"✅ Начислено {score} баллов для: {', '.join(usernames)}", reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {e}")
        return

    # === Режим создания опроса ===
    if poll_stage == "awaiting_question":
        ctx.user_data["poll_question"] = text
        ctx.user_data["poll_stage"] = "awaiting_options"
        return await update.message.reply_text("📋 Теперь отправьте варианты ответов в столбик (по одному на строку):")

    elif poll_stage == "awaiting_options":
        options = [opt.strip() for opt in text.split("\n") if opt.strip()]
        if len(options) < 2:
            return await update.message.reply_text("❌ Нужно минимум два варианта.")
        ctx.user_data["poll_options"] = options
        ctx.user_data["poll_stage"] = "preview"

        preview = f"📊 <b>{ctx.user_data['poll_question']}</b>\n\n" + "\n".join(f"🔘 {opt}" for opt in options)
        kb = [
            [InlineKeyboardButton("✅ Отправить опрос", callback_data="send_poll")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="edit_poll")],
            [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="admin_back")]
        ]
        return await update.message.reply_text(preview, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    return await update.message.reply_text("❌ Сейчас бот не ожидает никакого текстового ввода.")
        
async def poll_control_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if update.callback_query.data == "edit_poll":
        ctx.user_data["poll_stage"] = "awaiting_question"
        await update.callback_query.message.reply_text("✏️ Введите новый текст вопроса:")
    elif update.callback_query.data == "send_poll":
        q = ctx.user_data.get("poll_question")
        opts = ctx.user_data.get("poll_options")
        if not q or not opts:
            return await update.callback_query.message.reply_text("⚠️ Недостаточно данных для отправки.")
        kb = [[InlineKeyboardButton(f"{i+1}. {o}", callback_data=f"poll_{i}_{o}")] for i, o in enumerate(opts)]
        await ctx.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=POLL_IMAGE_URL,
            caption=f"📊<b>{q}</b>\n\nВыбери вариант:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        ctx.user_data.clear()
        await update.callback_query.message.reply_text("✅ Опрос отправлен в канал.")
# === Админ: EXP и ручное начисление ===

async def admin_score_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    r = requests.get(SUPABASE_URL, headers=HEADERS)
    data = r.json() if r.ok else []

    # Группировка по пользователям
    totals = {}
    for rec in data:
        u = rec.get("username")
        totals[u] = totals.get(u, 0) + rec.get("score", 0)

    # Сортируем и формируем строки
    lines = [f"@{u} — {s} EXP" for u, s in sorted(totals.items(), key=lambda x: -x[1])]

    kb = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="admin_back")]]

    # === Разбиваем и отправляем по частям (лимит Telegram — 4096 символов) ===
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:  # небольшой запас
            await update.callback_query.message.reply_text(chunk.strip())
            chunk = ""
        chunk += line + "\n"

    if chunk:
        await update.callback_query.message.reply_text(chunk.strip(), reply_markup=InlineKeyboardMarkup(kb))

async def admin_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data["add_stage"] = "awaiting_text"
    fmt = "Пример:\nSamrus91 Lilya_Mukhutdinova 25"
    await update.callback_query.message.reply_text(f"Пришлите логины пользователей и количество баллов.\n{fmt}")

async def admin_back_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await admin_menu_handler(update, ctx)
# === Стартовый экран ===
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📊 Мои EXP", callback_data="get_exp")]]
    await update.message.reply_text("⚡️ Привет, я Expik! Чтобы узнать свой EXP, нажми кнопку👇", reply_markup=InlineKeyboardMarkup(kb))


# === Main ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", admin_menu_handler))

    # Callback'и
    app.add_handler(CallbackQueryHandler(create_poll_start, pattern="^create_poll$"))
    app.add_handler(CallbackQueryHandler(poll_control_handler, pattern="^(send_poll|edit_poll)$"))
    app.add_handler(CallbackQueryHandler(admin_score_handler, pattern="^admin_score$"))
    app.add_handler(CallbackQueryHandler(admin_add_start, pattern="^admin_addexp$"))
    app.add_handler(CallbackQueryHandler(admin_back_handler, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"^(get_exp|react_|register_)"))
    app.add_handler(CallbackQueryHandler(poll_vote_handler, pattern=r"^poll_"))

    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ChatType.PRIVATE, admin_text_router))
    app.add_handler(MessageHandler(filters.REPLY & ChatType.GROUPS, comment_listener))
    app.add_handler(MessageHandler(filters.ALL & filters.UpdateType.CHANNEL_POST, reaction_auto_add))

    print("🚀 Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()

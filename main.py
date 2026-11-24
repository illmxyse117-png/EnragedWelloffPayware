
import json
import os
import re
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "9109351369:AAHVzmAn_TQSFTiFpC4EXi7XTPc8ay7QWEY"
ACCESS_KEY = "3appkeyunlock-Qhbs345"

DB_FILE = "users.json"

users = {}
states = {}
sessions = {}


def load_users():
    global users

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = {}


def save_users():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def valid_link(text):
    try:
        parsed = urlparse(text)
        return (
            parsed.scheme in ("https", "http")
            and bool(parsed.netloc)
            and "." in parsed.netloc
            and " " not in text
        )
    except Exception:
        return False


def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Создать символы",
            callback_data="create"
        )],
        [InlineKeyboardButton(
            "✏️ Изменить никнейм",
            callback_data="nickname"
        )]
    ])


async def edit_screen(query, text, keyboard=None):
    await query.edit_message_text(
        text,
        reply_markup=keyboard
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in users:
        users[uid] = {
            "authorized": False,
            "nickname": ""
        }
        save_users()

    if users[uid]["authorized"]:
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=menu_keyboard()
        )
    else:
        states[uid] = "key"
        await update.message.reply_text(
            "🔐 Введите ключ доступа:"
        )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = str(query.from_user.id)

    user = users.get(uid)

    if not user or not user.get("authorized"):
        await edit_screen(query, "❌ Нет доступа.")
        return

    if query.data == "create":
        if not user.get("nickname"):
            states[uid] = "nickname_for_create"
            await edit_screen(
                query,
                "👤 Сначала введите свой никнейм:"
            )
        else:
            states[uid] = "link"
            await edit_screen(
                query,
                "🔗 Отправьте ссылку на NFT:"
            )

    elif query.data == "nickname":
        states[uid] = "nickname"
        await edit_screen(
            query,
            "✏️ Введите новый никнейм:"
        )

    elif query.data == "gram":
        states[uid] = "gram_price"
        await edit_screen(
            query,
            "💰 Введите цену NFT в GRAM (1–99999):"
        )

    elif query.data == "stars":
        states[uid] = "stars_price"
        await edit_screen(
            query,
            "⭐ Введите цену NFT в звёздах (125–9999999):"
        )


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text.strip()

    if uid not in users:
        users[uid] = {
            "authorized": False,
            "nickname": ""
        }

    user = users[uid]
    state = states.get(uid)

    if not user.get("authorized"):
        if text == ACCESS_KEY:
            user["authorized"] = True
            save_users()
            states.pop(uid, None)

            await update.message.reply_text(
                "✅ Доступ разрешён!",
                reply_markup=menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ Неверный ключ.")
        return

    # НИКНЕЙМ
    if state in ("nickname", "nickname_for_create"):
        if not text or len(text) > 32:
            await update.message.reply_text(
                "❌ Никнейм должен содержать от 1 до 32 символов."
            )
            return

        user["nickname"] = text
        save_users()

        if state == "nickname_for_create":
            states[uid] = "link"
            await update.message.reply_text(
                "✅ Никнейм сохранён!\n\n🔗 Теперь отправьте ссылку на NFT:"
            )
        else:
            states[uid] = None
            await update.message.reply_text(
                "✅ Никнейм изменён!",
                reply_markup=menu_keyboard()
            )
        return

    # ССЫЛКА NFT
    if state == "link":
        if not valid_link(text):
            await update.message.reply_text(
                "❌ Нужна ссылка формата https://..."
            )
            return

        sessions.setdefault(uid, {})["link"] = text

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("GRAM", callback_data="gram"),
                InlineKeyboardButton("⭐ ЗВЁЗДЫ", callback_data="stars")
            ]
        ])

        states[uid] = "currency"

        await update.message.reply_text(
            "💱 Выберите валюту:",
            reply_markup=keyboard
        )
        return

    # ЦЕНА
    if state in ("gram_price", "stars_price"):
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Введите цену только цифрами."
            )
            return

        price = int(text)

        if state == "gram_price":
            if not 1 <= price <= 99999:
                await update.message.reply_text(
                    "❌ GRAM: цена должна быть от 1 до 99999."
                )
                return
            currency = "GRAM"

        else:
            if not 125 <= price <= 9999999:
                await update.message.reply_text(
                    "❌ ЗВЁЗДЫ: цена должна быть от 125 до 9999999."
                )
                return
            currency = "ЗВЁЗДЫ"

        # Генерация текста на основе введённых данных
        nickname = user["nickname"]

        # Последние цифры берутся из введённой цены NFT
        # В данном сценарии это введённая цена.
        symbols = (
            f"{nickname} ُ"
            + (" " * 15)
            + str(price)
        )

        link = sessions.get(uid, {}).get("link", "")

        result = (
            "✅ Символы созданы!\n\n"
            f"👤 Никнейм: {nickname}\n"
            f"🔗 NFT: {link}\n"
            f"💰 Цена: {price} {currency}\n\n"
            "🔤 Результат:\n"
            f"{symbols}"
        )

        states[uid] = None
        sessions.pop(uid, None)

        await update.message.reply_text(
            result,
            reply_markup=menu_keyboard()
        )
        return


def main():
    load_users()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages
        )
    )

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()


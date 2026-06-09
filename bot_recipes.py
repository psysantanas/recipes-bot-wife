import logging
import json
import os
from datetime import date
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ============================
# НАСТРОЙКИ
# ============================

TELEGRAM_TOKEN = "8896114803:AAHLgBI4e-4wkG8elYgFgvbTd4tEMerh4hQ"
GROQ_API_KEY = "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"

HISTORY_FILE = "meal_history.json"
FAVORITES_FILE = "favorites.json"


# ============================
# ФАЙЛЫ
# ============================

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"lunches": [], "dinners": [], "last_reset": str(date.today())}


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


def save_favorites(favorites):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def add_to_history(history, meal_type, dish_name):
    key = "lunches" if meal_type == "lunch" else "dinners"
    if key not in history:
        history[key] = []
    history[key].append({"dish": dish_name, "date": str(date.today())})
    history[key] = history[key][-30:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ============================
# GROQ
# ============================

def ask_groq(prompt):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты заботливый домашний повар. Предлагай простые рецепты до 40 минут."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.75
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"🚨 ОШИБКА GROQ: {e}")
        return f"Извини, сейчас проблемы с соединением.\nОшибка: {str(e)[:100]}"


# ============================
# КЛАВИАТУРЫ
# ============================

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🍽 Обед"), KeyboardButton("🌙 Ужин")],
        [KeyboardButton("🍳 Завтрак"), KeyboardButton("🎲 Случайный")],
        [KeyboardButton("📋 История"), KeyboardButton("❤️ Избранное")],
    ], resize_keyboard=True)


def get_recipe_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ещё вариант 👉", callback_data="more")],
        [InlineKeyboardButton("❤️ Сохранить рецепт", callback_data="save")]
    ])


# ============================
# ОБРАБОТЧИКИ
# ============================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❤️ Привет, моя хорошая!\n\n"
        "Просто пиши или нажимай кнопки — я придумаю, что приготовить.",
        reply_markup=get_main_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lower = text.lower()
    print(f"📨 Получено: {text}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        if "обед" in lower:
            prompt = "Придумай вкусное блюдо на обед."
            meal_type = "lunch"
        elif "ужин" in lower:
            prompt = "Придумай лёгкое блюдо на ужин."
            meal_type = "dinner"
        elif "завтрак" in lower:
            prompt = "Придумай простой завтрак."
            meal_type = "lunch"
        elif "история" in lower:
            await update.message.reply_text("📋 История пока в разработке.")
            return
        elif "избранное" in lower:
            await update.message.reply_text("❤️ Избранное пока в разработке.")
            return
        else:
            prompt = f"Придумай простой рецепт: {text}"
            meal_type = "lunch"

        reply = ask_groq(prompt)
        print(f"✅ Получен ответ от Groq длиной {len(reply)} символов")

        dish_name = reply.split("\n")[0].replace("**", "").strip()
        add_to_history(load_history(), meal_type, dish_name)

        await update.message.reply_text(reply, reply_markup=get_recipe_keyboard())

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        await update.message.reply_text("Извини, произошла ошибка. Попробуй ещё раз.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Ищу другой вариант... 🤔")
    reply = ask_groq("Предложи другой вариант блюда")
    await query.message.reply_text(reply, reply_markup=get_recipe_keyboard())


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("❤️ Бот запущен! Жду запросы...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
import asyncio
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "8561984209:AAHoDA8SLa0fHCK-IZrjEJm2jOr-tHKOmdw"
MODERATOR_ID = 7722679810  # ID модератора (@DK_2012)

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_state = {}
last_message_time = {}

# Кнопки выбора
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🐞 Сообщить о баге", callback_data="Баг")],
    [InlineKeyboardButton(text="🚫 Жалоба на читера", callback_data="Читер")],
    [InlineKeyboardButton(text="❓ Другое", callback_data="Другое")]
])

# Приветствие
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Здравствуйте!\n\n"
        "Добро пожаловать в официальный бот поддержки сервера\n"
        "🌍 Age Peacemakers 🌍\n\n"
        "🛠 Здесь вы можете:\n"
        "🐞 Сообщить о баге или ошибке\n"
        "🚫 Пожаловаться на читера\n"
        "❓ Задать вопрос или оставить обращение\n\n"
        "✍️ Выберите категорию ниже и опишите ситуацию.\n"
        "Вы также можете прикрепить скриншоты или видео.\n\n"
        "👮 Наша команда модераторов обязательно рассмотрит ваш запрос.\n"
        "Спасибо, что помогаете делать Age Peacemakers лучше 💙",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Выбор категории
@dp.callback_query()
async def choose_type(call: types.CallbackQuery):
    user_state[call.from_user.id] = call.data
    await call.message.answer(
        "✍️ Опишите вашу проблему\n"
        "Можно отправить текст, фото или видео.",
        parse_mode="Markdown"
    )
    await call.answer()

# Приём сообщений
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    # Антиспам (15 секунд)
    if user_id in last_message_time:
        if time.time() - last_message_time[user_id] < 15:
            await message.answer("⏳ Пожалуйста, подождите 15 секунд перед следующим запросом.")
            return

    last_message_time[user_id] = time.time()

    category = user_state.get(user_id, "Не указано")
    username = f"@{message.from_user.username}" if message.from_user.username else "без username"

    caption = (
        "📩 Новый запрос — Age Peacemakers\n\n"
        f"👤 Игрок: {username}\n"
        f"🆔 ID: {user_id}\n"
        f"📂 Тип: {category}\n\n"
        "📝 Сообщение:"
    )

    if message.text:
        await bot.send_message(
            MODERATOR_ID,
            caption + f"\n{message.text}",
            parse_mode="Markdown"
        )

    elif message.photo:
        await bot.send_photo(
            MODERATOR_ID,
            message.photo[-1].file_id,
            caption=caption,
            parse_mode="Markdown"
        )

    elif message.video:
        await bot.send_video(
            MODERATOR_ID,
            message.video.file_id,
            caption=caption,
            parse_mode="Markdown"
        )

    await message.answer(
        "✅ Сообщение принято!\n\n"
        "👮 Модераторы сервера Age Peacemakers рассмотрят ваш запрос\n"
        "и при необходимости свяжутся с вами.\n\n"
        "Спасибо за обращение 💙",
        parse_mode="Markdown"
    )

# Ответ модератора игроку
@dp.message(lambda msg: msg.reply_to_message and msg.from_user.id == MODERATOR_ID)
async def reply_from_moderator(message: types.Message):
    try:
        original_text = message.reply_to_message.text
        user_id = int(original_text.split("ID: ")[1].split("")[0])

        await bot.send_message(
            user_id,
            "💬 Ответ модератора Age Peacemakers:\n\n" + message.text,
            parse_mode="Markdown"
        )
        await message.answer("✅ Ответ успешно отправлен игроку.")
    except:
        await message.answer("❌ Ошибка: не удалось отправить ответ.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    
    asyncio.run(main())
    

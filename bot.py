import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from python_aternos import Client

TOKEN = "8561984209:AAHoDA8SLa0fHCK-IZrjEJm2jOr-tHKOmdw"
MODERATORS = [7722679810,7806716052]

ATERNOS_USER = "agepeacemakersss"
ATERNOS_PASS = "agepeacemakers"
SERVER_IP = "age_peacemakers.aternos.me"

PRICES = {
    "барон": 20,
    "инквизитор": 30,
    "рыцарь": 35,
    "наёмник": 40,
    "кузнец": 45,
    "кухарь": 50,
    "зодчий": 55,
    "царь": 65
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
pending_donates = {}
aternos_lock = asyncio.Lock()

class DonateForm(StatesGroup):
    waiting_for_nick = State()
    waiting_for_rank = State()

main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 Купить донат", callback_data="buy_donate")],
    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="ℹ️ О сервере", callback_data="server_info")],
    [InlineKeyboardButton(text="📜 Правила", callback_data="rules"), InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
    [InlineKeyboardButton(text="🐞 Баг", callback_data="report_bug"), InlineKeyboardButton(text="🚫 Жалоба", callback_data="report_player")]
])

cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_action")]
])

async def safe_execute_aternos(nickname, rank):
    async with aternos_lock:
        try:
            pause_before = random.randint(10, 25)
            await asyncio.sleep(pause_before)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, execute_aternos_logic, nickname, rank)
            
            pause_after = random.randint(5, 10)
            await asyncio.sleep(pause_after)
            
            return result
        except Exception as e:
            return f"❌ Ошибка системы очереди: {e}"

def execute_aternos_logic(nickname, rank):
    try:
        at = Client.from_credentials(ATERNOS_USER, ATERNOS_PASS)
        servers = at.list_servers()
        target_server = next((s for s in servers if s.address == SERVER_IP), None)
        
        if not target_server:
            return "❌ Сервер не найден в списке аккаунта."

        if target_server.status_num == 1:
            target_server.execute_command(f"lp user {nickname} parent set {rank}")
            return f"✅ Успешно! Ранг `{rank}` выдан игроку `{nickname}` через консоль."
        elif target_server.status_num == 0:
            target_server.start()
            return f"⏳ Сервер был выключен. Помощник отправил сигнал на запуск. Выдайте `{rank}` игроку `{nickname}` вручную позже."
        else:
            return f"⚠️ Сервер в процессе обработки. Выдайте `{rank}` игроку `{nickname}` вручную через сайт."
    except Exception as e:
        return f"❌ Ошибка Aternos (возможна капча): {e}"

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\nДобро пожаловать в бот **Age Peacemakers** 🌍\nЗдесь можно безопасно купить привилегии.",
        reply_markup=main_keyboard
    )

@dp.callback_query(F.data == "buy_donate")
async def start_donate(call: types.CallbackQuery, state: FSMContext):
    ranks_text = "\n".join([f"• **{k.capitalize()}** — {v} ⭐" for k, v in PRICES.items()])
    await call.message.answer(
        f"🛒 **Доступные ранги:**\n{ranks_text}\n\n✍️ Введи свой **Никнейм** точно как в игре:",
        reply_markup=cancel_keyboard
    )
    await state.set_state(DonateForm.waiting_for_nick)
    await call.answer()

@dp.callback_query(F.data == "cancel_action")
async def cancel(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Действие отменено.", reply_markup=main_keyboard)
    await call.answer()

@dp.message(DonateForm.waiting_for_nick)
async def process_nick(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip())
    await message.answer("💎 Теперь напиши название ранга (например: кухарь):", reply_markup=cancel_keyboard)
    await state.set_state(DonateForm.waiting_for_rank)

@dp.message(DonateForm.waiting_for_rank)
async def process_rank(message: types.Message, state: FSMContext):
    rank = message.text.strip().lower()
    if rank not in PRICES:
        await message.answer("❌ Такого ранга нет. Попробуй еще раз:", reply_markup=cancel_keyboard)
        return
    
    data = await state.get_data()
    nickname = data['nickname']
    price = PRICES[rank]
    
    pending_donates[message.from_user.id] = {"nickname": nickname, "rank": rank}
    
    await message.answer(f"🧾 Заказ для `{nickname}`: ранг **{rank.upper()}**.\nЦена: {price} ⭐")
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"Ранг {rank.capitalize()}",
        description=f"Авто-выдача для игрока {nickname}",
        payload="payload_donate",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=price)],
        provider_token="" 
    )
    await state.clear()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: types.Message):
    user_id = message.from_user.id
    info = pending_donates.pop(user_id, None)
    
    if not info:
        await message.answer("❌ Ошибка: Данные платежа потеряны.")
        return

    nick, rank = info['nickname'], info['rank']
    await message.answer("✅ Оплата прошла! Вы поставлены в очередь выдачи. Это займет около 15-30 секунд для защиты от бана IP...")
    
    result = await safe_execute_aternos(nick, rank)
    
    await message.answer(result)
    
    for mod in MODERATORS:
        try:
            await bot.send_message(mod, f"💰 **ПОКУПКА:** `{nick}` купил `{rank}`.\nРезультат: {result}")
        except:
            pass

@dp.callback_query(F.data.in_({"server_info", "profile", "rules", "faq", "report_bug", "report_player"}))
async def info_pages(call: types.CallbackQuery):
    texts = {
        "server_info": f"🌍 IP: `{SERVER_IP}`\n🔌 Port: `25565`",
        "profile": f"👤 Имя: {call.from_user.first_name}\n🆔 ID: `{call.from_user.id}`",
        "rules": "📜 Не читерить, не флудить, уважать администрацию.",
        "faq": "❓ Донат выдается через защищенную очередь. Если покупок много, время ожидания увеличивается.",
        "report_bug": "🐞 Нашел баг? Опиши его администратору в ЛС.",
        "report_player": "🚫 Заметил нарушителя? Пришли ник и доказательства админу."
    }
    await call.message.answer(texts[call.data])
    await call.answer()

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

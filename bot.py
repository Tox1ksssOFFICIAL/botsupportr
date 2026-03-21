import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from python_aternos import Client
from aiocryptopay import CryptoPay

TOKEN = ""
CRYPTO_TOKEN = "ТВОЙ_API_TOKEN_ИЗ_CRYPTO_BOT"
MODERATORS = [7722679810]

ATERNOS_USER = "ТВОЙ_ЛОГИН"
ATERNOS_PASS = "ТВОЙ_ПАРОЛЬ"
SERVER_IP = "age_peacemakers.aternos.me"

PRICES_RUB = {
    "барон": 50,
    "инквизитор": 100,
    "рыцарь": 150,
    "наёмник": 200,
    "кузнец": 300,
    "кухарь": 400,
    "зодчий": 500,
    "царь": 1000
}

PRICES_STARS = {
    "барон": 20,
    "инквизитор": 40,
    "рыцарь": 60,
    "наёмник": 80,
    "кузнец": 120,
    "кухарь": 160,
    "зодчий": 200,
    "царь": 400
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
crypto = CryptoPay(token=CRYPTO_TOKEN)
aternos_lock = asyncio.Lock()
pending_stars = {}

class DonateForm(StatesGroup):
    waiting_for_nick = State()
    waiting_for_rank = State()
    waiting_for_method = State()

main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 Купить донат", callback_data="buy_donate")],
    [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="ℹ️ О сервере", callback_data="server_info")],
    [InlineKeyboardButton(text="📜 Правила", callback_data="rules"), InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
    [InlineKeyboardButton(text="🐞 Баг", callback_data="report_bug"), InlineKeyboardButton(text="🚫 Жалоба", callback_data="report_player")]
])

cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]])

async def safe_execute_aternos(nickname, rank):
    async with aternos_lock:
        try:
            wait_time = random.randint(25, 50)
            await asyncio.sleep(wait_time)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, execute_aternos_logic, nickname, rank)
        except Exception as e:
            return f"❌ Ошибка очереди: {e}"

def execute_aternos_logic(nickname, rank):
    try:
        at = Client.from_credentials(ATERNOS_USER, ATERNOS_PASS)
        server = next((s for s in at.list_servers() if s.address == SERVER_IP), None)
        if not server: return "❌ Сервер не найден в аккаунте."
        if server.status_num == 1:
            server.execute_command(f"lp user {nickname} parent set {rank}")
            return f"✅ Успешно! `{rank}` выдан игроку `{nickname}`."
        elif server.status_num == 0:
            server.start()
            return f"⏳ Сервер был выключен. Бот его запустил. Выдайте `{rank}` для `{nickname}` вручную позже."
        return "⚠️ Сервер в процессе обработки. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка Aternos (Cloudflare): {e}"

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(f"👋 Привет!\nДобро пожаловать в **Age Peacemakers** 🌍\nВыберите нужное действие:", reply_markup=main_keyboard)

@dp.callback_query(F.data == "buy_donate")
async def start_donate(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("✍️ Введите ваш игровой **Никнейм**:", reply_markup=cancel_kb)
    await state.set_state(DonateForm.waiting_for_nick)
    await call.answer()

@dp.message(DonateForm.waiting_for_nick)
async def process_nick(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip())
    ranks = "\n".join([f"• {k.capitalize()}" for k in PRICES_RUB.keys()])
    await message.answer(f"💎 Какой ранг вы хотите приобрести?\n\n{ranks}", reply_markup=cancel_kb)
    await state.set_state(DonateForm.waiting_for_rank)

@dp.message(DonateForm.waiting_for_rank)
async def process_rank(message: types.Message, state: FSMContext):
    rank = message.text.strip().lower()
    if rank not in PRICES_RUB:
        await message.answer("❌ Такого ранга не существует. Напишите название правильно:")
        return
    await state.update_data(rank=rank)
    
    method_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Звёзды ({PRICES_STARS[rank]})", callback_data="pay_stars")],
        [InlineKeyboardButton(text=f"💳 Крипто/Рубли ({PRICES_RUB[rank]}₽)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    await message.answer(f"💳 Выберите способ оплаты для ранга **{rank.upper()}**:", reply_markup=method_kb)
    await state.set_state(DonateForm.waiting_for_method)

@dp.callback_query(F.data == "pay_stars")
async def pay_stars(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    nick, rank = data['nickname'], data['rank']
    pending_stars[call.from_user.id] = {"nick": nick, "rank": rank}
    
    await bot.send_invoice(
        call.message.chat.id, title=f"Ранг {rank}", description=f"Для игрока {nick}",
        payload="stars_pay", currency="XTR", prices=[LabeledPrice(label="XTR", amount=PRICES_STARS[rank])],
        provider_token=""
    )
    await state.clear()
    await call.answer()

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    nick, rank = data['nickname'], data['rank']
    amount = PRICES_RUB[rank]
    inv = await crypto.create_invoice(amount=amount, currency_type='fiat', fiat='RUB', asset='USDT')
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=inv.pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"chk_{inv.invoice_id}_{nick}_{rank}")]
    ])
    await call.message.answer(f"🧾 Счет на **{amount} RUB** создан.\nИгрок: `{nick}`\nПривилегия: `{rank}`\n\nПосле оплаты обязательно нажмите кнопку 'Проверить':", reply_markup=kb)
    await state.clear()
    await call.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def stars_success(message: types.Message):
    info = pending_stars.pop(message.from_user.id, None)
    if info:
        await message.answer("✅ Оплата Звёздами принята! Ожидайте выдачи (очередь защиты 40 сек)...")
        res = await safe_execute_aternos(info['nick'], info['rank'])
        await message.answer(res)
        for mod in MODERATORS:
            try: await bot.send_message(mod, f"💰 **STARS:** `{info['nick']}` купил `{info['rank']}`.\nРезультат: {res}")
            except: pass

@dp.callback_query(F.data.startswith("chk_"))
async def crypto_success(call: types.CallbackQuery):
    _, inv_id, nick, rank = call.data.split("_")
    invs = await crypto.get_invoices(invoice_ids=int(inv_id))
    if invs and invs.status == 'paid':
        await call.message.edit_text("✅ Оплата подтверждена! Ожидайте выдачи (очередь защиты 40 сек)...")
        res = await safe_execute_aternos(nick, rank)
        await call.message.answer(res)
        for mod in MODERATORS:
            try: await bot.send_message(mod, f"💰 **CRYPTO:** `{nick}` купил `{rank}`.\nРезультат: {res}")
            except: pass
    else:
        await call.answer("❌ Оплата еще не подтверждена или счет истек!", show_alert=True)

@dp.callback_query(F.data == "cancel")
async def cancel_all(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Действие отменено.", reply_markup=main_keyboard)
    await call.answer()

@dp.callback_query(F.data.in_({"server_info", "profile", "rules", "faq", "report_bug", "report_player"}))
async def info_pages(call: types.CallbackQuery):
    texts = {
        "server_info": f"🌍 IP: `{SERVER_IP}`\n🔌 Port: `25565`",
        "profile": f"👤 Имя: {call.from_user.first_name}\n🆔 ID: `{call.from_user.id}`",
        "rules": "📜 Не читерить. Не оскорблять администрацию. Вести себя адекватно.",
        "faq": "❓ Донат выдается автоматически через очередь защиты. Если сервер выключен, бот запустит его сам.",
        "report_bug": "🐞 Нашли баг? Опишите его администратору.",
        "report_player": "🚫 Заметили читера? Пришлите ник и доказательства админу."
    }
    await call.message.answer(texts[call.data])
    await call.answer()

async def main():
    try: await bot.delete_webhook(drop_pending_updates=True)
    except: pass
    print("🚀 Бот Age Peacemakers запущен и готов к продажам!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

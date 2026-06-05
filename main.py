from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import os
import logging

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция расчёта пошлины
def calculate_duty(sale_price, rate2, duty_pct):
    base = sale_price * 0.99 - rate2
    return max(0, base * (duty_pct / 100))

# Режим 1: подбор цены продажи ($) для заданной наценки
def calculate_sale_price(purchase_rub, exchange_rate, rate1, rate2, other, margin, duty_pct):
    purchase_usd = purchase_rub / exchange_rate
    base_cost = purchase_usd + rate1 + rate2 + other
    price = base_cost * (1 + margin / 100)

    # Итеративный расчёт с учётом пошлины
    while True:
        duty = calculate_duty(price, rate2, duty_pct)
        total_cost = base_cost + duty
        new_price = total_cost * (1 + margin / 100)
        if abs(new_price - price) < 0.01:
            break
        price = new_price
    return round(price, 2)

# Режим 2: подбор цены закупки (₽) для заданной наценки
def calculate_purchase_price(sale_price, exchange_rate, rate1, rate2, other, margin, duty_pct):
    duty = calculate_duty(sale_price, rate2, duty_pct)
    cost = sale_price / (1 + margin / 100)  # себестоимость без наценки
    usd = cost - rate1 - rate2 - other - duty  # стоимость закупки в USD
    rub = usd * exchange_rate  # конвертируем в рубли
    return max(0, round(rub, 2))

# Режим 3: вычисление наценки (%)
def calculate_margin(sale_price, purchase_rub, exchange_rate, rate1, rate2, other, duty_pct):
    purchase_usd = purchase_rub / exchange_rate  # цена закупки в долларах
    base_cost = purchase_usd + rate1 + rate2 + other  # базовая себестоимость
    duty = calculate_duty(sale_price, rate2, duty_pct)  # пошлина
    total_cost = base_cost + duty  # полная себестоимость
    margin_percent = ((sale_price / total_cost) - 1) * 100  # формула наценки
    return max(0, round(margin_percent, 2))

# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "<b>🤖 Telegram-бот для расчётов</b>\n\n"
        "Введите числа через пробел:\n"
        "<code>режим параметры...</code>\n\n"
        "🔢 <b>Режим 1</b>: подбор цены продажи ($) — 8 чисел\n"
        "🔢 <b>Режим 2</b>: подбор цены закупки (₽) — 8 чисел\n"
        "🔢 <b>Режим 3</b>: вычисление наценки (%) — 8 чисел\n\n"
        "Формат для режимов 1–2:\n"
        "<code>режим наценка курс пошлины прочие закупка/продажа ставка1 ставка2</code>\n"
        "Формат для режима 3:\n"
        "<code>режим закупка курс пошлины прочие продажа ставка1 ставка2</code>\n\n"
        "Примеры:\n"
        "Режим 1: <code>1 15 75 10 5 50000 10 20</code>\n"
        "Режим 2: <code>2 15 75 10 5 600 10 20</code>\n"
        "Режим 3: <code>3 50000 75 10 5 600 10 20</code>",
        parse_mode="HTML"
    )

# Основной обработчик сообщений
@dp.message()
async def calculate(message: types.Message):
    try:
        if not message.text:
            return

        parts = message.text.strip().split()
        if not parts:
            return

        # Преобразуем строку в список чисел
        data = list(map(float, parts))

        # Извлекаем режим — первый элемент, преобразуем в int
        mode = int(data[0])

        # Проверка количества чисел
        if mode in [1, 2] and len(data) != 8:
            await message.answer("❌ Для режимов 1 и 2 нужно ровно 8 чисел!")
            return
        elif mode == 3 and len(data) != 8:
            await message.answer("❌ Для режима 3 нужно ровно 8 чисел!")
            return

        # Распаковываем параметры в зависимости от режима и формируем вывод с исходными данными и пиктограммами
        if mode == 1:
            margin, rate, duty_pct, other, purchase_rub, r1, r2 = data[1:8]
            result = calculate_sale_price(purchase_rub, rate, r1, r2, other, margin, duty_pct)
            response = (
                f"<b>🔍 Режим 1 — Подбор цены продажи</b>\n\n"
                f"💹 Курс: {rate} ₽/$  |  🏦 Цена закупки: {purchase_rub} ₽\n"
                f"🛠 Ставки: {r1} $ + {r2} $  |  📋 Прочие: {other} $\n"
                f"📊 Наценка: {margin}%  |  🏛 Пошлина: {duty_pct}%\n"
                f"🛒 <b>Цена продажи: {result} $</b>"
            )
            await message.answer(response, parse_mode="HTML")

        elif mode == 2:
            margin, rate, duty_pct, other, sale_price, r1, r2 = data[1:8]
            result = calculate_purchase_price(sale_price, rate, r1, r2, other, margin, duty_pct)
            response = (
                f"<b>🔍 Режим 2 — Подбор цены закупки</b>\n\n"
                f"💵 Цена продажи: {sale_price} $  |  💹 Курс: {rate} ₽/$\n"
                f"🛠 Ставки: {r1} $ + {r2} $  |  📋 Прочие: {other} $\n"
                f"📊 Наценка: {margin}%  |  🏛 Пошлина: {duty_pct}%\n"
                f"🛒 <b>Цена закупки: {result} ₽</b>"
            )
            await message.answer(response, parse_mode="HTML")

        elif mode == 3:
            purchase_rub, rate, duty_pct, other, sale_price, r1, r2 = data[1:8]
            result = calculate_margin(sale_price, purchase_rub, rate, r1, r2, other, duty_pct)
            response = (
                f"<b>🔍 Режим 3 — Вычисление наценки</b>\n\n"
                f"🏦 Цена закупки: {purchase_rub} ₽  |  💵 Цена продажи: {sale_price} $\n"
                f"🛠 Ставки: {r1} $ + {r2} $  |  📋 Прочие: {other} $\n"
                f"💹 Курс: {rate} ₽/$  |  🏛 Пошлина: {duty_pct}%\n"
                f"🛒 <b>Наценка: {result}%</b>"
            )
            await message.answer(response, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, polling_timeout=30, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    WebAppInfo, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

# 1. ТВОИ ДАННЫЕ
BOT_TOKEN = "7879795402:AAGiZAtx5oeJjhiRKmu5eErQ3v4Jhyr3Bto"
WEBAPP_URL = "https://adlkasov.github.io/Mixfoodprotonew/" 

MANAGER_CHAT_ID = "8416984139" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- 1. КОМАНДА /START ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🍔 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await message.answer(
        "Привет! Я бот доставки <b>MIXFOOD</b> 🍕\n\nНажми на кнопку ниже, чтобы сделать заказ.", 
        reply_markup=markup,
        parse_mode="HTML"
    )

# --- 2. ПРИЕМ ЗАКАЗА ОТ MINI APP ---
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    # Получаем Telegram ID клиента (чтобы потом присылать ему статусы)
    customer_id = message.from_user.id
    
    # Генерируем короткий номер заказа (например, #4829)
    order_number = f"#{random.randint(1000, 9999)}"
    
    customer = data.get('customer', {})
    items = data.get('items', [])
    
    # Формируем текст чека
    text = f"<b>🧾 ЗАКАЗ {order_number}</b>\n\n"
    text += f"👤 <b>Клиент:</b> {customer.get('name')}\n"
    text += f"📞 <b>Телефон:</b> {customer.get('phone')}\n"
    text += f"📍 <b>Адрес:</b> {customer.get('address')}\n"
    if customer.get('comment'):
        text += f"💬 <b>Комментарий:</b> {customer.get('comment')}\n"
        
    text += f"\n🛒 <b>Состав:</b>\n"
    for item in items:
        text += f"▫️ {item['name']} — {item['qty']} шт. ({item['qty'] * item['price']} тг)\n"
        
    text += f"\n💰 <b>Итого:</b> {data.get('totalPrice')} тг ({data.get('paymentMethod')})"

    # Отправляем подтверждение КЛИЕНТУ
    await message.answer(f"✅ Ваш заказ <b>{order_number}</b> успешно оформлен и передан на кухню!\n\nОжидайте уведомлений о статусе.", parse_mode="HTML")

    # Создаем кнопки статусов для МЕНЕДЖЕРА
    # В callback_data мы прячем ID клиента и номер заказа (формат: статус|id|номер)
    manager_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принят", callback_data=f"status:accepted:{customer_id}:{order_number}")],
        [InlineKeyboardButton(text="🍳 Готовится", callback_data=f"status:preparing:{customer_id}:{order_number}")],
        [InlineKeyboardButton(text="🛵 Доставляется", callback_data=f"status:delivering:{customer_id}:{order_number}")],
        [InlineKeyboardButton(text="🏁 Завершен", callback_data=f"status:done:{customer_id}:{order_number}")]
    ])

    # Отправляем чек с кнопками МЕНЕДЖЕРУ
    try:
        await bot.send_message(MANAGER_CHAT_ID, text, reply_markup=manager_keyboard, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при отправке менеджеру (проверь MANAGER_CHAT_ID): {e}")


# --- 3. ОБРАБОТКА НАЖАТИЙ КНОПОК МЕНЕДЖЕРОМ ---
# Ловим все нажатия на кнопки, где callback_data начинается с "status:"
@dp.callback_query(F.data.startswith("status:"))
async def process_status_update(callback: types.CallbackQuery):
    # Разбиваем спрятанные данные: "status:preparing:123456789:#4829"
    _, status_code, customer_id, order_number = callback.data.split(":")
    
    # Словарь со статусами для красивого вывода
    statuses = {
        "accepted": "✅ <b>Принят в работу</b>. Скоро начнем готовить!",
        "preparing": "🍳 <b>Готовится</b>. Повара уже колдуют над вашим заказом.",
        "delivering": "🛵 <b>В пути</b>. Курьер уже мчится к вам по адресу!",
        "done": "🏁 <b>Завершен</b>. Приятного аппетита! Ждем вас снова."
    }
    
    status_text = statuses.get(status_code, "Обновлен")
    
    # Отправляем уведомление КЛИЕНТУ по его ID
    try:
        await bot.send_message(
            chat_id=int(customer_id),
            text=f"🔔 <b>Обновление по заказу {order_number}</b>\n\nНовый статус: {status_text}",
            parse_mode="HTML"
        )
        
        # Уведомляем менеджера (всплывающее окно), что клиент получил пуш
        await callback.answer(f"Статус отправлен клиенту!", show_alert=False)
        
    except Exception as e:
        await callback.answer("Ошибка: не удалось отправить сообщение клиенту.", show_alert=True)

# Запуск
async def main():
    print("Бот запущен! Ожидаю заказы...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

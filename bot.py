import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

BOT_TOKEN = "7879795402:AAGiZAtx5oeJjhiRKmu5eErQ3v4Jhyr3Bto"
WEBAPP_URL = "https://adlkasov.github.io/Mixfoodprotonew/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обрабатываем команду /start
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    # Создаем кнопку (Reply Keyboard), которая будет открывать твой сайт
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍔 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Привет! Я бот доставки <b>MIXFOOD</b> 🍕\n\nНажми на кнопку ниже, чтобы открыть меню и сделать заказ.", 
        reply_markup=markup,
        parse_mode="HTML"
    )

# Ловим данные, которые отправляет наш сайт через tg.sendData()
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    # Данные приходят в виде JSON-строки, превращаем её в Python-словарь
    data = json.loads(message.web_app_data.data)
    
    customer = data.get('customer', {})
    items = data.get('items', [])
    
    # Красиво форматируем чек заказа
    text = f"<b>🔔 НОВЫЙ ЗАКАЗ!</b>\n\n"
    text += f"👤 <b>Клиент:</b> {customer.get('name')}\n"
    text += f"📞 <b>Телефон:</b> {customer.get('phone')}\n"
    text += f"📍 <b>Адрес:</b> {customer.get('address')}\n"
    
    if customer.get('comment'):
        text += f"💬 <b>Комментарий:</b> {customer.get('comment')}\n"
        
    text += f"\n🛒 <b>Состав заказа:</b>\n"
    for item in items:
        # Считаем сумму по каждой позиции
        item_sum = item['qty'] * item['price']
        text += f"▫️ {item['name']} — {item['qty']} шт. ({item_sum} тг)\n"
        
    text += f"\n💳 <b>Способ оплаты:</b> {data.get('paymentMethod')}\n"
    text += f"💰 <b>Итого к оплате:</b> {data.get('totalPrice')} тг"

    # Отправляем сформированный чек обратно пользователю
    # (в будущем сюда можно добавить пересылку сообщения в чат курьеров или менеджеров)
    await message.answer(text, parse_mode="HTML")

# Запуск бота
async def main():
    print("Бот запущен! Зайди в Telegram и напиши ему /start")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

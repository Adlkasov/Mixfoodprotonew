import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7879795402:AAGiZAtx5oeJjhiRKmu5eErQ3v4Jhyr3Bto"
WEBAPP_URL = "https://adlkasov.github.io/Mixfoodprotonew/"
MANAGER_ID = 8416984139

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная база данных в памяти (для MVP)
# Формат: {'1054': {'user_id': 987654321, 'status': 'Создан', 'method': 'kaspi'}}
orders_db = {}

# --- ГЕНЕРАЦИЯ КЛАВИАТУРЫ МЕНЕДЖЕРА ---
def get_manager_keyboard(order_id, method):
    buttons = []
    
    if method == 'kaspi':
        buttons.append([InlineKeyboardButton(text="🧾 Выставил счет Kaspi", callback_data=f"status_{order_id}_billed")])
        buttons.append([InlineKeyboardButton(text="✅ Оплата получена", callback_data=f"status_{order_id}_paid")])
    
    buttons.append([
        InlineKeyboardButton(text="🍳 Готовится", callback_data=f"status_{order_id}_cooking"),
        InlineKeyboardButton(text="🛵 В пути", callback_data=f"status_{order_id}_delivering")
    ])
    buttons.append([InlineKeyboardButton(text="🎉 Доставлен", callback_data=f"status_{order_id}_done")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- СТАРТ ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🍔 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку ниже, чтобы сделать заказ 🍕", reply_markup=markup)

# --- ПРИЕМ ЗАКАЗА ИЗ WEB APP ---
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    customer = data.get('customer', {})
    payment = data.get('payment', {})
    items = data.get('items', [])
    total_price = data.get('totalPrice', 0)
    
    # Генерируем номер заказа
    order_id = str(random.randint(1000, 9999))
    orders_db[order_id] = {
        'user_id': message.from_user.id,
        'status': 'Создан',
        'method': payment.get('method')
    }
    
    # 1. ОТВЕТ КЛИЕНТУ
    items_text = "\n".join([f"▫️ {i['name']} — {i['qty']} шт." for i in items])
    
    client_text = f"✅ <b>Заказ #{order_id} успешно создан!</b>\n\n🛒 <b>Состав:</b>\n{items_text}\n\n💰 <b>Итого:</b> {total_price} тг\n\n"
    
    if payment.get('method') == 'kaspi':
        client_text += "⏳ <i>Ожидайте, менеджер скоро выставит вам счет в приложении Kaspi. Мы пришлем уведомление!</i>"
    else:
        client_text += "💵 <i>Оплата наличными при получении. Ваш заказ уже передан на кухню!</i>"
        
    await message.answer(client_text, parse_mode="HTML")
    
    # 2. ОТПРАВКА МЕНЕДЖЕРУ
    mgr_text = f"🚨 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
    mgr_text += f"👤 {customer.get('name')} | 📞 {customer.get('phone')}\n📍 {customer.get('address')}\n"
    if customer.get('comment'): mgr_text += f"💬 Коммент: {customer.get('comment')}\n"
    
    mgr_text += f"\n🛒 Заказ:\n{items_text}\n\n💰 Сумма: <b>{total_price} тг</b>\n"
    
    if payment.get('method') == 'kaspi':
        mgr_text += f"\n💳 <b>ОПЛАТА KASPI</b>\nНужно выставить счет на:\n"
        mgr_text += f"Номер: <code>{payment.get('kaspiPhone')}</code>\nИмя: {payment.get('kaspiName')}"
    else:
        mgr_text += f"\n💵 <b>ОПЛАТА НАЛИЧНЫМИ</b>"

    kb = get_manager_keyboard(order_id, payment.get('method'))
    await bot.send_message(chat_id=MANAGER_ID, text=mgr_text, reply_markup=kb, parse_mode="HTML")

# --- ОБРАБОТКА СТАТУСОВ ОТ МЕНЕДЖЕРА ---
@dp.callback_query(F.data.startswith("status_"))
async def status_handler(call: types.CallbackQuery):
    # Разбираем callback_data (например, "status_1234_paid")
    _, order_id, action = call.data.split("_")
    
    if order_id not in orders_db:
        await call.answer("Ошибка: Заказ не найден в базе!", show_alert=True)
        return
        
    user_id = orders_db[order_id]['user_id']
    
    # Логика статусов и уведомлений клиента
    user_msg = ""
    if action == "billed":
        user_msg = f"🧾 <b>По заказу #{order_id} выставлен счет!</b>\nПожалуйста, перейдите в приложение Kaspi.kz и оплатите его."
    elif action == "paid":
        user_msg = f"✅ <b>Оплата по заказу #{order_id} получена!</b>\nНачинаем готовить 🍳"
    elif action == "cooking":
        user_msg = f"🍳 <b>Ваш заказ #{order_id} готовится!</b>"
    elif action == "delivering":
        user_msg = f"🛵 <b>Ваш заказ #{order_id} передан курьеру и уже в пути!</b>"
    elif action == "done":
        user_msg = f"🎉 <b>Заказ #{order_id} доставлен. Приятного аппетита!</b>"

    # Отправляем уведомление клиенту
    if user_msg:
        try:
            await bot.send_message(chat_id=user_id, text=user_msg, parse_mode="HTML")
        except Exception as e:
            await call.answer("Не удалось отправить сообщение клиенту (возможно он заблокировал бота)", show_alert=True)
            return

    # Подтверждаем нажатие менеджеру
    await call.answer(f"Статус обновлен: {action}")
    
    # Опционально: можно менять текст самого сообщения менеджера (добавлять [ОПЛАЧЕНО] и т.д.)

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

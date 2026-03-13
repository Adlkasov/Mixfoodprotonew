import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# --- НАСТРОЙКИ ---
BOT_TOKEN = "7879795402:AAGiZAtx5oeJjhiRKmu5eErQ3v4Jhyr3Bto"
WEBAPP_URL = "https://adlkasov.github.io/Mixfoodprotonew/"
MANAGER_ID = 8416984139  # Telegram ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ (в памяти) ---
orders_db = {}

# --- ФУНКЦИЯ: ГЕНЕРАЦИЯ ТЕКСТА ДЛЯ МЕНЕДЖЕРА ---
def get_manager_text(order_id, data):
    # Яркий заголовок со статусом
    status_emoji = {
        'Создан': '🆕', 'Счет выставлен': '🧾', 'Оплачен': '✅',
        'Готовится': '🍳', 'В пути': '🛵', 'Доставлен': '🎉'
    }
    emoji = status_emoji.get(data['status'], '📌')
    
    text = f"{emoji} <b>ЗАКАЗ #{order_id} | Статус: {data['status'].upper()}</b>\n\n"
    
    text += f"👤 <b>Клиент:</b> {data['name']} | 📞 {data['phone']}\n"
    text += f"📍 <b>Адрес:</b> {data['address']}\n"
    if data['comment']: 
        text += f"💬 <b>Коммент:</b> {data['comment']}\n"
    
    text += f"\n🛒 <b>Состав:</b>\n{data['items_text']}\n\n💰 <b>Сумма: {data['total_price']} тг</b>\n"
    
    if data['method'] == 'kaspi':
        text += f"\n💳 <b>ОПЛАТА KASPI</b>\n"
        text += f"Реквизиты для счета: <code>{data['kaspiPhone']}</code> ({data['kaspiName']})"
    else:
        text += f"\n💵 <b>ОПЛАТА НАЛИЧНЫМИ (при получении)</b>"
        
    return text

# --- ФУНКЦИЯ: ГЕНЕРАЦИЯ КНОПОК ДЛЯ МЕНЕДЖЕРА ---
def get_manager_keyboard(order_id, status, method):
    buttons = []
    
    # Если заказ доставлен, убираем все кнопки
    if status == 'Доставлен':
        return None

    # Кнопки для Kaspi (показываем только если еще не оплачено)
    if method == 'kaspi' and status in ['Создан']:
        buttons.append([InlineKeyboardButton(text="🧾 Выставил счет", callback_data=f"status_{order_id}_billed")])
    elif method == 'kaspi' and status in ['Счет выставлен']:
        buttons.append([InlineKeyboardButton(text="✅ Оплата получена", callback_data=f"status_{order_id}_paid")])
    
    # Стандартные статусы (показываем, если наличные или если Kaspi уже оплачен)
    if method == 'cash' or status not in ['Создан', 'Счет выставлен']:
        row = []
        if status != 'Готовится':
            row.append(InlineKeyboardButton(text="🍳 Готовится", callback_data=f"status_{order_id}_cooking"))
        if status != 'В пути':
            row.append(InlineKeyboardButton(text="🛵 В пути", callback_data=f"status_{order_id}_delivering"))
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton(text="🎉 Завершить (Доставлен)", callback_data=f"status_{order_id}_done")])
    
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
    
    order_id = str(random.randint(1000, 9999))
    items_text = "\n".join([f"▫️ {i['name']} — {i['qty']} шт." for i in data.get('items', [])])
    
    # Сохраняем ВСЕ данные в словарь, чтобы потом их можно было редактировать
    orders_db[order_id] = {
        'user_id': message.from_user.id,
        'status': 'Создан',
        'method': data.get('payment', {}).get('method'),
        'name': data.get('customer', {}).get('name'),
        'phone': data.get('customer', {}).get('phone'),
        'address': data.get('customer', {}).get('address'),
        'comment': data.get('customer', {}).get('comment'),
        'items_text': items_text,
        'total_price': data.get('totalPrice', 0),
        'kaspiPhone': data.get('payment', {}).get('kaspiPhone', ''),
        'kaspiName': data.get('payment', {}).get('kaspiName', '')
    }
    
    # 1. ОТВЕТ КЛИЕНТУ (остается как было)
    client_text = f"✅ <b>Заказ #{order_id} успешно создан!</b>\n\n🛒 <b>Состав:</b>\n{items_text}\n\n💰 <b>Итого:</b> {orders_db[order_id]['total_price']} тг\n\n"
    if orders_db[order_id]['method'] == 'kaspi':
        client_text += "⏳ <i>Ожидайте, менеджер скоро выставит вам счет в приложении Kaspi. Мы пришлем уведомление!</i>"
    else:
        client_text += "💵 <i>Оплата наличными при получении. Ваш заказ уже передан на кухню!</i>"
        
    await message.answer(client_text, parse_mode="HTML")
    
    # 2. ОТПРАВКА МЕНЕДЖЕРУ
    mgr_text = get_manager_text(order_id, orders_db[order_id])
    kb = get_manager_keyboard(order_id, 'Создан', orders_db[order_id]['method'])
    
    await bot.send_message(chat_id=MANAGER_ID, text=mgr_text, reply_markup=kb, parse_mode="HTML")

# --- ОБРАБОТКА СТАТУСОВ ОТ МЕНЕДЖЕРА ---
@dp.callback_query(F.data.startswith("status_"))
async def status_handler(call: types.CallbackQuery):
    _, order_id, action = call.data.split("_")
    
    if order_id not in orders_db:
        await call.answer("Ошибка: Заказ устарел или не найден в базе!", show_alert=True)
        return
        
    user_id = orders_db[order_id]['user_id']
    
    # 1. Определяем новый статус и сообщение для клиента
    user_msg = ""
    new_status = ""
    
    if action == "billed":
        new_status = "Счет выставлен"
        user_msg = f"🧾 <b>По заказу #{order_id} выставлен счет!</b>\nПожалуйста, перейдите в Kaspi.kz и оплатите его."
    elif action == "paid":
        new_status = "Оплачен"
        user_msg = f"✅ <b>Оплата по заказу #{order_id} получена!</b>\nНачинаем готовить 🍳"
    elif action == "cooking":
        new_status = "Готовится"
        user_msg = f"🍳 <b>Ваш заказ #{order_id} готовится!</b>"
    elif action == "delivering":
        new_status = "В пути"
        user_msg = f"🛵 <b>Ваш заказ #{order_id} передан курьеру и уже в пути!</b>"
    elif action == "done":
        new_status = "Доставлен"
        user_msg = f"🎉 <b>Заказ #{order_id} доставлен. Приятного аппетита!</b>"

    # 2. Обновляем статус в базе
    orders_db[order_id]['status'] = new_status

    # 3. ОБНОВЛЯЕМ СООБЩЕНИЕ У МЕНЕДЖЕРА
    mgr_text = get_manager_text(order_id, orders_db[order_id])
    kb = get_manager_keyboard(order_id, new_status, orders_db[order_id]['method'])
    
    try:
        # Вот эта магия меняет текст текущего сообщения
        await call.message.edit_text(text=mgr_text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        # Ошибка возникает, если попытаться обновить сообщение на точно такое же (например, дважды кликнули)
        pass

    # 4. Отправляем уведомление клиенту
    if user_msg:
        try:
            await bot.send_message(chat_id=user_id, text=user_msg, parse_mode="HTML")
        except Exception:
            await call.answer("Статус изменен, но клиент заблокировал бота.", show_alert=True)
            return

    # Завершаем обработку нажатия (чтобы часики на кнопке перестали крутиться)
    await call.answer(f"Статус изменен на: {new_status}")

async def main():
    print("Бот запущен! Идет прием заказов...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

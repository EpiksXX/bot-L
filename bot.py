import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

# === НАСТРОЙКИ ===
BOT_TOKEN = "8605918168:AAGKyy0fUB8bajEV7evGqpnjZfFciJMUG5Q"
PHONE_IP = "192.168.1.88"  # IP твоего телефона
MAX_HISTORY = 10           # Сколько последних сообщений помнит бот (5 твоих, 5 её)
# =================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения памяти: {user_id: [{"role": "user", "content": "..."}, ...]}
users_history = {}

async def ask_gemma(user_id: int, user_text: str) -> str:
    url = f"http://{PHONE_IP}:8080/v1/chat/completions"
    
    # Если пользователь пишет впервые, создаем для него пустую память
    if user_id not in users_history:
        users_history[user_id] = []
        
    # Добавляем новый вопрос в память пользователя
    users_history[user_id].append({"role": "user", "content": user_text})
    
    # Обрезаем историю, если она стала слишком длинной, чтобы не перегрузить память телефона
    if len(users_history[user_id]) > MAX_HISTORY:
        users_history[user_id] = users_history[user_id][-MAX_HISTORY:]

    # Собираем финальный список сообщений: Системный промпт + История диалога
    messages = [
        {
            "role": "system", 
            "content": "Тебя зовут Хлоя. Ты серьезная, умная, но в глубине души очень милая девушка-ассистент. "
                       "Твои правила: "
                       "1. Отвечай максимально коротко и по делу (1-2 предложения). "
                       "2. Общайся вежливо, с легкой заботой, но без лишних эмоций. "
                       "3. Категорически ЗАПРЕЩЕНО использовать эмодзи. "
                       "4. ЗАПРЕЩЕНО описывать свои действия в звездочках или скобках. Пиши только чистый текст своей речи."
        }
    ] + users_history[user_id]

    payload = {
        "messages": messages,
        "temperature": 0.4
    }
    
    # Делаем асинхронный запрос к Termux на телефоне
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_text = data["choices"][0]["message"]["content"]
                    
                    # Сохраняем ответ Хлои в память, чтобы она помнила, что сказала
                    users_history[user_id].append({"role": "assistant", "content": ai_text})
                    
                    return ai_text
                else:
                    # Если ошибка, удаляем последний вопрос из памяти, так как на него не было ответа
                    users_history[user_id].pop()
                    return f"❌ Ошибка от телефона: {response.status}"
        except Exception as e:
            users_history[user_id].pop()
            return f"❌ Не могу достучаться до телефона. Он в сети?\nОшибка: {e}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Очищаем память при старте
    users_history[message.from_user.id] = []
    await message.answer("Привет! Я Хлоя. Задавай свой вопрос.")

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    # Команда для ручной очистки памяти
    users_history[message.from_user.id] = []
    await message.answer("Память очищена. Я забыла наш предыдущий разговор.")

@dp.message()
async def handle_message(message: Message):
    # Показываем пользователю статус "Печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Идем за ответом на телефон, передавая ID пользователя
    ai_response = await ask_gemma(message.from_user.id, message.text)
    
    # Отправляем результат обратно в телегу
    await message.answer(ai_response)

async def main():
    print("🤖 Бот успешно запущен, память активирована!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

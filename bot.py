import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

# === НАСТРОЙКИ ===
BOT_TOKEN = "AAGKyy0fUB8bajEV7evGqpnjZfFciJMUG5Q"
PHONE_IP = "192.168.1.88"  # Замени на IP твоего телефона
# =================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def ask_gemma(user_text: str) -> str:
    url = f"http://{PHONE_IP}:8080/v1/chat/completions"
    payload = {
        "messages": [
            {
                "role": "system", 
                "content": "Ты полезный текстовый ИИ-ассистент. Отвечай прямо и по делу."
            },
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.5
    }
    
    # Делаем асинхронный запрос к Termux на телефоне
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"❌ Ошибка от телефона: {response.status}"
        except Exception as e:
            return f"❌ Не могу достучаться до телефона. Он в сети?\nОшибка: {e}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я на связи с нейросетью. Напиши мне любой вопрос.")

@dp.message()
async def handle_message(message: Message):
    # Показываем пользователю статус "Печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Идем за ответом на телефон
    ai_response = await ask_gemma(message.text)
    
    # Отправляем результат обратно в телегу
    await message.answer(ai_response)

async def main():
    print("🤖 Бот успешно запущен и ждет сообщений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

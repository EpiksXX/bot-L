import asyncio
import aiohttp
import os
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PHONE_IP = os.getenv("PHONE_IP")
MAX_HISTORY = 10
HISTORY_FILE = "data/history.json" # Файл будет лежать в защищенной папке Docker

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_locks = {}

def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

# --- НОВЫЙ БЛОК: РАБОТА С ПАМЯТЬЮ (JSON) ---
def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # JSON сохраняет ключи как строки, переводим их обратно в числа (ID юзеров)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"⚠️ Ошибка чтения памяти: {e}")
    return {}

def save_history():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(users_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения памяти: {e}")
# ---------------------------------------------

# Загружаем память при старте
users_history = load_history()

async def ask_gemma(user_id: int, user_text: str) -> str:
    url = f"http://{PHONE_IP}:8080/v1/chat/completions"
    
    if user_id not in users_history:
        users_history[user_id] = []
        
    users_history[user_id].append({"role": "user", "content": user_text})
    
    if len(users_history[user_id]) > MAX_HISTORY:
        users_history[user_id] = users_history[user_id][-MAX_HISTORY:]

    messages = [
        {
            "role": "system", 
            "content": "Тебя зовут Хлоя. Ты серьезная, умная, но в глубине души очень милая девушка-ассистент. "
                       "Твои правила: "
                       "Импровизируй в диалоге когда спрашивают на счёт твоих личных предпочтений"
                       "1. Отвечай максимально коротко и по делу (2-3 предложения)."
                       "2. Общайся вежливо, с легкой заботой, но без лишних эмоций. "
                       "3. Категорически ЗАПРЕЩЕНО использовать эмодзи. "
                       "4. ЗАПРЕЩЕНО описывать свои действия в звездочках или скобках."
        }
    ] + users_history[user_id]

    payload = {"messages": messages, "temperature": 0.8}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_text = data["choices"][0]["message"]["content"]
                    
                    users_history[user_id].append({"role": "assistant", "content": ai_text})
                    save_history() # <-- Сохраняем в JSON после успешного ответа
                    
                    return ai_text
                else:
                    users_history[user_id].pop()
                    return f"❌ Ошибка от телефона: {response.status}"
        except Exception as e:
            users_history[user_id].pop()
            return f"❌ Не могу достучаться до телефона. Ошибка: {e}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    users_history[message.from_user.id] = []
    save_history()
    await message.answer("Привет! Я Хлоя. Готова к работе.")

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    users_history[message.from_user.id] = []
    save_history()
    await message.answer("Память очищена. Я забыла наш предыдущий разговор.")

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    lock = get_user_lock(user_id)
    
    if lock.locked():
        await message.answer("⏳ Подожди, я еще формулирую ответ на твой прошлый вопрос...")
        return

    async with lock:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        ai_response = await ask_gemma(user_id, message.text)
        await message.answer(ai_response)

async def main():
    print("🤖 Бот запущен! Память загружена.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

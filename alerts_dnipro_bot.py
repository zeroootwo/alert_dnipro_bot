import asyncio
import os
import logging
import pytz
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from alerts_in_ua import AsyncClient as AsyncAlertsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
DB_NAME = "chats.db"
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY)")
        await db.commit()

async def add_chat(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (chat_id,))
        await db.commit()

async def get_all_chats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT chat_id FROM chats") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_chat(message.chat.id)
    await message.answer("🛡️ Dnipro Alert Bot активований!\nТепер я буду надсилати сповіщення про тривоги в цей чат")

@dp.my_chat_member()
async def on_my_chat_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        await add_chat(event.chat.id)
        logger.info(f"➕ БОТ ДОДАНИЙ В ЧАТ: {event.chat.id} ({event.chat.title})")
    elif event.new_chat_member.status in ["left", "kicked"]:
        logger.info(f"➖ БОТ ВИДАЛЕНИЙ З ЧАТУ: {event.chat.id}")

async def main():
    await init_db()
    alerts_client = AsyncAlertsClient(token=API_KEY)
    shared_data = {"is_alert": False}

    async def is_dnipro_alert():
        logger.info("Запрос к API") 
        active_alerts = await alerts_client.get_active_alerts()
        return any("Дніпр" in str(a.location_title) for a in active_alerts)
        
    @dp.message(Command("status"))
    async def manual_check(message: types.Message):
        status = shared_data["is_alert"]
        text = "🚨 У Дніпрі наразі ТРИВОГА! 🚨" if status else "✅ У Дніпрі наразі ВІДБІЙ ✅"
        await message.answer(text)
        
    asyncio.create_task(dp.start_polling(bot))
    kiev_tz = pytz.timezone('Europe/Kyiv')
    last_status = None
    first_run = True
    while True:
        try:
            current_status = await is_dnipro_alert()
            if current_status is None:
                await asyncio.sleep(30)
                continue
            shared_data["is_alert"] = current_status
            now = datetime.now(kiev_tz).strftime("%H:%M")
            if first_run:
                if current_status:
                    logger.info(f"🚀 Бот запущен. Сейчас в Днепре ТРЕВОГА 🚨")
                else:
                    logger.info(f"🚀 Бот запущен. Сейчас в Днепре ТИХО ✅")
                last_status = current_status
                first_run = False
                await asyncio.sleep(25)
                continue
            if current_status != last_status:
                chats = await get_all_chats()
                if current_status:
                    message_text = f"🚨 УВАГА! Повітряна тривога!\nНегайно пройти в найближче укриття! 🚨 {now}"
                    logger.info("Сообщение о тревоге отправлено")
                else:
                    message_text = f"✅ УВАГА! Відбій ✅ {now}"
                    logger.info("Сообщение о отбое отправлено")
                for chat_id in chats:
                    try:
                        await bot.send_message(chat_id, text=message_text)
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
                last_status = current_status
            await asyncio.sleep(25)
        except Exception as e:
            error_msg = str(e)
            if "Limit" in error_msg or "429" in error_msg:
                logger.error(f"🛑 Превышен лимит запитов! Спим 10 минут... ({error_msg})")
                await asyncio.sleep(600)
            else:
                logger.error(f"❌ Ошибка: {error_msg}")
                await asyncio.sleep(30)
                
if __name__ == "__main__":
    asyncio.run(main())

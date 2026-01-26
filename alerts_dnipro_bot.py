import asyncio
import os
import logging
import pytz
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
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

async def remove_chat(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        await db.commit()

async def get_all_chats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT chat_id FROM chats") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

@dp.my_chat_member()
async def on_my_chat_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        await add_chat(event.chat.id)
        logger.info(f"➕ Бот добавлен в чат {event.chat.id}")
    elif event.new_chat_member.status in ["left", "kicked"]:
        await remove_chat(event.chat.id)
        logger.info(f"➖ Бот удален из чата {event.chat.id}")

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_chat(message.chat.id)
    await message.answer("🛡️ **Dnipro Alert Bot активований!**\nТепер я буду надсилати сповіщення про тривоги в цей чат")

@dp.message(Command("status"))
async def manual_check(message: types.Message, shared_data: dict):
    status = shared_data["is_alert"]
    text = "🚨 У Дніпрі наразі ТРИВОГА! 🚨" if status else "✅ У Дніпрі наразі ВІДБІЙ ✅"
    await message.answer(text)

async def main():
    await init_db()
    alerts_client = AsyncAlertsClient(token=API_KEY)
    shared_data = {"is_alert": False}
    dp["shared_data"] = shared_data
    async def is_dnipro_alert():
        try:
            active_alerts = await alerts_client.get_active_alerts()
            return any("Дніпр" in str(a.location_title) for a in active_alerts)
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            return None
    asyncio.create_task(dp.start_polling(bot))
    kiev_tz = pytz.timezone('Europe/Kyiv')
    last_status = None
    first_run = True
    logger.info("🚀 Бот запускается...")
    while True:
        current_status = await is_dnipro_alert()
        if current_status is None:
            await asyncio.sleep(30)
            continue
        shared_data["is_alert"] = current_status
        now = datetime.now(kiev_tz).strftime("%H:%M")
        if first_run:
            last_status = current_status
            first_run = False
            logger.info(f"Первая проверка: {'ТРЕВОГА' if current_status else 'ТИХО'}")
            await asyncio.sleep(25)
            continue
        if current_status != last_status:
            chats = await get_all_chats()
            if current_status:
                text = f"🚨 **УВАГА! Повітряна тривога!**\nНегайно пройти в найближче укриття! 🚨\n📍{now}"
            else:
                text = f"✅ **ВІДБІЙ тривоги!** ✅\n📍{now}"
            for chat_id in chats:
                try:
                    await bot.send_message(chat_id, text=text, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Не удалось отправить в {chat_id}: {e}")
            last_status = current_status
        await asyncio.sleep(25)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("🤖 Бот остановлен.")

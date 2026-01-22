import asyncio
import os
import logging
import pytz
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from alerts_in_ua import AsyncClient as AsyncAlertsClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔎 Перевірити тривогу наразі")]], resize_keyboard=True)

async def main():
    alerts_client = AsyncAlertsClient(token=API_KEY)
    shared_data = {"is_alert": False}

    async def is_dnipro_alert():
        active_alerts = await alerts_client.get_active_alerts()
        return any("Дніпр" in str(a.location_title) for a in active_alerts)

    @dp.message(F.text == "/status")
    async def manual_check(message: types.Message):
        status = shared_data["is_alert"]
        text = "🚨 У Дніпрі наразі ТРИВОГА! 🚨" if status else "✅ У Дніпрі наразі ВІДБІЙ ✅"
        await message.answer(text)

    asyncio.create_task(dp.start_polling(bot))
    kiev_tz = pytz.timezone('Europe/Kyiv')
    last_status = None
    first_run = True
    logger.info("🚀 Бот запускается и ждет первой проверки...")
    while True:
        try:
            logger.info("🔍 Запрос к API...")
            current_status = await is_dnipro_alert()
            shared_data["is_alert"] = current_status
            now=datetime.now(kiev_tz).strftime("%H:%M")
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
                if current_status:
                    message=f"🚨 УВАГА! Повітряна тривога!\nНегайно пройти в найближче укриття! 🚨{now}"
                    await bot.send_message(CHAT_ID, text=message )
                    logger.info("Сообщение о тревоге отправлено")
                else:
                        message=f"✅ УВАГА! Відбій ✅{now}"
                        await bot.send_message(CHAT_ID, text=message)
                        logger.info("Сообщение о отбое отправлено")
                last_status = current_status
            await asyncio.sleep(25)
        except Exception as e:
            error_msg = str(e)
            if "Limit" in error_msg or "429" in error_msg:
                logger.error(f"🛑 Превышен лимит запросов! Спим 10 минут... ({error_msg})")
                await asyncio.sleep(600)
            else:
                logger.error(f"❌ Ошибка: {error_msg}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("🤖 Бот остановлен.")
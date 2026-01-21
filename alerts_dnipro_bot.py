import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from alerts_in_ua import AsyncClient as AsyncAlertsClient

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

async def main():
    alerts_client = AsyncAlertsClient(API_KEY)
    
    async def is_dnipro_alert():
        active_alerts = await alerts_client.get_active_alerts()
        return any(
            alert.location_title in ["Дніпро", "Дніпропетровська область"]
            for alert in active_alerts
        )
    try:
        last_status = await is_dnipro_alert()
        print(f"✅ Бот запущен. Текущий статус в Днепре: {'ТРЕВОГА' if last_status else 'ОТБОЙ'}")
    except Exception as e:
        last_status = False
        print(f"⚠️ Начальная проверка не удалась: {e}")
    while True:
        try:
            print("🔍 Проверка статуса API...")
            current_status = await is_dnipro_alert()
            if current_status != last_status:
                if current_status is True:
                    await bot.send_message(CHAT_ID, "🚨 **УВАГА! Повітряна тривога у ДНІПРІ або ОБЛАСТІ!**", parse_mode="Markdown")
                else:
                    await bot.send_message(CHAT_ID, "✅ **Відбій у місті Дніпро!**", parse_mode="Markdown")
                last_status = current_status
                print(f"📢 Статус изменился: {last_status}")
        except Exception as e:
            print(f"❌ Ошибка API или сети: {e}. Ждем 25 секунд...")
        await asyncio.sleep(25)

if __name__ == "__main__":
    asyncio.run(main())

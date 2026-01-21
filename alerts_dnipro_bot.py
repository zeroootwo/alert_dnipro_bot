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
    async def is_city_alert():
        active_alerts = await alerts_client.get_active_alerts()
        return any(
            alert.location_title == "Дніпро" and alert.location_type == "city"
            for alert in active_alerts
        )
    last_status = await is_city_alert()
    print(f"Бот запущен. Статус города Днепр: {'ТРЕВОГА' if last_status else 'ОТБОЙ'}")
    while True:
        try:
            current_status = await is_city_alert()
            if current_status != last_status:
                if current_status is True:
                    await bot.send_message(CHAT_ID, "🚨 **УВАГА! Повітряна тривога саме у ДНІПРІ!**", parse_mode="Markdown")
                else:
                    if last_status is True:
                        await bot.send_message(CHAT_ID, "✅ **Відбій у місті Дніпро!**", parse_mode="Markdown")
                last_status = current_status
                print(f"Статус города изменился: {last_status}")

        except Exception as e:
            print(f"Ошибка API или сети: {e}. Пробуем еще раз...")
        await asyncio.sleep(25)
if __name__ == "__main__":
    asyncio.run(main())
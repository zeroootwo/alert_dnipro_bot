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
    last_status=await alerts_client.get_air_raid_alert_status("9")
    print(f"Бот запущен. Текущий статус в Днепре: {last_status}")
    while True:
        try:
            current_status=await alerts_client.get_air_raid_alert_status("9")
            if current_status != last_status:
                if current_status is True:
                    await bot.send_message(CHAT_ID, "**УВАГА! Повітряна тривога у Дніпрі! Негайно пройти у найближче укриття!**")
                else:
                    await bot.send_message(CHAT_ID, "**Відбій повітряної тривоги!**")
                last_status=current_status
        except Exception as e:
            print(f"Проблема с API или сетью: {e}. Пробуем езе раз...")
        await asyncio.sleep(30)
if __name__ == "__main__":
    asyncio.run(main())
# -*- coding: utf-8 -*-
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")

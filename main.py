import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from bot.middlewares import AccessControlMiddleware
from bot.routers.callbacks import router as callbacks_router
from bot.routers.commands import router as commands_router
from bot.routers.dialog import router as dialog_router
from bot.routers.reporting import router as reporting_router
from config import settings
from db.connection import close_pool, open_pool

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await open_pool()

    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    session = AiohttpSession(proxy=proxy_url) if proxy_url else None
    bot = Bot(token=settings.telegram_bot_token, session=session)
    dp = Dispatcher()
    dp.update.outer_middleware(AccessControlMiddleware())
    dp.include_router(commands_router)
    dp.include_router(reporting_router)
    dp.include_router(callbacks_router)
    dp.include_router(dialog_router)

    try:
        await dp.start_polling(bot)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

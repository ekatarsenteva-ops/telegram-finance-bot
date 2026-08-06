import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import settings

logger = logging.getLogger(__name__)


class AccessControlMiddleware(BaseMiddleware):
    """Silently drops updates from users not in the allowed list."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and user.id not in settings.allowed_user_ids:
            logger.warning("Blocked update from unauthorized user_id=%s", user.id)
            return None
        return await handler(event, data)

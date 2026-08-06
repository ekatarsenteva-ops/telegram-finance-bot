import logging

logger = logging.getLogger(__name__)


async def sync_to_sheets() -> None:
    """Точка расширения: синхронизация с Google Sheets. Не реализована в этой версии."""
    logger.debug("sync_to_sheets: not implemented, skipping")

from psycopg_pool import AsyncConnectionPool

from config import settings

pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    open=False,
    check=AsyncConnectionPool.check_connection,
)


async def open_pool() -> None:
    await pool.open()


async def close_pool() -> None:
    await pool.close()

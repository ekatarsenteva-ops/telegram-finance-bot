import pathlib
import sys

import psycopg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from config import settings

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def main() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("Нет файлов миграций в migrations/")
        return

    with psycopg.connect(settings.database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            conn.commit()

        for path in migration_files:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s", (path.name,)
                )
                if cur.fetchone():
                    print(f"Пропущено (уже применено): {path.name}")
                    continue

                print(f"Применяю: {path.name}")
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                )
            conn.commit()

    print("Миграции применены.")


if __name__ == "__main__":
    main()

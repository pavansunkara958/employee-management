import os

from sqlalchemy.engine import URL


def database_url() -> URL:
    # URL.create escapes special characters — RDS-generated passwords contain them
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "app"),
        password=os.environ["DB_PASSWORD"],          # no default — must be provided
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "employees"),
    )
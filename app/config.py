import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

WA_TOKEN = os.getenv("WA_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")
PRECO_KZ = int(os.getenv("PRECO_KZ", "15000"))
IBAN = os.getenv("IBAN", "")
NIVEIS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Se houver DB_HOST usa TiDB (MySQL); senão usa SQLite local
USA_MYSQL = bool(os.getenv("DB_HOST"))
if USA_MYSQL:
    DATABASE_URL = URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "4000")),
        database=os.getenv("DB_NAME"),
    )
else:
    DATABASE_URL = "sqlite:///bot.db"
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # lê o .env só no seu computador; no Render usa a aba Environment
except ImportError:
    pass

WA_TOKEN = os.getenv("WA_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_ID", "")

import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
USA_MYSQL = os.getenv("USA_MYSQL", "false").lower() == "true"
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")  # ex.: 244923030010 (sem +)
PRECO_KZ = os.getenv("PRECO_KZ", "10000")
IBAN = os.getenv("IBAN", "")
NIVEIS = ["A1", "A2", "B1", "B2", "C1", "C2"]
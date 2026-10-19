import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # lê o .env só no seu computador; no Render usa a aba Environment
except ImportError:
    pass

WA_TOKEN = os.getenv("WA_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_ID", "")
import httpx
from .config import WA_TOKEN, WA_PHONE_ID

URL = f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}/messages"


def enviar(telefone: str, texto: str) -> None:
    if not WA_TOKEN or not WA_PHONE_ID:
        print("[erro WhatsApp] WA_TOKEN ou WA_PHONE_ID não configurados")
        return
    try:
        r = httpx.post(
            URL,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "text",
                "text": {"body": texto},
            },
            timeout=15,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[erro WhatsApp] {telefone}: {e}")
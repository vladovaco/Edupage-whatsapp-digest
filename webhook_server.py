"""Voliteľný režim „na požiadanie cez WhatsApp": webhook server pre WhatsApp Cloud API.

Keď napíšeš svojmu WhatsApp číslu (botovi) správu „digest", server stiahne
novinky z Edupage a odpovie ti hlasovkou.

Spustenie:
    python webhook_server.py

V Meta App nastav webhook URL na https://tvoja-domena/webhook
(verify token = WEBHOOK_VERIFY_TOKEN z .env). Server musí byť dostupný
z internetu – napr. cez reverzný proxy alebo tunel (cloudflared, ngrok).
"""

import logging
import threading

from flask import Flask, request

from edupage_digest.config import load_config
from edupage_digest.main import run_digest
from edupage_digest import whatsapp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("webhook")

app = Flask(__name__)
config = load_config()

TRIGGER_WORDS = {"digest", "sprava", "správy", "spravy", "novinky", "edupage"}


def _handle_request(sender: str) -> None:
    try:
        text = run_digest(config, to=sender)
        if not text:
            whatsapp.send_text_message(
                config, "Žiadne nové správy z Edupage. 🙂", to=sender
            )
    except Exception:
        logger.exception("Digest zlyhal.")
        try:
            whatsapp.send_text_message(
                config, "Prepáč, digest sa nepodarilo vytvoriť. Pozri logy servera.", to=sender
            )
        except Exception:
            logger.exception("Nepodarilo sa poslať ani chybovú správu.")


@app.get("/webhook")
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == config.webhook_verify_token
    ):
        return request.args.get("hub.challenge", ""), 200
    return "Forbidden", 403


@app.post("/webhook")
def receive():
    payload = request.get_json(silent=True) or {}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from", "")
                body = message.get("text", {}).get("body", "").strip().lower()
                # Reagujeme len na odosielateľa nastaveného v .env – nikto cudzí
                # nemôže spúšťať digest s údajmi tvojho dieťaťa.
                if sender != config.whatsapp_recipient.lstrip("+"):
                    logger.warning("Ignorujem správu od neznámeho čísla %s.", sender)
                    continue
                if body in TRIGGER_WORDS:
                    logger.info("Požiadavka na digest od %s.", sender)
                    threading.Thread(target=_handle_request, args=(sender,), daemon=True).start()
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.webhook_port)

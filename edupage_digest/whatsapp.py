"""Odosielanie správ cez WhatsApp Cloud API (Meta Graph API)."""

import logging
from pathlib import Path

import requests

from .config import Config

logger = logging.getLogger(__name__)

TIMEOUT = 60


class WhatsAppError(RuntimeError):
    pass


def _base_url(config: Config) -> str:
    return (
        f"https://graph.facebook.com/{config.whatsapp_api_version}"
        f"/{config.whatsapp_phone_number_id}"
    )


def _headers(config: Config) -> dict:
    return {"Authorization": f"Bearer {config.whatsapp_token}"}


def _check(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        raise WhatsAppError(
            f"WhatsApp API vrátilo {response.status_code}: {data.get('error', response.text)}"
        )
    return data


def upload_media(config: Config, file_path: Path, mime_type: str) -> str:
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{_base_url(config)}/media",
            headers=_headers(config),
            data={"messaging_product": "whatsapp", "type": mime_type},
            files={"file": (file_path.name, f, mime_type)},
            timeout=TIMEOUT,
        )
    media_id = _check(response).get("id")
    if not media_id:
        raise WhatsAppError("WhatsApp API nevrátilo id nahraného média.")
    logger.info("Audio nahrané, media_id=%s", media_id)
    return media_id


def send_voice_message(config: Config, media_id: str, to: str | None = None) -> None:
    response = requests.post(
        f"{_base_url(config)}/messages",
        headers=_headers(config),
        json={
            "messaging_product": "whatsapp",
            "to": to or config.whatsapp_recipient,
            "type": "audio",
            "audio": {"id": media_id},
        },
        timeout=TIMEOUT,
    )
    _check(response)
    logger.info("Hlasovka odoslaná na %s.", to or config.whatsapp_recipient)


def send_text_message(config: Config, text: str, to: str | None = None) -> None:
    response = requests.post(
        f"{_base_url(config)}/messages",
        headers=_headers(config),
        json={
            "messaging_product": "whatsapp",
            "to": to or config.whatsapp_recipient,
            "type": "text",
            "text": {"body": text[:4096]},
        },
        timeout=TIMEOUT,
    )
    _check(response)
    logger.info("Textová správa odoslaná na %s.", to or config.whatsapp_recipient)

"""Konfigurácia aplikácie – všetko sa číta z premenných prostredia (.env)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Chýba povinná premenná prostredia {name}. "
            f"Skopíruj .env.example do .env a doplň hodnoty."
        )
    return value


@dataclass
class Config:
    # Edupage
    edupage_username: str = field(default_factory=lambda: _require("EDUPAGE_USERNAME"))
    edupage_password: str = field(default_factory=lambda: _require("EDUPAGE_PASSWORD"))
    edupage_subdomain: str = field(default_factory=lambda: _require("EDUPAGE_SUBDOMAIN"))
    # person_id dieťaťa – potrebné len ak má rodičovské konto viac detí
    edupage_child_id: int | None = field(
        default_factory=lambda: int(os.environ["EDUPAGE_CHILD_ID"])
        if os.environ.get("EDUPAGE_CHILD_ID", "").strip()
        else None
    )

    # WhatsApp Cloud API (Meta)
    whatsapp_token: str = field(default_factory=lambda: _require("WHATSAPP_TOKEN"))
    whatsapp_phone_number_id: str = field(
        default_factory=lambda: _require("WHATSAPP_PHONE_NUMBER_ID")
    )
    whatsapp_recipient: str = field(default_factory=lambda: _require("WHATSAPP_RECIPIENT"))
    whatsapp_api_version: str = field(
        default_factory=lambda: os.environ.get("WHATSAPP_API_VERSION", "v21.0")
    )
    # Poslať okrem hlasovky aj textovú verziu digestu
    send_text_too: bool = field(
        default_factory=lambda: os.environ.get("SEND_TEXT_TOO", "true").lower()
        in ("1", "true", "yes", "ano")
    )

    # Koľko dní dozadu sa pozerať, keď aplikácia beží prvýkrát (bez uloženého stavu)
    digest_days: int = field(default_factory=lambda: int(os.environ.get("DIGEST_DAYS", "2")))

    # Voliteľné: Claude API kľúč pre pekné hovorené zhrnutie.
    # Bez neho sa použije jednoduché šablónové zhrnutie.
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "").strip() or None
    )

    # Webhook server (režim „na požiadanie cez WhatsApp správu“)
    webhook_verify_token: str = field(
        default_factory=lambda: os.environ.get("WEBHOOK_VERIFY_TOKEN", "edupage-digest")
    )
    # Render/Railway/Fly nastavujú port cez PORT, lokálne sa dá použiť WEBHOOK_PORT
    webhook_port: int = field(
        default_factory=lambda: int(
            os.environ.get("PORT") or os.environ.get("WEBHOOK_PORT", "8000")
        )
    )

    state_file: Path = field(default_factory=lambda: PROJECT_ROOT / ".state.json")
    out_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "out")


def load_config() -> Config:
    return Config()

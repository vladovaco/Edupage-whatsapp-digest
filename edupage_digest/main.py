"""Hlavný beh: Edupage → digest → hlasovka → WhatsApp."""

import argparse
import json
import logging
from datetime import datetime, timedelta

import requests

from . import digest as digest_module
from . import edupage_client, tts, whatsapp
from .config import Config, load_config

logger = logging.getLogger(__name__)

# Návratový kód pri sieťovej chybe (Edupage nedostupné). GitHub Actions workflow
# podľa neho vie, že má beh zopakovať na inom runneri.
NETWORK_ERROR_EXIT_CODE = 3


def _load_since(config: Config) -> datetime:
    if config.state_file.exists():
        try:
            data = json.loads(config.state_file.read_text())
            return datetime.fromisoformat(data["last_run"])
        except (ValueError, KeyError):
            logger.warning("Poškodený stavový súbor %s, ignorujem ho.", config.state_file)
    return datetime.now() - timedelta(days=config.digest_days)


def _save_since(config: Config, when: datetime) -> None:
    config.state_file.write_text(json.dumps({"last_run": when.isoformat()}))


def run_digest(
    config: Config,
    to: str | None = None,
    dry_run: bool = False,
    ignore_state: bool = False,
) -> str:
    """Stiahne novinky, zostaví digest a pošle hlasovku. Vráti text digestu."""
    now = datetime.now()
    since = (
        now - timedelta(days=config.digest_days) if ignore_state else _load_since(config)
    )
    logger.info("Hľadám novinky od %s.", since.strftime("%d.%m.%Y %H:%M"))

    edupage = edupage_client.login(config)
    events = edupage_client.fetch_events(edupage, since)

    text = digest_module.build_digest(events, config, now)
    if not text:
        logger.info("Žiadne nové správy – nič neposielam.")
        if not dry_run and not ignore_state:
            _save_since(config, now)
        return ""

    logger.info("Digest:\n%s", text)
    if dry_run:
        return text

    audio_path, mime_type = tts.text_to_voice(text, config)
    media_id = whatsapp.upload_media(config, audio_path, mime_type)
    whatsapp.send_voice_message(config, media_id, to=to)
    if config.send_text_too:
        whatsapp.send_text_message(config, "📚 Edupage digest:\n\n" + text, to=to)

    if not ignore_state:
        _save_since(config, now)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stiahne najnovšie správy z Edupage a pošle ich ako hlasovku na WhatsApp."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Len vypíše digest, nič negeneruje ani neposiela.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Ignoruje uložený stav a zoberie novinky za posledných N dní.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config()
    ignore_state = args.days is not None
    if ignore_state:
        config.digest_days = args.days

    try:
        text = run_digest(config, dry_run=args.dry_run, ignore_state=ignore_state)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error("Sieťová chyba: %s", e)
        raise SystemExit(NETWORK_ERROR_EXIT_CODE)
    if text:
        print("\n" + text)
    else:
        print("Žiadne nové správy z Edupage.")


if __name__ == "__main__":
    main()

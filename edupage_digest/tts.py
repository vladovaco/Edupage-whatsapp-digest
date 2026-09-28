"""Prevod textu na hlasovku: ElevenLabs (fallback gTTS) + ffmpeg konverzia do OGG/Opus.

WhatsApp zobrazí správu ako klasickú hlasovku len vtedy, keď je audio
OGG s kodekom Opus a jednou (mono) stopou. Ak ffmpeg nie je k dispozícii,
pošle sa MP3 – prehrať sa dá tiež, len sa nezobrazí ako hlasovka.
"""

import logging
import shutil
import subprocess
from pathlib import Path

import requests

from .config import Config

logger = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _elevenlabs_tts(text: str, config: Config, mp3_path: Path) -> bool:
    """Syntéza cez ElevenLabs API. Vráti False, ak zlyhá (použije sa gTTS)."""
    try:
        response = requests.post(
            ELEVENLABS_URL.format(voice_id=config.elevenlabs_voice_id),
            params={"output_format": "mp3_44100_128"},
            headers={
                "xi-api-key": config.elevenlabs_api_key,
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": config.elevenlabs_model,
            },
            timeout=120,
        )
    except requests.RequestException as e:
        logger.warning("ElevenLabs: chyba pripojenia (%s), používam gTTS.", e)
        return False

    if response.status_code != 200:
        logger.warning(
            "ElevenLabs vrátil chybu %s: %s – používam gTTS.",
            response.status_code,
            response.text[:300],
        )
        return False

    mp3_path.write_bytes(response.content)
    logger.info("TTS (ElevenLabs) hotové: %s", mp3_path)
    return True


def _gtts_tts(text: str, mp3_path: Path) -> None:
    from gtts import gTTS

    gTTS(text=text, lang="sk").save(str(mp3_path))
    logger.info("TTS (gTTS) hotové: %s", mp3_path)


def text_to_voice(text: str, config: Config) -> tuple[Path, str]:
    """Vygeneruje audio súbor z textu. Vráti (cesta, mime_type)."""
    out_dir = config.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / "digest.mp3"

    if not (config.elevenlabs_api_key and _elevenlabs_tts(text, config, mp3_path)):
        if not config.elevenlabs_api_key:
            logger.warning("ELEVENLABS_API_KEY nie je nastavený, používam gTTS.")
        _gtts_tts(text, mp3_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg nie je nainštalovaný – posielam MP3 namiesto OGG/Opus hlasovky.")
        return mp3_path, "audio/mpeg"

    ogg_path = out_dir / "digest.ogg"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", str(mp3_path),
            "-c:a", "libopus",
            "-b:a", "32k",
            "-ar", "48000",
            "-ac", "1",
            str(ogg_path),
        ],
        check=True,
        capture_output=True,
    )
    logger.info("Konverzia do OGG/Opus hotová: %s", ogg_path)
    return ogg_path, "audio/ogg"

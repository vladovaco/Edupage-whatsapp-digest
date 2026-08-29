"""Prevod textu na hlasovku: gTTS (slovenčina) + ffmpeg konverzia do OGG/Opus.

WhatsApp zobrazí správu ako klasickú hlasovku len vtedy, keď je audio
OGG s kodekom Opus a jednou (mono) stopou. Ak ffmpeg nie je k dispozícii,
pošle sa MP3 – prehrať sa dá tiež, len sa nezobrazí ako hlasovka.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS

logger = logging.getLogger(__name__)


def text_to_voice(text: str, out_dir: Path) -> tuple[Path, str]:
    """Vygeneruje audio súbor z textu. Vráti (cesta, mime_type)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / "digest.mp3"

    tts = gTTS(text=text, lang="sk")
    tts.save(str(mp3_path))
    logger.info("TTS hotové: %s", mp3_path)

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

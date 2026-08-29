"""Zostavenie textového digestu z udalostí – hovorená slovenčina pre hlasovku."""

import html
import logging
import re
from datetime import datetime

from edupage_api.people import EduAccount
from edupage_api.timeline import EventType, TimelineEvent

from .config import Config

logger = logging.getLogger(__name__)

EVENT_TYPE_LABELS = {
    EventType.MESSAGE: "Správa",
    EventType.NEWS: "Oznam",
    EventType.HOMEWORK: "Domáca úloha",
    EventType.BIG_EXAM: "Veľká písomka",
    EventType.ORAL_EXAM: "Ústna odpoveď",
    EventType.SHORT_EXAM: "Krátka písomka",
    EventType.PAPER: "Písomka",
    EventType.PROJECT_EXAM: "Projekt",
    EventType.TESTING: "Testovanie",
    EventType.GRADE: "Nová známka",
    EventType.SUBSTITUTION: "Suplovanie",
    EventType.TT_CANCEL: "Odpadnutá hodina",
    EventType.FREE_DAY: "Voľný deň",
    EventType.HOLIDAY: "Prázdniny",
    EventType.SHORT_HOLIDAY: "Krátke prázdniny",
    EventType.EVENT: "Udalosť",
    EventType.SCHOOL_EVENT: "Školská akcia",
    EventType.SCHOOL_TRIP: "Školský výlet",
    EventType.EXCURSION: "Exkurzia",
    EventType.PARENTS_EVENING: "Rodičovské združenie",
    EventType.CLASS_TEACHER_EVENT: "Triednická akcia",
    EventType.STUDENT_ABSENT: "Absencia",
    EventType.EXCUSED_LESSON: "Ospravedlnenka",
}

DAYS_SK = ["pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota", "nedeľa"]


def _person_name(person: EduAccount | str | None) -> str:
    if person is None:
        return ""
    if isinstance(person, EduAccount):
        return person.name or ""
    return str(person)


def _clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def events_to_plain_lines(events: list[TimelineEvent]) -> list[str]:
    lines = []
    for event in events:
        label = EVENT_TYPE_LABELS.get(event.event_type, "Udalosť")
        day = DAYS_SK[event.timestamp.weekday()]
        when = f"{day} {event.timestamp.day}.{event.timestamp.month}."
        author = _person_name(event.author)
        text = _clean_text(event.text)
        if not text and not author:
            continue
        who = f" od {author}" if author else ""
        lines.append(f"{label} ({when}){who}: {text}")
    return lines


def build_fallback_digest(events: list[TimelineEvent], now: datetime) -> str:
    """Jednoduchý šablónový digest – použije sa, keď nie je k dispozícii Claude API."""
    lines = events_to_plain_lines(events)
    if not lines:
        return ""
    intro = (
        f"Ahoj, tu je súhrn z Edupage. "
        f"Máš {len(lines)} {'novú položku' if len(lines) == 1 else 'nové položky' if len(lines) < 5 else 'nových položiek'}. "
    )
    return intro + " ".join(f"{i}. {line}" for i, line in enumerate(lines, start=1))


SUMMARY_SYSTEM_PROMPT = """Si asistent, ktorý pre rodiča pripravuje hovorený súhrn noviniek zo školského systému Edupage o jeho dieťati.

Pravidlá:
- Píš po slovensky, prirodzenou hovorenou rečou – text sa prevedie na hlasovú správu.
- Žiadny markdown, odrážky, emoji ani nadpisy. Len súvislé vety.
- Začni krátkym pozdravom a jednou vetou zhrň, čo je nové.
- Potom prejdi jednotlivé novinky: kto ich poslal, čoho sa týkajú a kedy sa čo koná. Dôležité termíny (písomky, úlohy, akcie, suplovanie) povedz vždy s dňom.
- Buď stručný: maximálne zhruba 200 slov, nepodstatné detaily vynechaj.
- Nič si nevymýšľaj – používaj iba informácie zo vstupu.
- Dátumy a čísla píš slovom alebo prirodzene (napríklad „v stredu tretieho septembra"), aby sa dobre čítali nahlas."""


def build_claude_digest(events: list[TimelineEvent], config: Config) -> str | None:
    """Zhrnutie cez Claude API. Vráti None, ak sa zhrnutie nepodarí (použije sa fallback)."""
    lines = events_to_plain_lines(events)
    if not lines:
        return ""

    try:
        import anthropic
    except ImportError:
        logger.warning("Balík anthropic nie je nainštalovaný, používam šablónový digest.")
        return None

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=4096,  # digest je zámerne krátky (~200 slov)
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Nové položky z Edupage:\n" + "\n".join(lines),
                }
            ],
        )
    except anthropic.RateLimitError:
        logger.warning("Claude API: rate limit, používam šablónový digest.")
        return None
    except anthropic.APIStatusError as e:
        logger.warning("Claude API vrátilo chybu %s, používam šablónový digest.", e.status_code)
        return None
    except anthropic.APIConnectionError:
        logger.warning("Claude API: chyba pripojenia, používam šablónový digest.")
        return None

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None


def build_digest(events: list[TimelineEvent], config: Config, now: datetime) -> str:
    """Vráti finálny text digestu; prázdny reťazec znamená „nič nové"."""
    if not events:
        return ""
    if config.anthropic_api_key:
        digest = build_claude_digest(events, config)
        if digest:
            return digest
    return build_fallback_digest(events, now)

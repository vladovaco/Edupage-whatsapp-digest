"""Prihlásenie do Edupage a stiahnutie noviniek z nástenky (timeline)."""

import logging
import sys
import time
from datetime import datetime, timedelta

from edupage_api import Edupage
from edupage_api.timeline import EventType, TimelineEvent, TimelineEvents

from .config import Config

logger = logging.getLogger(__name__)

# Oprava chyby v edupage-api 0.12.5: niektoré školy vracajú "timelineUserProps"
# ako prázdny zoznam namiesto slovníka a parsovanie spadne na AttributeError.
_original_parse_items = TimelineEvents._TimelineEvents__parse_items


def _parse_items_tolerant(self, items, user_props):
    if not isinstance(user_props, dict):
        user_props = {}
    return _original_parse_items(self, items, user_props)


TimelineEvents._TimelineEvents__parse_items = _parse_items_tolerant

# Typy udalostí, ktoré rodiča reálne zaujímajú. Ostatné (pípnutie pri príchode,
# výdaj stravy, interné pomocné eventy...) sa do digestu nedostanú.
RELEVANT_EVENT_TYPES = {
    EventType.MESSAGE,
    EventType.NEWS,
    EventType.HOMEWORK,
    EventType.BIG_EXAM,
    EventType.ORAL_EXAM,
    EventType.SHORT_EXAM,
    EventType.PAPER,
    EventType.PROJECT_EXAM,
    EventType.TESTING,
    EventType.GRADE,
    EventType.SUBSTITUTION,
    EventType.TT_CANCEL,
    EventType.FREE_DAY,
    EventType.HOLIDAY,
    EventType.SHORT_HOLIDAY,
    EventType.EVENT,
    EventType.SCHOOL_EVENT,
    EventType.SCHOOL_TRIP,
    EventType.EXCURSION,
    EventType.PARENTS_EVENING,
    EventType.CLASS_TEACHER_EVENT,
    EventType.STUDENT_ABSENT,
    EventType.EXCUSED_LESSON,
}


def login(config: Config) -> Edupage:
    edupage = Edupage()
    second_factor = edupage.login(
        config.edupage_username, config.edupage_password, config.edupage_subdomain
    )

    if second_factor is not None:
        logger.info("Edupage vyžaduje dvojfaktorové overenie.")
        # Najprv chvíľu čakáme, či prihlásenie nepotvrdí mobilná aplikácia.
        for _ in range(6):
            if second_factor.is_confirmed():
                second_factor.finish()
                break
            time.sleep(5)
        else:
            if sys.stdin.isatty():
                code = input("Zadaj 2FA kód z e-mailu alebo mobilnej aplikácie: ").strip()
                second_factor.finish_with_code(code)
            else:
                raise SystemExit(
                    "Edupage vyžaduje 2FA a beh nie je interaktívny. Potvrď prihlásenie "
                    "v mobilnej aplikácii do 30 sekúnd od štartu, alebo spusti apku v termináli."
                )

    if config.edupage_child_id is not None:
        edupage.switch_to_child(config.edupage_child_id)
        logger.info("Prepnuté na dieťa s person_id=%s", config.edupage_child_id)

    return edupage


def fetch_events(edupage: Edupage, since: datetime) -> list[TimelineEvent]:
    """Vráti relevantné udalosti novšie ako `since`, od najstaršej po najnovšiu."""
    events = edupage.get_notification_history(date_from=(since - timedelta(days=1)).date())

    fresh = [
        e
        for e in events
        if e.event_type in RELEVANT_EVENT_TYPES and e.timestamp and e.timestamp > since
    ]
    fresh.sort(key=lambda e: e.timestamp)
    logger.info("Stiahnutých %d udalostí, po filtrovaní %d nových.", len(events), len(fresh))
    return fresh

"""Filtres Jinja : les dates sont stockées en UTC et affichées en heure de Paris."""

from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MOIS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def paris_datetime(value: str | None, fmt: str = "%d / %m / %Y à %H:%M") -> str:
    """'2026-11-18T09:30:00.000Z' -> '18 / 11 / 2026 à 10:30' (heure de Paris)."""
    if not value:
        return ""
    return datetime.fromisoformat(value).astimezone(PARIS).strftime(fmt)


def today_paris(now: datetime | None = None) -> str:
    """Date du jour en toutes lettres, sans dépendre de la locale : 'mercredi 18 novembre 2026'."""
    now = (now or datetime.now(PARIS)).astimezone(PARIS)
    return f"{JOURS[now.weekday()]} {now.day} {MOIS[now.month - 1]} {now.year}"


def init_app(app) -> None:
    app.add_template_filter(paris_datetime, "paris")
    app.add_template_global(today_paris, "today_paris")

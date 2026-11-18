"""Filtres Jinja : les dates sont stockées en UTC et affichées en heure de Paris."""

from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


def paris_datetime(value: str | None, fmt: str = "%d/%m/%Y à %H:%M") -> str:
    """'2026-11-18T09:30:00.000Z' -> '18/11/2026 à 10:30' (heure de Paris)."""
    if not value:
        return ""
    return datetime.fromisoformat(value).astimezone(PARIS).strftime(fmt)


def init_app(app) -> None:
    app.add_template_filter(paris_datetime, "paris")

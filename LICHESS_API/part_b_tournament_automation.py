"""
part_b_tournament_automation.py

Lichess API - Tournament Automation
====================================
Automates the weekly creation of Lichess Arena tournaments using the
authenticated Lichess API. Supports a DRY_RUN mode that simulates tournament
creation without making any POST requests.

Usage:
    python part_b_tournament_automation.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from dotenv import load_dotenv

LICHESS_API_BASE = "https://lichess.org"
CREATE_ARENA_ENDPOINT = f"{LICHESS_API_BASE}/api/tournament"

# Lichess silently returns a fake 404 to requests carrying the default
# python-requests/curl User-Agent (anti-bot heuristic). A descriptive UA, as
# recommended by the Lichess API docs, avoids that and surfaces the real
# response.
USER_AGENT = "lichess-data-analysis-tool/1.0 (+part_b_tournament_automation.py)"

# Set to False to actually POST tournaments to the Lichess API.
DRY_RUN = True

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("lichess.part_b")


def next_weekday_datetime(weekday: int, hour: int, minute: int = 0) -> datetime:
    """Return the next UTC datetime matching `weekday` (0=Mon..6=Sun) and time.

    If today already matches the weekday but the time has passed, rolls over
    to the following week.
    """
    now = datetime.now(timezone.utc)
    days_ahead = (weekday - now.weekday()) % 7
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def build_schedule() -> list[dict[str, Any]]:
    """Weekly tournament calendar. Edit this list to define your own events.

    All times are UTC. `start_time` can also be a hardcoded `datetime` if you
    need a one-off event instead of a recurring weekly slot.
    """
    return [
        {
            "name": "Monday Blitz Battle",
            "start_time": next_weekday_datetime(weekday=0, hour=18, minute=0),
            "variant": "standard",
            "duration_minutes": 60,
            "clock_time": 3,
            "clock_increment": 2,
            "rated": True,
            "description": "Weekly blitz arena open to all ratings.",
        },
        {
            "name": "Wednesday Rapid Rumble",
            "start_time": next_weekday_datetime(weekday=2, hour=19, minute=30),
            "variant": "standard",
            "duration_minutes": 90,
            "clock_time": 10,
            "clock_increment": 5,
            "rated": True,
            "description": "Weekly rapid arena, casual and competitive players welcome.",
        },
        {
            "name": "Friday Bullet Frenzy",
            "start_time": next_weekday_datetime(weekday=4, hour=20, minute=0),
            "variant": "standard",
            "duration_minutes": 45,
            "clock_time": 1,
            "clock_increment": 0,
            "rated": True,
            "description": "Fast-paced bullet arena to close the week.",
        },
        {
            "name": "Sunday Classical Clash",
            "start_time": next_weekday_datetime(weekday=6, hour=15, minute=0),
            "variant": "standard",
            "duration_minutes": 120,
            "clock_time": 30,
            "clock_increment": 20,
            "rated": True,
            "description": "Slow-paced classical arena for deep thinkers.",
        },
    ]


def load_token() -> Optional[str]:
    """Load the Lichess API token from the .env file, if present."""
    load_dotenv()
    token = os.getenv("LICHESS_API_TOKEN")
    if not token:
        logger.warning("LICHESS_API_TOKEN not set. Live tournament creation will fail without it.")
    return token


def is_past(tournament: dict[str, Any]) -> bool:
    """True if the tournament's scheduled start time is already behind us."""
    return tournament["start_time"] <= datetime.now(timezone.utc)


def build_payload(tournament: dict[str, Any]) -> dict[str, Any]:
    """Translate an internal schedule entry into the Lichess Arena API payload."""
    start_ms = int(tournament["start_time"].timestamp() * 1000)
    return {
        "name": tournament["name"],
        "clockTime": tournament["clock_time"],
        "clockIncrement": tournament["clock_increment"],
        "minutes": tournament["duration_minutes"],
        "startDate": start_ms,
        "variant": tournament["variant"],
        "rated": str(tournament["rated"]).lower(),
        "description": tournament.get("description", ""),
    }


def create_tournament(session: requests.Session, tournament: dict[str, Any], dry_run: bool) -> None:
    """Create a single Arena tournament, or simulate it when `dry_run` is True.

    Handles HTTP 429 with exponential backoff. Any failure is logged and
    swallowed so the caller can keep processing the rest of the schedule.
    """
    payload = build_payload(tournament)

    if dry_run:
        logger.info("[DRY RUN] Would create tournament: %s", payload)
        return

    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.post(CREATE_ARENA_ENDPOINT, data=payload, timeout=30)

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", backoff))
                logger.warning(
                    "Rate limited creating '%s'. Retrying in %.1fs (attempt %d/%d).",
                    tournament["name"], retry_after, attempt, MAX_RETRIES,
                )
                time.sleep(retry_after)
                backoff *= 2
                continue

            response.raise_for_status()
            data = response.json()
            logger.info(
                "Created tournament '%s' -> https://lichess.org/tournament/%s",
                tournament["name"], data.get("id", "?"),
            )
            return

        except requests.exceptions.RequestException as exc:
            logger.error(
                "Failed to create tournament '%s' (attempt %d/%d): %s",
                tournament["name"], attempt, MAX_RETRIES, exc,
            )
            time.sleep(backoff)
            backoff *= 2

    logger.error("Giving up on tournament '%s' after %d attempts.", tournament["name"], MAX_RETRIES)


def run(dry_run: bool = DRY_RUN) -> None:
    """Process the weekly schedule: skip past events, create the rest."""
    token = load_token()
    schedule = build_schedule()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})

    logger.info("Processing %d scheduled tournaments (DRY_RUN=%s)...", len(schedule), dry_run)

    for tournament in schedule:
        if is_past(tournament):
            logger.info(
                "Skipping '%s': scheduled start %s has already passed.",
                tournament["name"], tournament["start_time"].isoformat(),
            )
            continue

        try:
            create_tournament(session, tournament, dry_run)
        except Exception as exc:
            logger.error("Unexpected error processing '%s': %s", tournament["name"], exc)
            continue


if __name__ == "__main__":
    run()

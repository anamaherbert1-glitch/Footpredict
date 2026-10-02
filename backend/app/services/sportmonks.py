from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.db import get_connection

BASE_URL = "https://api.sportmonks.com/v3/football"


class SportMonksError(RuntimeError):
    pass


def _token() -> str:
    token = os.getenv("SPORTMONKS_API_TOKEN")
    if not token:
        raise SportMonksError("SPORTMONKS_API_TOKEN is not configured")
    return token


def fetch(path: str, params: dict | None = None) -> dict:
    query = {"api_token": _token(), **(params or {})}
    url = f"{BASE_URL}/{path.lstrip('/')}?{urlencode(query)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise SportMonksError(f"SportMonks request failed: {exc}") from exc

    if not isinstance(payload, dict) or "data" not in payload:
        raise SportMonksError("Unexpected SportMonks response")
    return payload


def _participants(fixture: dict) -> tuple[dict | None, dict | None]:
    home = away = None
    for participant in fixture.get("participants", []) or []:
        location = participant.get("meta", {}).get("location")
        if location == "home":
            home = participant
        elif location == "away":
            away = participant
    return home, away


def _score(fixture: dict, location: str) -> int | None:
    for score in fixture.get("scores", []) or []:
        if score.get("description") in {"CURRENT", "FT", "2ND_HALF"} and score.get("participant") == location:
            value = score.get("goals")
            if value is not None:
                return int(value)
    return None


def _upsert_league(cur, league: dict, season: str | None) -> str:
    external_id = str(league["id"])
    name = league.get("name") or f"League {external_id}"
    country = (league.get("country") or {}).get("name") if isinstance(league.get("country"), dict) else None
    cur.execute(
        """
        INSERT INTO leagues (name, country, season, external_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name, season) DO UPDATE
        SET country = EXCLUDED.country, external_id = EXCLUDED.external_id
        RETURNING id
        """,
        (name, country, season, external_id),
    )
    return str(cur.fetchone()[0])


def _upsert_team(cur, participant: dict, league_id: str | None) -> str:
    external_id = str(participant["id"])
    name = participant.get("name") or f"Team {external_id}"
    short_name = participant.get("short_code") or participant.get("short_name")
    country = None
    country_data = participant.get("country")
    if isinstance(country_data, dict):
        country = country_data.get("name")

    cur.execute(
        """
        INSERT INTO teams (name, short_name, country, league_id, external_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (external_id) DO UPDATE SET
            name = EXCLUDED.name,
            short_name = EXCLUDED.short_name,
            country = EXCLUDED.country,
            league_id = EXCLUDED.league_id
        """,
        (name, short_name, country, league_id, external_id),
    )

    cur.execute("SELECT id FROM teams WHERE external_id = %s LIMIT 1", (external_id,))
    row = cur.fetchone()
    if not row:
        raise SportMonksError(f"Unable to store team {external_id}")
    return str(row[0])


def ingest_fixtures(
    *,
    start_date: str,
    end_date: str,
    league_id: int | None = None,
    season: str | None = None,
) -> dict:
    path = f"fixtures/between/{start_date}/{end_date}"
    params = {
        "include": "participants;scores;league;state",
        "per_page": 100,
    }
    if league_id is not None:
        params["filters"] = f"fixtureLeagues:{league_id}"

    payload = fetch(path, params)
    fixtures = payload.get("data", []) or []
    inserted = updated = skipped = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for fixture in fixtures:
                home, away = _participants(fixture)
                if not home or not away:
                    skipped += 1
                    continue

                league = fixture.get("league") or {}
                league_external = league.get("id")
                internal_league = None
                if league_external:
                    internal_league = _upsert_league(cur, league, season)

                home_id = _upsert_team(cur, home, internal_league)
                away_id = _upsert_team(cur, away, internal_league)

                kickoff = fixture.get("starting_at")
                if not kickoff:
                    skipped += 1
                    continue

                state = fixture.get("state") or {}
                status = "finished" if state.get("short_name") in {"FT", "AET", "PEN"} else "scheduled"
                home_goals = _score(fixture, "home")
                away_goals = _score(fixture, "away")
                external_id = str(fixture["id"])

                cur.execute(
                    """
                    INSERT INTO matches (
                        league_id, home_team_id, away_team_id, kickoff_at,
                        status, home_goals, away_goals, external_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (external_id) DO UPDATE SET
                        league_id = EXCLUDED.league_id,
                        home_team_id = EXCLUDED.home_team_id,
                        away_team_id = EXCLUDED.away_team_id,
                        kickoff_at = EXCLUDED.kickoff_at,
                        status = EXCLUDED.status,
                        home_goals = EXCLUDED.home_goals,
                        away_goals = EXCLUDED.away_goals
                    """,
                    (
                        internal_league,
                        home_id,
                        away_id,
                        kickoff,
                        status,
                        home_goals,
                        away_goals,
                        external_id,
                    ),
                )
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    updated += 1

    return {
        "provider": "sportmonks",
        "fixtures_seen": len(fixtures),
        "inserted_or_created": inserted,
        "updated": updated,
        "skipped": skipped,
        "start_date": start_date,
        "end_date": end_date,
    }

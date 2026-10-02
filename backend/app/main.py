from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.db import get_connection
from app.models.poisson import TeamStrength, predict_match

app = FastAPI(title="FootPredict API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    home_team_id: str
    away_team_id: str
    league_id: str | None = None
    home_attack: float = Field(gt=0)
    home_defense: float = Field(gt=0)
    away_attack: float = Field(gt=0)
    away_defense: float = Field(gt=0)
    home_advantage: float = Field(default=1.0, gt=0)
    model_version_id: str | None = None


@app.get("/health")
def health():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return {"status": "ok", "database": "connected"}


@app.get("/matches")
def list_matches(limit: int = 20):
    limit = min(max(limit, 1), 100)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, league_id, home_team_id, away_team_id,
                       kickoff_at, status, home_goals, away_goals
                FROM matches
                ORDER BY kickoff_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            columns = [d.name for d in cur.description]
    return [dict(zip(columns, row)) for row in rows]


@app.post("/predict")
def create_prediction(payload: PredictionRequest):
    prediction = predict_match(
        home_team=payload.home_team_id,
        away_team=payload.away_team_id,
        home_strength=TeamStrength(
            attack=payload.home_attack,
            defense=payload.home_defense,
            home_advantage=payload.home_advantage,
        ),
        away_strength=TeamStrength(
            attack=payload.away_attack,
            defense=payload.away_defense,
        ),
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (
                    match_id, model_version_id,
                    probability_home, probability_draw, probability_away,
                    probability_over_25, probability_under_25,
                    probability_btts_yes, probability_btts_no,
                    lambda_home, lambda_away,
                    predicted_home_goals, predicted_away_goals,
                    most_likely_score
                )
                SELECT
                    m.id, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s
                FROM matches m
                WHERE m.home_team_id = %s
                  AND m.away_team_id = %s
                  AND (%s IS NULL OR m.league_id = %s)
                ORDER BY m.kickoff_at DESC
                LIMIT 1
                RETURNING id, match_id, created_at
                """,
                (
                    payload.model_version_id,
                    prediction.prob_home,
                    prediction.prob_draw,
                    prediction.prob_away,
                    prediction.prob_over_25,
                    prediction.prob_under_25,
                    prediction.prob_btts_yes,
                    prediction.prob_btts_no,
                    prediction.lambda_home,
                    prediction.lambda_away,
                    prediction.lambda_home,
                    prediction.lambda_away,
                    f"{prediction.most_likely_score[0]}-{prediction.most_likely_score[1]}",
                    payload.home_team_id,
                    payload.away_team_id,
                    payload.league_id,
                    payload.league_id,
                ),
            )
            saved = cur.fetchone()

    if not saved:
        raise HTTPException(
            status_code=404,
            detail="No matching fixture found for the supplied teams/league",
        )

    return {
        "prediction_id": str(saved[0]),
        "match_id": str(saved[1]),
        "created_at": saved[2],
        "prediction": {
            "lambda_home": prediction.lambda_home,
            "lambda_away": prediction.lambda_away,
            "prob_home": prediction.prob_home,
            "prob_draw": prediction.prob_draw,
            "prob_away": prediction.prob_away,
            "prob_over_25": prediction.prob_over_25,
            "prob_under_25": prediction.prob_under_25,
            "prob_btts_yes": prediction.prob_btts_yes,
            "prob_btts_no": prediction.prob_btts_no,
            "most_likely_score": prediction.most_likely_score,
        },
    }


@app.get("/teams/search")
def search_teams(q: str, limit: int = 10):
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query must contain at least 2 characters")
    limit = min(max(limit, 1), 25)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, short_name, country, league_id,
                       elo_rating, attack_rating, defense_rating, home_advantage
                FROM teams
                WHERE name ILIKE %s OR short_name ILIKE %s
                ORDER BY name
                LIMIT %s
                """,
                (f"%{q}%", f"%{q}%", limit),
            )
            rows = cur.fetchall()
            columns = [d.name for d in cur.description]
    return [dict(zip(columns, row)) for row in rows]


@app.get("/matches/upcoming")
def upcoming_matches(limit: int = 20):
    limit = min(max(limit, 1), 100)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.kickoff_at, m.status,
                       m.home_team_id, ht.name AS home_team,
                       m.away_team_id, at.name AS away_team,
                       m.league_id, l.name AS league
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                LEFT JOIN leagues l ON l.id = m.league_id
                WHERE m.kickoff_at >= now()
                  AND m.status IN ('scheduled', 'upcoming')
                ORDER BY m.kickoff_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            columns = [d.name for d in cur.description]
    return [dict(zip(columns, row)) for row in rows]

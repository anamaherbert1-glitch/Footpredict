from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.db import get_connection
from app.models.poisson import predict_match

app = FastAPI(title="FootPredict API", version="0.1.0")


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
    result = predict_match(
        home_attack=payload.home_attack,
        home_defense=payload.home_defense,
        away_attack=payload.away_attack,
        away_defense=payload.away_defense,
        home_advantage=payload.home_advantage,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (
                    match_id,
                    model_version_id,
                    probability_home,
                    probability_draw,
                    probability_away,
                    probability_over_25,
                    probability_under_25,
                    probability_btts_yes,
                    probability_btts_no,
                    lambda_home,
                    lambda_away,
                    predicted_home_goals,
                    predicted_away_goals,
                    most_likely_score
                )
                SELECT
                    m.id,
                    %s,
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
                    result["home_win_probability"],
                    result["draw_probability"],
                    result["away_win_probability"],
                    result["over_2_5_probability"],
                    result["under_2_5_probability"],
                    result["btts_yes_probability"],
                    result["btts_no_probability"],
                    result["lambda_home"],
                    result["lambda_away"],
                    result["expected_home_goals"],
                    result["expected_away_goals"],
                    result["most_likely_score"],
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
        "prediction": result,
    }

"""
Modèle de probabilités football - Approche Poisson
=================================================

Principe :
- On estime la force offensive et défensive de chaque équipe
- On calcule le nombre de buts attendus (λ) pour chaque équipe
- On utilise la loi de Poisson pour obtenir la distribution des scores
- On agrège pour obtenir les probabilités 1X2, Over/Under, BTTS, etc.
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class TeamStrength:
    attack: float
    defense: float
    home_advantage: float = 1.0


@dataclass
class MatchPrediction:
    home_team: str
    away_team: str
    lambda_home: float
    lambda_away: float
    prob_home: float
    prob_draw: float
    prob_away: float
    most_likely_score: Tuple[int, int]
    prob_over_25: float
    prob_under_25: float
    prob_btts_yes: float
    prob_btts_no: float
    score_matrix: Dict[Tuple[int, int], float]


def poisson_probability(lmbda: float, k: int) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)


def calculate_expected_goals(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_home_goals: float = 1.45,
    league_avg_away_goals: float = 1.15
) -> Tuple[float, float]:
    lambda_home = (
        home.attack *
        away.defense *
        home.home_advantage *
        league_avg_home_goals
    )
    lambda_away = (
        away.attack *
        home.defense *
        league_avg_away_goals
    )
    lambda_home = max(0.2, min(lambda_home, 4.5))
    lambda_away = max(0.2, min(lambda_away, 4.0))
    return lambda_home, lambda_away


def build_score_matrix(
    lambda_home: float,
    lambda_away: float,
    max_goals: int = 8
) -> Dict[Tuple[int, int], float]:
    matrix = {}
    total = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson_probability(lambda_home, i) * poisson_probability(lambda_away, j)
            matrix[(i, j)] = p
            total += p
    if total > 0:
        for key in matrix:
            matrix[key] /= total
    return matrix


def predict_match(
    home_team: str,
    away_team: str,
    home_strength: TeamStrength,
    away_strength: TeamStrength,
    league_avg_home_goals: float = 1.45,
    league_avg_away_goals: float = 1.15,
    max_goals: int = 8
) -> MatchPrediction:
    lambda_home, lambda_away = calculate_expected_goals(
        home_strength, away_strength, league_avg_home_goals, league_avg_away_goals
    )
    matrix = build_score_matrix(lambda_home, lambda_away, max_goals)
    prob_home = prob_draw = prob_away = 0.0
    prob_over_25 = 0.0
    prob_btts_yes = 0.0
    most_likely_score = (0, 0)
    max_prob = -1.0
    for (h, a), p in matrix.items():
        if h > a:
            prob_home += p
        elif h == a:
            prob_draw += p
        else:
            prob_away += p
        if (h + a) > 2.5:
            prob_over_25 += p
        if h >= 1 and a >= 1:
            prob_btts_yes += p
        if p > max_prob:
            max_prob = p
            most_likely_score = (h, a)
    return MatchPrediction(
        home_team=home_team,
        away_team=away_team,
        lambda_home=round(lambda_home, 3),
        lambda_away=round(lambda_away, 3),
        prob_home=round(prob_home, 4),
        prob_draw=round(prob_draw, 4),
        prob_away=round(prob_away, 4),
        most_likely_score=most_likely_score,
        prob_over_25=round(prob_over_25, 4),
        prob_under_25=round(1 - prob_over_25, 4),
        prob_btts_yes=round(prob_btts_yes, 4),
        prob_btts_no=round(1 - prob_btts_yes, 4),
        score_matrix=matrix
    )


def calculate_value(prob: float, odd: float) -> float:
    if odd <= 1.0 or prob <= 0:
        return 0.0
    return (prob * odd) - 1.0

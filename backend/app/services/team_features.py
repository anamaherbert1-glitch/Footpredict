from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamFeatures:
    attack: float
    defense: float
    elo: float
    home_advantage: float


def normalize_rating(value: float | None, default: float) -> float:
    if value is None:
        return default
    return max(0.20, min(float(value), 3.00))


def build_team_features(row: tuple) -> TeamFeatures:
    # Les valeurs stockées dans Neon deviennent la source principale du modèle.
    # Les défauts permettent de garder le moteur fonctionnel tant que les données
    # avancées (xG, forme, absences, etc.) ne sont pas encore alimentées.
    _, _, _, _, elo, attack, defense, home_advantage = row
    return TeamFeatures(
        attack=normalize_rating(attack, 1.0),
        defense=normalize_rating(defense, 1.0),
        elo=float(elo) if elo is not None else 1500.0,
        home_advantage=max(0.50, min(float(home_advantage or 1.0), 1.50)),
    )

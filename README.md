# FootPredict

Système de prédiction de matchs de football avec extension Chrome + moteur de probabilités avancé.

## Structure

```
├── extension/          # Extension Chrome (Manifest V3)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js      # Détection Melbet / 1xBet
│   └── sidebar/        # Interface Pro
│
└── backend/
    └── app/models/
        ├── engine.py           # Moteur principal (Elo + Poisson + Dixon-Coles + forme pondérée)
        ├── poisson.py          # Modèle Poisson de base
        └── advanced_model.py   # Version précédente multi-facteurs
```

## Fonctionnalités

### Extension Chrome
- Détection automatique des matchs sur Melbet et 1xBet
- Récupération des cotes 1X2, Over/Under, BTTS
- Interface pro (panneau latéral)
- Calcul de value

### Moteur de prédiction
- **Elo** avec avantage domicile
- **Forme récente pondérée** par la force des adversaires
- **Poisson + Dixon-Coles**
- Impact des absences de joueurs clés
- Jours de repos / fatigue
- Motivation & rivalry
- Score de confiance
- Value betting

## Installation de l'extension

1. Ouvrir `chrome://extensions/`
2. Activer le Mode développeur
3. "Charger l'extension non empaquetée"
4. Sélectionner le dossier `extension/`

## Prochaines étapes

- [ ] Brancher Supabase (stockage Elo, matchs, xG...)
- [ ] API FastAPI
- [ ] Calcul automatique des forces des équipes
- [ ] Backtesting
- [ ] Connexion extension ↔ backend

## Auteur

anamaherbert1-glitch

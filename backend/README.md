# FootPredict backend

## Local setup

1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to the Neon PostgreSQL connection string for the `production` branch.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API:

```bash
uvicorn app.main:app --reload
```

Health check: `GET /health`

The API currently exposes:
- `GET /health`
- `GET /matches`
- `POST /predict`

The database schema is hosted in Neon. Do not commit a real `DATABASE_URL` or database password.

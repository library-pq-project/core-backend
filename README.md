# AI Exam Prep Backend (FastAPI)

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy env file:

```bash
cp .env.example .env
```

4. Run migrations:

```bash
alembic upgrade head
```

5. Seed deterministic admin/student data:

```bash
python scripts/seed_data.py
```

6. Start the server:

```bash
uvicorn src.main:app --reload
```

API docs: `http://127.0.0.1:8000/api/docs`

## Admin Swagger Login

1. Use seeded admin credentials:
`admin@example.com` / `admin123`
2. Call `POST /api/auth/login` in Swagger with:
```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```
3. Copy `access_token` from response.
4. Click `Authorize` in Swagger and paste:
`Bearer <access_token>`
5. Run admin endpoints (for example `POST /api/academic/sessions`).

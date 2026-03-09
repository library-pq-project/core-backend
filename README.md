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

5. Start the server:

```bash
uvicorn src.main:app --reload
```

API docs: `http://127.0.0.1:8000/api/docs`

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

## Prototype Mode (Dev only)

Use this mode to unblock AI generation without JWT/program/session setup friction.

Set in `.env`:

```bash
APP_ENV=development
PROTOTYPE_MODE=true
PROTOTYPE_USER_ID=1
GEMINI_API_KEY=<your_key>
```

Safety rule:
- `PROTOTYPE_MODE=true` is blocked when `APP_ENV=production|prod`.

When prototype mode is on:
- auth resolves a bootstraped local user automatically,
- program/session/semester/active-calendar prerequisites are auto-created,
- missing course/topic/assessment refs in AI requests are auto-created.

### Minimal AI E2E call

`POST /api/ai/question-generation`

```json
{
  "quiz_title": "CSC411 Midsem Practice",
  "user_prompt": "Focus on search algorithms and heuristics with exam-style phrasing.",
  "course_id": 1,
  "topic_ids": [1],
  "lecture_note_id": null,
  "question_type": "objective",
  "difficulty_level": "mixed",
  "requested_count": 5
}
```

`topic_ids` behavior:
- `null` or `[]` => use all topics in the course
- `[id1, id2]` => use only those selected topics

Then fetch persisted questions:
- `GET /api/questions?course_id=1&source_type=ai_generated`
- or assessment-scoped retrieval endpoints if assessment was used.

Generated AI questions now auto-create an AI assessment owned by the current user.
To list your own generated assessments:
- `GET /api/assessments?mine_only=true&source_type=ai_generated`

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

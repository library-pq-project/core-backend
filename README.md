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
FILE_STORAGE_PROVIDER=local
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

## Bulk Question Import

Admin-only endpoints:
- `POST /api/questions/bulk` (JSON payload)
- `POST /api/questions/bulk-upload` (CSV/XLSX/JSON file)
- `GET /api/questions/import-jobs`
- `GET /api/questions/import-jobs/{job_id}`

JSON bulk payload:

```json
{
  "import_mode": "mixed",
  "default_course_id": 1,
  "default_assessment_id": 1,
  "default_source_type": "actual",
  "auto_categorize_topics": true,
  "draft_theory_without_solution": false,
  "rows": [
    {
      "question_type": "objective",
      "question_text": "Which search is uninformed?",
      "mark_allocation": 2,
      "options": [
        {"option_text": "A*", "position": 1, "is_correct": false},
        {"option_text": "Breadth-first search", "position": 2, "is_correct": true}
      ]
    },
    {
      "question_type": "theory",
      "question_text": "Explain admissibility in A*.",
      "mark_allocation": 5,
      "marking_scheme": "Define admissibility and justify optimality.",
      "solution_text": "A heuristic is admissible if it never overestimates..."
    }
  ]
}
```

CSV/XLSX supported columns:
- `assessment_id`, `course_id`, `topic_id`, `topic_name`
- `question_type`, `question_text`, `source_text`, `content_format`
- `mark_allocation`, `marking_scheme`, `solution_text`, `explanation`
- Objective options: `option_a`, `option_b`, `option_c`, `option_d`
- Correct option: `correct_option_position` (1..n) or `correct_option_label` (`A`, `B`, ...)

## Bulk Topic Upsert

Admin-only endpoints:
- `POST /api/topics/bulk-upsert` (JSON)
- `POST /api/topics/bulk-upload` (CSV/XLSX/JSON)

JSON payload:

```json
{
  "rows": [
    {"course_id": 1, "name": "Search Algorithms", "description": "Graph search methods"},
    {"course_id": 1, "name": "Knowledge Representation", "description": "Logic and ontologies"}
  ]
}
```

## Topic Auto-categorization Policy

Applied during AI generation and question bulk import:
- score against existing course topics
- if confidence >= `TOPIC_CLASSIFICATION_CONFIDENCE_THRESHOLD`, assign matched topic
- else:
  - if `AUTO_CREATE_TOPIC_IF_LOW_CONFIDENCE=true`, create topic
  - otherwise assign/create `UNCATEGORIZED_TOPIC_NAME`

## Course Compacts

Admin endpoints:
- `POST /api/courses/{course_id}/compacts` upload compact (`pdf/docx/txt/md/json`)
- `POST /api/courses/{course_id}/compacts/{compact_id}/activate` set active compact
- `GET /api/courses/{course_id}/compacts`
- `GET /api/courses/{course_id}/compact-active`

Active compact text is injected into AI generation context.

## File Storage Provider

`FILE_STORAGE_PROVIDER`:
- `local` for development
- `s3` for production

### Local storage mode

For local development, use:

```bash
FILE_STORAGE_PROVIDER=local
UPLOAD_DIR=uploads
```

No R2 / S3 credentials are required in local mode.

When using `s3`, configure:
- `S3_ENDPOINT_URL` (optional for S3-compatible services)
- `R2_ACCOUNT_ID` (optional helper for Cloudflare R2; endpoint is auto-derived if `S3_ENDPOINT_URL` is empty)
- `S3_BUCKET_NAME`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_REGION` (`auto` recommended for R2)
- `S3_ADDRESSING_STYLE` (`path` recommended for R2; default auto)
- `S3_KEY_PREFIX` (optional)

### Cloudflare R2 quick env

```bash
FILE_STORAGE_PROVIDER=s3
R2_ACCOUNT_ID=<your_account_id>
S3_BUCKET_NAME=<your_bucket_name>
S3_ACCESS_KEY_ID=<r2_access_key_id>
S3_SECRET_ACCESS_KEY=<r2_secret_access_key>
S3_REGION=auto
S3_ADDRESSING_STYLE=path
```

Notes:
- non-upload endpoints do not require R2 credentials even if upload features exist in the project
- upload endpoints only initialize object storage when they are actually used

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

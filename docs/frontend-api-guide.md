# Frontend API Guide

This document covers the main endpoints the frontend is most likely to need. It is intentionally selective: the goal is to help Dami ship the UI without wading through every internal or low-level route.

For each endpoint, this guide explains:

- what the endpoint is used for
- which attributes are required
- the allowed values for each attribute
- where the frontend should fetch valid values from when that applies

## Authentication

### `POST /api/auth/login`

Use this to log a user in.

**Request body**

```json
{
  "email": "student@example.com",
  "password": "string"
}
```

**Fields**

| Field | Required | Type | Allowed values | Where values come from |
|---|---|---|---|---|
| `email` | Yes | string | Any valid email address | User input |
| `password` | Yes | string | Any password string | User input |

**Response**

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

Use the token as:

```http
Authorization: Bearer <access_token>
```

### `GET /api/auth/me`

Use this after login to get the current user profile.

Important response fields:

| Field | Meaning | Notes |
|---|---|---|
| `role` | User role | Common values are `student` and `admin` |
| `program_id` | User's program | Can be `null` until profile is completed |
| `current_level` | User's academic level | Backend accepts free text |
| `profile_update_required` | Whether user should update profile | Boolean |

### `PUT /api/auth/me/profile`

Use this when a student updates their academic identity.

**Request body**

```json
{
  "program_id": 1,
  "current_level": "400"
}
```

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `program_id` | Yes | integer | Existing program IDs | `GET /api/academic/programs` |
| `current_level` | Yes | string | Free text in backend; frontend should restrict to institutional levels like `100`, `200`, `300`, `400`, `500` | Frontend-controlled |

## Academic Lookups

These are useful for populating dropdowns and other selectors.

### `GET /api/academic/programs`

Use for program selection.

### `GET /api/academic/sessions`

Use for `academic_session_id`.

### `GET /api/academic/semesters`

Use for `semester_id`.

### `GET /api/academic/me/offered-courses`

Use this to fetch only the courses currently relevant to the logged-in student.

**Query params**

| Field | Required | Type | Allowed values |
|---|---|---|---|
| `skip` | No | integer | `>= 0` |
| `limit` | No | integer | `1..100` |

## Courses and Topics

### `GET /api/courses`

Use to list all courses.

**Query params**

| Field | Required | Type | Allowed values |
|---|---|---|---|
| `skip` | No | integer | `>= 0` |
| `limit` | No | integer | `1..100` |

### `GET /api/topics`

Use to list topics, optionally for a specific course.

**Query params**

| Field | Required | Type | Allowed values | Where values come from |
|---|---|---|---|---|
| `course_id` | No | integer | Existing course IDs | `GET /api/courses` or `GET /api/academic/me/offered-courses` |
| `skip` | No | integer | `>= 0` | Static |
| `limit` | No | integer | `1..100` | Static |

### `GET /api/topics/in-course/{course_slug}`

Alternative topic lookup using course slug.

| Field | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|
| `course_slug` | string | Existing course slug | `GET /api/courses` |

## Lecture Notes

### `POST /api/lecture-notes`

Use this when a student uploads lecture notes for AI question generation.

**Content type**

`multipart/form-data`

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `title` | Yes | string | Any non-empty text | User input |
| `course_id` | Yes | integer | Existing course IDs | `GET /api/courses` or `GET /api/academic/me/offered-courses` |
| `file` | Yes | file | Supported note file types accepted by backend | User upload |

### `GET /api/lecture-notes`

Use this to list current user's lecture notes.

**Query params**

| Field | Required | Type | Allowed values |
|---|---|---|---|
| `skip` | No | integer | `>= 0` |
| `limit` | No | integer | `1..100` |

Use this endpoint to get valid `lecture_note_id` values.

## Assessments and Past Question Sets

### `GET /api/assessments`

Use this when a student selects a course and needs all available past question sets or AI-generated assessments.

**Query params**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `course_id` | No | integer | Existing course IDs | `GET /api/courses` |
| `academic_session_id` | No | integer | Existing session IDs | `GET /api/academic/sessions` |
| `semester_id` | No | integer | Existing semester IDs | `GET /api/academic/semesters` |
| `assessment_type` | No | string | Free text in backend; common values include `Test 1`, `Test 2`, `Midsemester`, `Exam`, `AI Practice Set` | Usually returned by this same endpoint |
| `source_type` | No | string | `actual`, `ai_generated` | Static enum |
| `mine_only` | No | boolean | `true`, `false` | Static |
| `skip` | No | integer | `>= 0` | Static |
| `limit` | No | integer | `1..100` | Static |

Use this endpoint to get valid `assessment_id` values.

### `GET /api/assessments/{assessment_id}/practice-config`

Use this before starting practice from an assessment.

| Field | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|
| `assessment_id` | integer | Existing assessment IDs | `GET /api/assessments` |

This endpoint returns:

- assessment metadata
- selectable topics
- question count constraints
- duration constraints

### `POST /api/assessments/{assessment_id}/practice/start`

Use this to create a practice quiz and immediately start an attempt from an assessment.

**Request body**

```json
{
  "desired_question_count": 10,
  "selected_topic_ids": [12, 13],
  "selected_duration_minutes": 30,
  "reveal_answers_post_submit": false
}
```

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `desired_question_count` | Yes | integer | `1..200` | Must also respect assessment constraints from practice-config |
| `selected_topic_ids` | No | array of integers | Topic IDs under that assessment/course | `GET /api/assessments/{assessment_id}/practice-config` |
| `selected_duration_minutes` | No | integer | `1..600` | Should respect min/max duration returned by practice-config |
| `reveal_answers_post_submit` | No | boolean | `true`, `false` | Static |

Notes:

- `selected_topic_ids = null` means all topics.
- The response returns the created `quiz` and `attempt`.

## AI Question Generation

### `POST /api/ai/question-generation`

Use this to generate AI questions from course context and an optional lecture note.

**Request body**

```json
{
  "quiz_title": "HCI Practice",
  "user_prompt": "Generate smart practice questions on usability heuristics.",
  "course_id": 3,
  "topic_ids": [12, 13],
  "lecture_note_id": 2,
  "question_type": "objective",
  "difficulty_level": "medium",
  "requested_count": 10
}
```

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `quiz_title` | Yes | string | Any non-empty text | User input |
| `user_prompt` | Yes | string | Any free-text instruction | User input |
| `course_id` | Yes | integer | Existing course IDs | `GET /api/courses` |
| `topic_ids` | No | array of integers | Topic IDs under selected course | `GET /api/topics?course_id={course_id}` |
| `lecture_note_id` | No | integer | Current user's lecture note IDs | `GET /api/lecture-notes` |
| `question_type` | No | string | `objective`, `theory`, `practical`, `case_based`, `mixed` | Static enum |
| `difficulty_level` | No | string | `easy`, `medium`, `hard`, `mixed` | Static enum |
| `requested_count` | Yes | integer | `1..100` | Static |

Notes:

- `topic_ids = null` or `[]` means all topics under the selected course.
- Generated questions are saved and linked to an AI-generated assessment.

## Quiz Attempt Flow

### `GET /api/quizzes/{quiz_id}/questions`

Use this to fetch the stored question set for a quiz.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `quiz_id` | Path | integer | Existing quiz ID | Comes from quiz creation/start responses |
| `skip` | Query | integer | `>= 0` | Static |
| `limit` | Query | integer | `1..100` | Static |

The response contains:

- `question_snapshot_text`
- `question_type`
- `options`

Use this when you want the quiz definition itself, not the student’s current answer state.

### `GET /api/quiz-attempts/{attempt_id}/questions`

Use this to restore attempt state after refresh or reconnection, or to load questions for the active attempt.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `attempt_id` | Path | integer | Existing attempt ID | Comes from assessment practice start or quiz attempt start |
| `skip` | Query | integer | `>= 0` | Static |
| `limit` | Query | integer | `1..100` | Static |

### `POST /api/quiz-attempts/{attempt_id}/submit`

Use this to submit answers.

**Request body**

```json
{
  "responses": [
    {
      "quiz_question_id": 101,
      "selected_quiz_question_option_id": 1001,
      "answer_text": null
    },
    {
      "quiz_question_id": 102,
      "selected_quiz_question_option_id": null,
      "answer_text": "Usability heuristics are general design principles..."
    }
  ]
}
```

**Response item fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `quiz_question_id` | Yes | integer | Existing quiz question ID for that attempt | `GET /api/quiz-attempts/{attempt_id}/questions` |
| `selected_quiz_question_option_id` | No | integer | One of the option IDs for that quiz question | `GET /api/quiz-attempts/{attempt_id}/questions` |
| `answer_text` | No | string | Free text | User input |

Rules:

- Objective questions use `selected_quiz_question_option_id`
- Theory questions usually use `answer_text` or file upload

## Theory Answer Upload

### `POST /api/quiz-attempts/{attempt_id}/theory-answers/upload`

Use this when a theory answer is uploaded as a file.

**Content type**

`multipart/form-data`

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `quiz_question_id` | Yes | integer | Existing quiz question ID for that attempt | `GET /api/quiz-attempts/{attempt_id}/questions` |
| `file` | Yes | file | Currently supported: `pdf`, `png`, `jpg`, `jpeg`, `txt`, `md`, `docx` | User upload |

## Grading, Result, and Review

### `POST /api/quiz-attempts/{attempt_id}/grade`

Use this after submission to trigger grading.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `attempt_id` | Path | integer | Existing attempt ID | Comes from quiz lifecycle |

No request body.

### `GET /api/quiz-attempts/{attempt_id}/result`

Use this for the result summary page.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `attempt_id` | Path | integer | Existing attempt ID | Comes from quiz lifecycle |

Important response fields:

- `status`
- `selected_duration_minutes`
- `total_score`
- `max_score`
- `percentage_score`
- `topic_analysis`

### `GET /api/quiz-attempts/{attempt_id}/review`

Use this for question-by-question review after submission.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `attempt_id` | Path | integer | Existing attempt ID | Comes from quiz lifecycle |
| `skip` | Query | integer | `>= 0` | Static |
| `limit` | Query | integer | `1..100` | Static |

Important note:

- Correct answers are only shown if backend visibility policy allows it.

## Analytics

### `GET /api/analytics/me/overview`

Use for a summary dashboard.

Returns:

- `quizzes_taken`
- `total_questions_attempted`
- `total_correct_answers`
- `average_accuracy`

### `GET /api/analytics/me/topic-performance`

Use for aggregated topic-level performance.

**Query params**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `course_id` | No | integer | Existing course IDs | `GET /api/courses` |
| `academic_session_id` | No | integer | Existing academic session IDs | `GET /api/academic/sessions` |
| `topic_id` | No | integer | Existing topic IDs under the selected course | `GET /api/topics?course_id={course_id}` |

### `GET /api/analytics/me/attempt-topic-metrics`

Use for attempt-level topic metric history.

**Query params**

| Field | Required | Type | Allowed values |
|---|---|---|---|
| `skip` | No | integer | `>= 0` |
| `limit` | No | integer | `1..100` |

## Admin Content Setup

### `POST /api/topics/bulk-upsert`

Use this when the frontend already has the full topic list and wants to send all topics in one request.

**Request body**

```json
{
  "rows": [
    {
      "course_id": 3,
      "name": "Usability Heuristics",
      "description": "Nielsen principles"
    },
    {
      "course_id": 3,
      "name": "User Research",
      "description": "Interviews and surveys"
    }
  ]
}
```

**Fields per row**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `course_id` | Yes | integer | Existing course IDs | `GET /api/courses` |
| `name` | Yes | string | Any non-empty topic name | User/admin input |
| `description` | No | string | Any text | User/admin input |

### `POST /api/courses/{course_id}/compacts`

Use this to upload a course compact.

**Content type**

`multipart/form-data`

**Fields**

| Field | Required | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `course_id` | Yes | path integer | Existing course IDs | `GET /api/courses` |
| `title` | Yes | string | Any non-empty text | User/admin input |
| `file` | Yes | file | Supported compact file type accepted by backend | User upload |

### `GET /api/courses/{course_id}/compacts`

Use this to list compact versions for a course.

**Query params**

| Field | Required | Type | Allowed values |
|---|---|---|---|
| `active_only` | No | boolean | `true`, `false` |
| `skip` | No | integer | `>= 0` |
| `limit` | No | integer | `1..100` |

### `POST /api/courses/{course_id}/compacts/{compact_id}/activate`

Use this to set a compact version as active.

| Field | Location | Type | Allowed values | Where to fetch valid values |
|---|---|---|---|---|
| `course_id` | Path | integer | Existing course IDs | `GET /api/courses` |
| `compact_id` | Path | integer | Existing compact IDs for that course | `GET /api/courses/{course_id}/compacts` |

## Quick Reference for Common Lookup Dependencies

| Need | Endpoint to fetch values |
|---|---|
| Programs | `GET /api/academic/programs` |
| Sessions | `GET /api/academic/sessions` |
| Semesters | `GET /api/academic/semesters` |
| Student's offered courses | `GET /api/academic/me/offered-courses` |
| All courses | `GET /api/courses` |
| Topics for a course | `GET /api/topics?course_id={course_id}` |
| Assessments for a course | `GET /api/assessments?course_id={course_id}` |
| Lecture notes | `GET /api/lecture-notes` |
| Topics available in an assessment practice setup | `GET /api/assessments/{assessment_id}/practice-config` |
| Quiz question IDs and option IDs for a live attempt | `GET /api/quiz-attempts/{attempt_id}/questions` |

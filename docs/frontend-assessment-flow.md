# Frontend Guide: Assessment Attempt Flow

This guide explains the exact frontend flow for a student taking an assessment from start to completion.

It reflects the current public API shape:

- `assessments` are the public starting point
- `quiz-attempts` are the public working lifecycle
- `quizzes` are internal backend containers and should not be used directly by the frontend

---

## 1. Main idea

The frontend flow should be:

1. Student logs in
2. Frontend loads available assessments
3. Student opens one assessment
4. Frontend loads practice configuration for that assessment
5. Student starts practice
6. Frontend receives `attempt.id`
7. Frontend loads attempt questions using `attempt.id`
8. Student answers questions
9. Frontend submits answers
10. Frontend triggers grading
11. Frontend loads result
12. Frontend loads review

After the attempt is created, the frontend should work with `attempt_id`, not `assessment_id`.

---

## 2. Endpoints used in order

### Step 1. Log in

`POST /api/auth/login`

Example request:

```json
{
  "email": "student@example.com",
  "password": "string"
}
```

Use the returned access token as:

```http
Authorization: Bearer <access_token>
```

---

### Step 2. Load assessments

`GET /api/assessments`

Useful filters:

- `course_id`
- `academic_session_id`
- `semester_id`
- `assessment_type`
- `source_type`

Example:

```http
GET /api/assessments?course_id=1&academic_session_id=1&semester_id=1
```

Use this to display the list of available assessment sources.

---

### Step 3. Load practice configuration for one assessment

`GET /api/assessments/{assessment_id}/practice-config`

Use this before starting practice.

It returns:

- assessment metadata
- available topics under that assessment
- minimum and maximum number of questions
- minimum and maximum duration

Example response shape:

```json
{
  "assessment": {
    "id": 1,
    "title_label": "2024/2025 • Test1 • Objective",
    "course_id": 1,
    "academic_session_id": 1,
    "semester_id": 1,
    "default_duration_minutes": 60,
    "total_available_questions": 20
  },
  "selectable_topics": [
    {
      "id": 4,
      "name": "Machine Learning Basics",
      "slug": "machine-learning-basics"
    }
  ],
  "constraints": {
    "min_questions": 1,
    "max_questions": 20,
    "min_duration_minutes": 1,
    "max_duration_minutes": 120
  }
}
```

Frontend use:

- populate topic picker from `selectable_topics`
- validate question count and duration before sending the start request

---

### Step 4. Start practice

`POST /api/assessments/{assessment_id}/practice/start`

Example request:

```json
{
  "desired_question_count": 10,
  "selected_topic_ids": [4, 5],
  "selected_duration_minutes": 30,
  "reveal_answers_post_submit": false
}
```

Field meaning:

- `desired_question_count`: how many questions the student wants
- `selected_topic_ids`: optional topic filter; `null` means all topics
- `selected_duration_minutes`: optional duration override within allowed constraints
- `reveal_answers_post_submit`: whether correct answers should be visible during review after submission

Example response shape:

```json
{
  "quiz_id": 12,
  "attempt": {
    "id": 33,
    "quiz_id": 12,
    "user_id": 8,
    "attempt_number": 1,
    "status": "in_progress",
    "started_at": "2026-06-16T10:20:00Z",
    "expected_end_at": "2026-06-16T10:50:00Z",
    "submitted_at": null,
    "duration_used_seconds": null,
    "selected_duration_minutes": 30,
    "graded_at": null
  },
  "available_question_count": 20
}
```

Frontend rule:

- store `attempt.id`
- use `attempt.id` for the rest of the workflow
- `quiz_id` can be treated as internal and ignored by the frontend in normal flow

---

### Step 5. Load attempt questions

`GET /api/quiz-attempts/{attempt_id}/questions`

Example:

```http
GET /api/quiz-attempts/33/questions
```

This returns the question set for the student’s active attempt.

Example response shape:

```json
[
  {
    "quiz_question_id": 101,
    "question_text": "What is supervised learning?",
    "question_type": "objective",
    "sequence_number": 1,
    "options": [
      {
        "id": 1001,
        "option_text_snapshot": "Option A",
        "display_order": 1
      },
      {
        "id": 1002,
        "option_text_snapshot": "Option B",
        "display_order": 2
      }
    ],
    "selected_quiz_question_option_id": null,
    "answer_text": null
  },
  {
    "quiz_question_id": 102,
    "question_text": "Explain reinforcement learning.",
    "question_type": "theory",
    "sequence_number": 2,
    "options": [],
    "selected_quiz_question_option_id": null,
    "answer_text": null
  }
]
```

Frontend use:

- render question list
- for objective questions, render `options`
- for theory questions, render a text area or file upload control
- if the student refreshes, call this endpoint again to recover state

---

## 3. How to submit answers

### Objective question

Send:

- `quiz_question_id`
- `selected_quiz_question_option_id`

Example:

```json
{
  "quiz_question_id": 101,
  "selected_quiz_question_option_id": 1002,
  "answer_text": null
}
```

### Theory question typed into the UI

Send:

- `quiz_question_id`
- `answer_text`

Example:

```json
{
  "quiz_question_id": 102,
  "selected_quiz_question_option_id": null,
  "answer_text": "Reinforcement learning is a learning method where an agent learns through rewards and penalties."
}
```

---

### Step 6. Submit all answers

`POST /api/quiz-attempts/{attempt_id}/submit`

Example request:

```json
{
  "responses": [
    {
      "quiz_question_id": 101,
      "selected_quiz_question_option_id": 1002,
      "answer_text": null
    },
    {
      "quiz_question_id": 102,
      "selected_quiz_question_option_id": null,
      "answer_text": "Reinforcement learning is a learning method where an agent learns through rewards and penalties."
    }
  ]
}
```

Important frontend rules:

- send one item per answered question
- objective answers should use `selected_quiz_question_option_id`
- typed theory answers should use `answer_text`
- if a theory answer is submitted as a file, upload the file separately using the upload endpoint below

---

## 4. Theory answer file upload

Use this only when the student uploads a file for a theory answer.

### Step 7. Upload theory answer file

`POST /api/quiz-attempts/{attempt_id}/theory-answers/upload`

Content type:

`multipart/form-data`

Fields:

- `quiz_question_id`
- `file`

Supported file types:

- `pdf`
- `png`
- `jpg`
- `jpeg`
- `txt`
- `md`
- `docx`

Example response shape:

```json
{
  "attempt_id": 33,
  "quiz_question_id": 102,
  "answer_extraction_status": "completed",
  "extracted_text_preview": "Reinforcement learning is..."
}
```

Frontend note:

- this endpoint stores the file and extracts text
- after upload, the student can still continue the attempt until final submission

---

## 5. Grading

### Step 8. Trigger grading

`POST /api/quiz-attempts/{attempt_id}/grade`

No request body.

Example response shape:

```json
{
  "attempt_id": 33,
  "quiz_id": 12,
  "graded": true,
  "total_score": 18.0,
  "max_score": 20.0,
  "percentage_score": 90.0
}
```

Frontend note:

- submit first
- then grade
- do not call grade before submission

---

## 6. Result page

### Step 9. Load result summary

`GET /api/quiz-attempts/{attempt_id}/result`

Example response shape:

```json
{
  "attempt_id": 33,
  "quiz_id": 12,
  "status": "graded",
  "started_at": "2026-06-16T10:20:00Z",
  "expected_end_at": "2026-06-16T10:50:00Z",
  "submitted_at": "2026-06-16T10:42:00Z",
  "duration_used_seconds": 1320,
  "selected_duration_minutes": 30,
  "total_score": 18.0,
  "max_score": 20.0,
  "percentage_score": 90.0,
  "correct_count": 8,
  "wrong_count": 1,
  "unanswered_count": 1,
  "topic_analysis": [
    {
      "topic_id": 4,
      "attempted_count": 5,
      "correct_count": 4,
      "accuracy_rate": 80.0,
      "score": 8.0
    }
  ]
}
```

Use this for:

- score summary
- percentage
- correct/wrong/unanswered counts
- topic analysis

---

## 7. Review page

### Step 10. Load review

`GET /api/quiz-attempts/{attempt_id}/review`

Use this for question-by-question feedback after submission.

Important response fields:

- `question_text`
- `question_type`
- `selected_option_text`
- `correct_option_text`
- `answer_text`
- `answer_extracted_text`
- `student_submission_mode`
- `feedback`
- `score_awarded`
- `grading_strengths`
- `grading_missing_points`
- `grading_confidence`

---

## 8. Meaning of `student_submission_mode`

`student_submission_mode` in the review response tells the frontend how the student submitted that answer.

Current values used by the backend are:

- `typed`
- `upload`

### `typed`

This means the answer was submitted directly as text in the request body using `answer_text`.

Example:

```json
{
  "quiz_question_id": 102,
  "selected_quiz_question_option_id": null,
  "answer_text": "My typed answer here"
}
```

### `upload`

This means the answer came from an uploaded file through:

- `POST /api/quiz-attempts/{attempt_id}/theory-answers/upload`

In that case, the backend stores:

- uploaded file metadata
- extracted text

For review screens:

- if `student_submission_mode = typed`, prefer showing `answer_text`
- if `student_submission_mode = upload`, prefer showing `answer_extracted_text`

---

## 9. Recommended frontend state flow

### Assessment list page

Use:

- `GET /api/assessments`

### Assessment setup modal/page

Use:

- `GET /api/assessments/{assessment_id}/practice-config`

### Start button

Use:

- `POST /api/assessments/{assessment_id}/practice/start`

Store:

- `attempt.id`

### Active attempt page

Use:

- `GET /api/quiz-attempts/{attempt_id}/questions`
- `POST /api/quiz-attempts/{attempt_id}/theory-answers/upload` when needed
- `POST /api/quiz-attempts/{attempt_id}/submit`

### Result page

Use:

- `POST /api/quiz-attempts/{attempt_id}/grade`
- `GET /api/quiz-attempts/{attempt_id}/result`

### Review page

Use:

- `GET /api/quiz-attempts/{attempt_id}/review`

---

## 10. Minimal exact frontend sequence

1. `GET /api/assessments`
2. `GET /api/assessments/{assessment_id}/practice-config`
3. `POST /api/assessments/{assessment_id}/practice/start`
4. `GET /api/quiz-attempts/{attempt_id}/questions`
5. Optional: `POST /api/quiz-attempts/{attempt_id}/theory-answers/upload`
6. `POST /api/quiz-attempts/{attempt_id}/submit`
7. `POST /api/quiz-attempts/{attempt_id}/grade`
8. `GET /api/quiz-attempts/{attempt_id}/result`
9. `GET /api/quiz-attempts/{attempt_id}/review`

That is the exact public assessment-to-completion flow the frontend should implement.

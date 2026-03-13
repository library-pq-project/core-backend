import random
from datetime import timedelta

from fastapi import HTTPException, status

from src.common.enums import QuizStatus
from src.common.utils import generate_slug, now_utc
from src.core.config import settings
from src.modules.quizzes.models import Quiz, QuizAttempt, QuizQuestion, QuizQuestionOption, QuizResponse
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import QuizCreate, QuizSubmitInput


class QuizService:
    def __init__(self, repository: QuizRepository):
        self.repository = repository

    def create_quiz(self, payload: QuizCreate, user_id: int) -> Quiz:
        selected_questions = self.repository.select_questions(
            course_id=payload.course_id,
            assessment_id=payload.assessment_id,
            topic_id=payload.topic_id,
            question_source_mode=payload.question_source_mode,
            question_type_mode=payload.question_type_mode,
            total_questions=payload.total_questions,
        )

        if len(selected_questions) < payload.total_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough questions for the selected filters",
            )

        quiz = Quiz(
            user_id=user_id,
            title=payload.title,
            slug=generate_slug(payload.title),
            course_id=payload.course_id,
            assessment_id=payload.assessment_id,
            topic_id=payload.topic_id,
            academic_session_id=payload.academic_session_id,
            semester_id=payload.semester_id,
            question_source_mode=payload.question_source_mode,
            question_type_mode=payload.question_type_mode,
            total_questions=payload.total_questions,
            max_attempts=payload.max_attempts,
            reveal_answers_post_submit=payload.reveal_answers_post_submit,
            status=QuizStatus.DRAFT.value,
        )

        for index, question in enumerate(selected_questions, start=1):
            quiz_question = QuizQuestion(
                question_id=question.id,
                question_snapshot_text=question.question_text,
                question_type=question.question_type,
                marks=float(question.mark_allocation),
                sequence_number=index,
            )

            if question.question_type == "objective":
                canonical_options = list(question.options)
                random.shuffle(canonical_options)
                for display_order, option in enumerate(canonical_options, start=1):
                    quiz_question.options.append(
                        QuizQuestionOption(
                            question_option_id=option.id,
                            option_text_snapshot=option.option_text,
                            is_correct_snapshot=option.is_correct,
                            display_order=display_order,
                        )
                    )

            quiz.quiz_questions.append(quiz_question)

        return self.repository.save_quiz(quiz)

    def list_quizzes(self, user_id: int, *, skip: int, limit: int) -> list[Quiz]:
        return self.repository.list_user_quizzes(user_id, skip=skip, limit=limit)

    def get_quiz(self, quiz_id: int, user_id: int) -> Quiz:
        quiz = self.repository.get_user_quiz(quiz_id, user_id)
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
        return quiz

    def _resolve_attempt_duration_minutes(
        self,
        *,
        quiz: Quiz,
        selected_duration_minutes: int | None,
    ) -> int:
        if quiz.assessment_id is not None:
            assessment = self.repository.get_assessment(quiz.assessment_id)
            default_duration = assessment.default_duration_minutes if assessment else 60
        else:
            default_duration = 60

        if selected_duration_minutes is None:
            return default_duration

        if selected_duration_minutes <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="selected_duration_minutes must be > 0")

        cap = min(settings.MAX_ATTEMPT_DURATION_MINUTES, max(default_duration * 2, default_duration))
        if selected_duration_minutes > cap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"selected_duration_minutes exceeds allowed cap ({cap})",
            )
        return selected_duration_minutes

    def start_attempt(self, quiz_id: int, user_id: int, selected_duration_minutes: int | None = None) -> QuizAttempt:
        quiz = self.get_quiz(quiz_id, user_id)
        latest = self.repository.get_latest_attempt(quiz_id, user_id)
        next_attempt_number = 1 if latest is None else latest.attempt_number + 1
        if next_attempt_number > quiz.max_attempts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum attempts reached")

        duration_minutes = self._resolve_attempt_duration_minutes(
            quiz=quiz,
            selected_duration_minutes=selected_duration_minutes,
        )
        started = now_utc()

        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_number=next_attempt_number,
            status=QuizStatus.IN_PROGRESS.value,
            started_at=started,
            expected_end_at=started + timedelta(minutes=duration_minutes),
            selected_duration_minutes=duration_minutes,
        )

        if quiz.status == QuizStatus.DRAFT.value:
            quiz.status = QuizStatus.IN_PROGRESS.value
            quiz.started_at = started
            self.repository.commit()

        return self.repository.save_attempt(attempt)

    def start_quiz(self, quiz_id: int, user_id: int) -> Quiz:
        self.start_attempt(quiz_id, user_id)
        return self.get_quiz(quiz_id, user_id)

    def _submit_for_attempt(
        self, quiz: Quiz, user_id: int, attempt: QuizAttempt, payload: QuizSubmitInput
    ) -> QuizAttempt:
        if attempt.status != QuizStatus.IN_PROGRESS.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is not in progress")

        quiz_question_map = {question.id: question for question in quiz.quiz_questions}
        for response_item in payload.responses:
            if response_item.quiz_question_id not in quiz_question_map:
                continue

            existing = self.repository.find_response(
                attempt_id=attempt.id,
                quiz_question_id=response_item.quiz_question_id,
                user_id=user_id,
            )
            if existing:
                existing.selected_quiz_question_option_id = response_item.selected_quiz_question_option_id
                existing.answer_text = response_item.answer_text
                self.repository.commit()
            else:
                response = QuizResponse(
                    attempt_id=attempt.id,
                    quiz_question_id=response_item.quiz_question_id,
                    user_id=user_id,
                    selected_quiz_question_option_id=response_item.selected_quiz_question_option_id,
                    answer_text=response_item.answer_text,
                )
                self.repository.upsert_response(response)

        submitted_at = now_utc()
        attempt.status = QuizStatus.SUBMITTED.value
        attempt.submitted_at = submitted_at
        attempt.duration_used_seconds = int((submitted_at - attempt.started_at).total_seconds())
        quiz.status = QuizStatus.SUBMITTED.value
        quiz.submitted_at = submitted_at
        self.repository.commit()
        return attempt

    def submit_quiz_for_attempt(
        self,
        *,
        quiz_id: int,
        user_id: int,
        attempt_id: int,
        payload: QuizSubmitInput,
    ) -> QuizAttempt:
        quiz = self.get_quiz(quiz_id, user_id)
        attempt = self.repository.get_attempt(quiz_id, attempt_id, user_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        return self._submit_for_attempt(quiz, user_id, attempt, payload)

    def submit_quiz(self, quiz_id: int, user_id: int, payload: QuizSubmitInput) -> Quiz:
        quiz = self.get_quiz(quiz_id, user_id)
        attempt = self.repository.get_latest_attempt(quiz_id, user_id)
        if attempt is None:
            attempt = self.start_attempt(quiz_id, user_id)
        self._submit_for_attempt(quiz, user_id, attempt, payload)
        return self.get_quiz(quiz_id, user_id)

    def get_in_progress_questions(self, quiz_id: int, user_id: int):
        quiz = self.get_quiz(quiz_id, user_id)
        attempt = self.repository.get_latest_attempt(quiz_id, user_id)
        if attempt is None or attempt.status != QuizStatus.IN_PROGRESS.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No in-progress attempt found")
        return quiz, attempt

    def get_attempt_questions(self, quiz_id: int, attempt_id: int, user_id: int):
        quiz = self.get_quiz(quiz_id, user_id)
        attempt = self.repository.get_attempt(quiz_id, attempt_id, user_id)
        if attempt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        responses = {
            response.quiz_question_id: response
            for response in self.repository.list_responses_for_attempt(attempt_id, user_id)
        }
        return quiz, attempt, responses

    def get_attempt_questions_by_attempt_id(self, attempt_id: int, user_id: int):
        attempt = self.repository.get_attempt_by_id(attempt_id, user_id)
        if attempt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        return self.get_attempt_questions(attempt.quiz_id, attempt_id, user_id)

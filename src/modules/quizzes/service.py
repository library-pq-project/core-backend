import random

from fastapi import HTTPException, status

from src.common.enums import QuizStatus
from src.common.utils import generate_slug, now_utc
from src.modules.quizzes.models import Quiz, QuizQuestion, QuizQuestionOption, QuizResponse
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import QuizCreate, QuizSubmitInput


class QuizService:
    def __init__(self, repository: QuizRepository):
        self.repository = repository

    def create_quiz(self, payload: QuizCreate, user_id: int) -> Quiz:
        selected_questions = self.repository.select_questions(
            course_id=payload.course_id,
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
            topic_id=payload.topic_id,
            question_source_mode=payload.question_source_mode,
            question_type_mode=payload.question_type_mode,
            total_questions=payload.total_questions,
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

            # Objective options are shuffled once and persisted for this quiz.
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

    def start_quiz(self, quiz_id: int, user_id: int) -> Quiz:
        quiz = self.get_quiz(quiz_id, user_id)
        if quiz.status == QuizStatus.DRAFT.value:
            quiz.status = QuizStatus.IN_PROGRESS.value
            quiz.started_at = now_utc()
            self.repository.commit()
        return quiz

    def submit_quiz(self, quiz_id: int, user_id: int, payload: QuizSubmitInput) -> Quiz:
        quiz = self.get_quiz(quiz_id, user_id)
        if quiz.status not in [QuizStatus.DRAFT.value, QuizStatus.IN_PROGRESS.value]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz cannot be submitted")

        quiz_question_map = {question.id: question for question in quiz.quiz_questions}
        for response_item in payload.responses:
            if response_item.quiz_question_id not in quiz_question_map:
                continue

            existing = self.repository.find_response(response_item.quiz_question_id, user_id)
            if existing:
                existing.selected_quiz_question_option_id = response_item.selected_quiz_question_option_id
                existing.answer_text = response_item.answer_text
                self.repository.commit()
            else:
                response = QuizResponse(
                    quiz_question_id=response_item.quiz_question_id,
                    user_id=user_id,
                    selected_quiz_question_option_id=response_item.selected_quiz_question_option_id,
                    answer_text=response_item.answer_text,
                )
                self.repository.upsert_response(response)

        quiz.status = QuizStatus.SUBMITTED.value
        quiz.submitted_at = now_utc()
        self.repository.commit()
        return quiz

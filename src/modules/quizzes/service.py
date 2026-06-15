import random
from datetime import timedelta
from io import BytesIO

from docx import Document
from pypdf import PdfReader

from src.common.errors import bad_request, not_found
from src.common.enums import QuizStatus
from src.common.utils import generate_slug, now_utc
from src.core.config import settings
from src.modules.lecture_notes.storage import FileStorageProvider, build_storage_provider
from src.modules.quizzes.models import Quiz, QuizAttempt, QuizQuestion, QuizQuestionOption, QuizResponse
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import QuizCreate, QuizSubmitInput


class QuizService:
    def __init__(self, repository: QuizRepository, storage_provider: FileStorageProvider | None = None):
        self.repository = repository
        self._storage_provider = storage_provider

    @property
    def storage_provider(self) -> FileStorageProvider:
        if self._storage_provider is None:
            self._storage_provider = build_storage_provider()
        return self._storage_provider

    def _extract_theory_answer_text(self, content: bytes, extension: str) -> tuple[str | None, str]:
        try:
            if extension in {"txt", "md"}:
                return content.decode("utf-8", errors="ignore"), "completed"

            if extension == "pdf":
                reader = PdfReader(BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return text, "completed"

            if extension in {"png", "jpg", "jpeg"}:
                try:
                    import pytesseract
                    from PIL import Image
                except Exception:
                    return None, "failed"
                image = Image.open(BytesIO(content))
                text = pytesseract.image_to_string(image)
                return text, "completed" if text else "failed"

            if extension == "docx":
                doc = Document(BytesIO(content))
                text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
                return text, "completed" if text else "failed"

            return None, "failed"
        except Exception:
            return None, "failed"

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
            raise bad_request(
                f"Only {len(selected_questions)} questions matched the selected filters, but {payload.total_questions} were requested",
                error_code="INSUFFICIENT_QUIZ_QUESTIONS",
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

        self._attach_questions_to_quiz(quiz=quiz, selected_questions=selected_questions)
        return self.repository.save_quiz(quiz)

    def _attach_questions_to_quiz(self, *, quiz: Quiz, selected_questions: list) -> None:
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

    def _normalize_question_type_mode(self, question_format: str) -> str | None:
        normalized = question_format.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in ["objective", "theory", "practical", "case_based"]:
            return normalized
        return None

    def list_quizzes(self, user_id: int, *, skip: int, limit: int) -> list[Quiz]:
        return self.repository.list_user_quizzes(user_id, skip=skip, limit=limit)

    def get_quiz(self, quiz_id: int, user_id: int) -> Quiz:
        quiz = self.repository.get_user_quiz(quiz_id, user_id)
        if not quiz:
            raise not_found("quiz", quiz_id)
        return quiz

    def get_attempt_by_id(self, attempt_id: int, user_id: int) -> QuizAttempt:
        attempt = self.repository.get_attempt_by_id(attempt_id, user_id)
        if attempt is None:
            raise not_found("attempt", attempt_id)
        return attempt

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
            raise bad_request(
                "selected_duration_minutes must be greater than 0",
                error_code="INVALID_ATTEMPT_DURATION",
            )

        cap = min(settings.MAX_ATTEMPT_DURATION_MINUTES, max(default_duration * 2, default_duration))
        if selected_duration_minutes > cap:
            raise bad_request(
                f"selected_duration_minutes exceeds the allowed cap of {cap} minutes",
                error_code="ATTEMPT_DURATION_EXCEEDS_CAP",
            )
        return selected_duration_minutes

    def start_attempt(self, quiz_id: int, user_id: int, selected_duration_minutes: int | None = None) -> QuizAttempt:
        quiz = self.get_quiz(quiz_id, user_id)
        latest = self.repository.get_latest_attempt(quiz_id, user_id)
        next_attempt_number = 1 if latest is None else latest.attempt_number + 1
        if next_attempt_number > quiz.max_attempts:
            raise bad_request(
                f"Quiz with id {quiz_id} allows at most {quiz.max_attempts} attempt(s)",
                error_code="MAX_ATTEMPTS_REACHED",
                resource="quiz",
                resource_id=quiz_id,
            )

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
            raise bad_request(
                f"Attempt with id {attempt.id} is not in progress",
                error_code="ATTEMPT_NOT_IN_PROGRESS",
                resource="attempt",
                resource_id=attempt.id,
            )

        quiz_question_map = {question.id: question for question in quiz.quiz_questions}
        for response_item in payload.responses:
            if response_item.quiz_question_id not in quiz_question_map:
                raise bad_request(
                    f"Quiz question with id {response_item.quiz_question_id} does not belong to quiz with id {quiz.id}",
                    error_code="QUIZ_QUESTION_NOT_IN_QUIZ",
                    resource="quiz_question",
                    resource_id=response_item.quiz_question_id,
                )

            existing = self.repository.find_response(
                attempt_id=attempt.id,
                quiz_question_id=response_item.quiz_question_id,
                user_id=user_id,
            )
            if existing:
                existing.selected_quiz_question_option_id = response_item.selected_quiz_question_option_id
                existing.answer_text = response_item.answer_text
                if response_item.answer_text is not None:
                    existing.answer_input_mode = "typed"
                self.repository.commit()
            else:
                response = QuizResponse(
                    attempt_id=attempt.id,
                    quiz_question_id=response_item.quiz_question_id,
                    user_id=user_id,
                    selected_quiz_question_option_id=response_item.selected_quiz_question_option_id,
                    answer_text=response_item.answer_text,
                    answer_input_mode="typed",
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
            raise not_found("attempt", attempt_id)
        return self._submit_for_attempt(quiz, user_id, attempt, payload)

    def submit_attempt_by_id(
        self,
        *,
        attempt_id: int,
        user_id: int,
        payload: QuizSubmitInput,
    ) -> QuizAttempt:
        attempt = self.get_attempt_by_id(attempt_id, user_id)
        quiz = self.get_quiz(attempt.quiz_id, user_id)
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
            raise bad_request(
                f"No in-progress attempt was found for quiz with id {quiz_id}",
                error_code="NO_IN_PROGRESS_ATTEMPT",
                resource="quiz",
                resource_id=quiz_id,
            )
        return quiz, attempt

    def get_in_progress_questions_with_responses(self, quiz_id: int, user_id: int):
        quiz, attempt = self.get_in_progress_questions(quiz_id, user_id)
        responses = {
            response.quiz_question_id: response
            for response in self.repository.list_responses_for_attempt(attempt.id, user_id)
        }
        return quiz, attempt, responses

    def get_attempt_questions(self, quiz_id: int, attempt_id: int, user_id: int):
        quiz = self.get_quiz(quiz_id, user_id)
        attempt = self.repository.get_attempt(quiz_id, attempt_id, user_id)
        if attempt is None:
            raise not_found("attempt", attempt_id)
        responses = {
            response.quiz_question_id: response
            for response in self.repository.list_responses_for_attempt(attempt_id, user_id)
        }
        return quiz, attempt, responses

    def get_attempt_questions_by_attempt_id(self, attempt_id: int, user_id: int):
        attempt = self.get_attempt_by_id(attempt_id, user_id)
        return self.get_attempt_questions(attempt.quiz_id, attempt_id, user_id)

    def upload_theory_answer(
        self,
        *,
        attempt_id: int,
        user_id: int,
        quiz_question_id: int,
        original_filename: str,
        content: bytes,
    ) -> QuizResponse:
        attempt = self.repository.get_attempt_by_id(attempt_id, user_id)
        if attempt is None:
            raise not_found("attempt", attempt_id)
        if attempt.status != QuizStatus.IN_PROGRESS.value:
            raise bad_request(
                f"Attempt with id {attempt_id} is not in progress",
                error_code="ATTEMPT_NOT_IN_PROGRESS",
                resource="attempt",
                resource_id=attempt_id,
            )

        quiz = self.repository.get_user_quiz(attempt.quiz_id, user_id)
        if quiz is None:
            raise not_found("quiz", attempt.quiz_id)

        question = next((item for item in quiz.quiz_questions if item.id == quiz_question_id), None)
        if question is None:
            raise not_found("quiz_question", quiz_question_id)
        if question.question_type == "objective":
            raise bad_request(
                f"Quiz question with id {quiz_question_id} is objective and does not accept theory uploads",
                error_code="OBJECTIVE_DOES_NOT_ACCEPT_UPLOAD",
                resource="quiz_question",
                resource_id=quiz_question_id,
            )

        extension = original_filename.split(".")[-1].lower() if "." in original_filename else ""
        if extension not in {"pdf", "png", "jpg", "jpeg", "txt", "md", "docx"}:
            raise bad_request(
                f"Unsupported theory answer file type '{extension or 'unknown'}'",
                error_code="UNSUPPORTED_THEORY_FILE_TYPE",
            )
        if len(content) > settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024:
            raise bad_request(
                f"File is too large. Maximum allowed size is {settings.MAX_UPLOAD_FILE_SIZE_MB}MB",
                error_code="THEORY_UPLOAD_TOO_LARGE",
            )

        stored = self.storage_provider.save(original_name=original_filename, content=content)
        extracted_text, extraction_status = self._extract_theory_answer_text(content, extension)

        response = self.repository.find_response(
            attempt_id=attempt_id,
            quiz_question_id=quiz_question_id,
            user_id=user_id,
        )
        if response is None:
            response = QuizResponse(
                attempt_id=attempt_id,
                quiz_question_id=quiz_question_id,
                user_id=user_id,
            )
        response.answer_input_mode = "upload"
        response.answer_text = extracted_text or response.answer_text
        response.answer_file_provider = stored.provider
        response.answer_file_bucket = stored.bucket
        response.answer_file_key = stored.key
        response.answer_file_path = stored.path
        response.answer_file_type = extension
        response.answer_file_size = len(content)
        response.answer_extracted_text = extracted_text
        response.answer_extraction_status = extraction_status
        return self.repository.upsert_response(response)

    def create_and_start_practice_from_assessment(
        self,
        *,
        assessment_id: int,
        user_id: int,
        desired_question_count: int,
        selected_topic_ids: list[int] | None,
        selected_duration_minutes: int | None,
        reveal_answers_post_submit: bool,
    ):
        assessment = self.repository.get_assessment(assessment_id)
        if assessment is None:
            raise not_found("assessment", assessment_id)

        topic_ids = selected_topic_ids or None
        question_type_mode = self._normalize_question_type_mode(assessment.question_format)

        available_count = self.repository.count_assessment_questions(
            assessment_id=assessment_id,
            topic_ids=topic_ids,
            question_type_mode=question_type_mode,
        )
        if desired_question_count > available_count:
            raise bad_request(
                f"Assessment with id {assessment_id} has only {available_count} eligible questions, but {desired_question_count} were requested",
                error_code="INSUFFICIENT_ASSESSMENT_QUESTIONS",
                resource="assessment",
                resource_id=assessment_id,
            )

        selected_questions = self.repository.select_assessment_questions(
            assessment_id=assessment_id,
            topic_ids=topic_ids,
            desired_count=desired_question_count,
            question_type_mode=question_type_mode,
        )
        if len(selected_questions) < desired_question_count:
            raise bad_request(
                f"Assessment with id {assessment_id} does not have enough questions for the selected topics and format",
                error_code="INSUFFICIENT_FILTERED_QUESTIONS",
                resource="assessment",
                resource_id=assessment_id,
            )

        label = assessment.year_label or "Past Questions"
        quiz = Quiz(
            user_id=user_id,
            title=f"{assessment.assessment_type} Practice ({label})",
            slug=generate_slug(f"{assessment.slug}-{user_id}-{now_utc().isoformat()}"),
            course_id=assessment.course_id,
            assessment_id=assessment.id,
            topic_id=topic_ids[0] if topic_ids and len(topic_ids) == 1 else None,
            academic_session_id=assessment.academic_session_id,
            semester_id=assessment.semester_id,
            question_source_mode="actual_only",
            question_type_mode=question_type_mode,
            total_questions=desired_question_count,
            max_attempts=1,
            reveal_answers_post_submit=reveal_answers_post_submit,
            status=QuizStatus.DRAFT.value,
        )
        self._attach_questions_to_quiz(quiz=quiz, selected_questions=selected_questions)
        quiz = self.repository.save_quiz(quiz)
        attempt = self.start_attempt(
            quiz_id=quiz.id,
            user_id=user_id,
            selected_duration_minutes=selected_duration_minutes,
        )
        return quiz, attempt, available_count

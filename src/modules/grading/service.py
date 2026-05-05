from fastapi import HTTPException, status

from src.common.enums import GradedBy, QuizStatus
from src.common.utils import now_utc
from src.modules.analytics.models import AttemptTopicMetric, TopicPerformance
from src.modules.analytics.repository import AnalyticsRepository
from src.modules.grading.ai_grader import TheoryAIGrader
from src.modules.grading.repository import GradingRepository
from src.modules.quizzes.models import QuizResult
from src.modules.quizzes.repository import QuizRepository


class GradingService:
    def __init__(
        self,
        grading_repository: GradingRepository,
        quiz_repository: QuizRepository,
        analytics_repository: AnalyticsRepository,
    ):
        self.grading_repository = grading_repository
        self.quiz_repository = quiz_repository
        self.analytics_repository = analytics_repository
        self.theory_grader = TheoryAIGrader()

    def _weakness_level(self, accuracy: float) -> str:
        if accuracy >= 70:
            return "low"
        if accuracy >= 40:
            return "medium"
        return "high"

    def grade_quiz(self, quiz_id: int, user_id: int, attempt_id: int) -> QuizResult:
        quiz = self.grading_repository.get_quiz_for_grading(quiz_id, user_id)
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        attempt = self.grading_repository.get_attempt(quiz_id, attempt_id, user_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        if attempt.status not in [QuizStatus.SUBMITTED.value, QuizStatus.GRADED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attempt must be submitted before grading",
            )

        existing_result = self.quiz_repository.get_result(quiz_id, user_id, attempt_id=attempt_id)
        if existing_result:
            return existing_result

        responses = {
            response.quiz_question_id: response
            for response in self.grading_repository.list_attempt_responses(attempt_id, user_id)
        }

        total_score = 0.0
        max_score = 0.0
        correct_count = 0
        wrong_count = 0
        unanswered_count = 0

        topic_stats: dict[int | None, dict[str, float]] = {}

        for quiz_question in quiz.quiz_questions:
            max_score += float(quiz_question.marks)
            response = responses.get(quiz_question.id)
            topic_id = quiz_question.question.topic_id if quiz_question.question else quiz.topic_id

            if response is None:
                unanswered_count += 1
                continue

            is_correct = False
            awarded = 0.0
            feedback = ""
            graded_by = GradedBy.AUTO.value

            if quiz_question.question_type == "objective":
                chosen = None
                if response.selected_quiz_question_option_id is not None:
                    chosen = next(
                        (item for item in quiz_question.options if item.id == response.selected_quiz_question_option_id),
                        None,
                    )
                if chosen and chosen.is_correct_snapshot:
                    is_correct = True
                    awarded = float(quiz_question.marks)
                    feedback = "Correct answer."
                else:
                    feedback = "Incorrect answer."
            else:
                question_text = quiz_question.question.question_text if quiz_question.question else quiz_question.question_snapshot_text
                marking_scheme = quiz_question.question.marking_scheme if quiz_question.question else ""
                model_solution = quiz_question.question.solution_text if quiz_question.question else ""
                student_answer = (response.answer_extracted_text or response.answer_text or "").strip()
                ai_grade = self.theory_grader.grade_theory_answer(
                    question_text=question_text,
                    marking_scheme=marking_scheme or "",
                    model_solution=model_solution or "",
                    student_answer=student_answer,
                    marks=float(quiz_question.marks),
                )
                awarded = round(float(quiz_question.marks) * ai_grade.score_ratio, 2)
                is_correct = ai_grade.score_ratio >= 0.7
                feedback = ai_grade.feedback
                graded_by = GradedBy.AI.value
                response.grading_strengths = ai_grade.strengths
                response.grading_missing_points = ai_grade.missing_points
                response.grading_confidence = ai_grade.confidence
                response.grading_explanation = ai_grade.explanation

            response.is_correct = is_correct
            response.score_awarded = awarded
            response.feedback = feedback
            response.graded_by = graded_by
            response.graded_at = now_utc()

            total_score += awarded
            if topic_id not in topic_stats:
                topic_stats[topic_id] = {"attempted": 0, "correct": 0, "score": 0.0}
            topic_stats[topic_id]["attempted"] += 1
            topic_stats[topic_id]["score"] += awarded
            if is_correct:
                correct_count += 1
                topic_stats[topic_id]["correct"] += 1
            else:
                wrong_count += 1

        percentage = (total_score / max_score * 100) if max_score > 0 else 0.0

        result = QuizResult(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            user_id=user_id,
            total_score=total_score,
            max_score=max_score,
            percentage_score=percentage,
            correct_count=correct_count,
            wrong_count=wrong_count,
            unanswered_count=unanswered_count,
        )
        self.quiz_repository.save_result(result)

        attempt.status = QuizStatus.GRADED.value
        attempt.graded_at = now_utc()
        quiz.status = QuizStatus.GRADED.value
        self.grading_repository.commit()

        for topic_id, stats in topic_stats.items():
            topic_attempted = int(stats["attempted"])
            topic_correct = int(stats["correct"])
            topic_score = float(stats["score"])

            topic_record = self.analytics_repository.get_topic_performance(
                user_id=user_id,
                course_id=quiz.course_id,
                topic_id=topic_id,
                academic_session_id=quiz.academic_session_id,
            )

            if topic_record is None:
                topic_record = TopicPerformance(
                    user_id=user_id,
                    course_id=quiz.course_id,
                    topic_id=topic_id,
                    academic_session_id=quiz.academic_session_id,
                    questions_attempted=0,
                    questions_correct=0,
                    average_score=0,
                    weakness_level="high",
                    last_updated=now_utc(),
                )

            topic_record.questions_attempted += topic_attempted
            topic_record.questions_correct += topic_correct
            accuracy = (
                (topic_record.questions_correct / topic_record.questions_attempted) * 100
                if topic_record.questions_attempted > 0
                else 0
            )
            topic_record.average_score = accuracy
            topic_record.weakness_level = self._weakness_level(accuracy)
            topic_record.last_updated = now_utc()
            self.analytics_repository.save_topic_performance(topic_record)

            self.analytics_repository.create_attempt_metric(
                AttemptTopicMetric(
                    attempt_id=attempt.id,
                    user_id=user_id,
                    course_id=quiz.course_id,
                    topic_id=topic_id,
                    academic_session_id=quiz.academic_session_id,
                    attempted_count=topic_attempted,
                    correct_count=topic_correct,
                    score=topic_score,
                    created_at=now_utc(),
                )
            )

        return result

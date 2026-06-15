from src.common.errors import not_found
from src.common.utils import generate_slug
from src.core.config import settings
from src.modules.academic.models import Assessment
from src.modules.assessments.repository import AssessmentRepository
from src.modules.assessments.schemas import AssessmentCreate


class AssessmentService:
    def __init__(self, repository: AssessmentRepository):
        self.repository = repository

    def create_assessment(self, payload: AssessmentCreate) -> Assessment:
        course = self.repository.get_course(payload.course_id)
        if course is None:
            raise not_found("course", payload.course_id)

        session = self.repository.get_session(payload.academic_session_id)
        if session is None:
            raise not_found("academic_session", payload.academic_session_id)

        if payload.semester_id is not None:
            semester = self.repository.get_semester(payload.semester_id)
            if semester is None:
                raise not_found("semester", payload.semester_id)

        year_label = payload.year_label or session.name
        slug = generate_slug(
            f"{payload.course_id}-{payload.academic_session_id}-{payload.semester_id}-{payload.assessment_type}-{payload.question_format}-{year_label}"
        )
        return self.repository.create(
            Assessment(
                course_id=course.id,
                academic_session_id=payload.academic_session_id,
                semester_id=payload.semester_id,
                assessment_type=payload.assessment_type,
                question_format=payload.question_format,
                default_duration_minutes=payload.default_duration_minutes,
                year_label=year_label,
                slug=slug,
            )
        )

    def list_assessments(
        self,
        *,
        course_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        assessment_type: str | None,
        source_type: str | None,
        created_by_user_id: int | None,
        skip: int,
        limit: int,
    ) -> list[dict]:
        rows = self.repository.list_with_counts(
            course_id=course_id,
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            assessment_type=assessment_type,
            source_type=source_type,
            created_by_user_id=created_by_user_id,
            skip=skip,
            limit=limit,
        )
        output: list[dict] = []
        for assessment, total_questions in rows:
            title_parts = [assessment.assessment_type]
            if assessment.year_label:
                title_parts.insert(0, assessment.year_label)
            title_parts.append(assessment.question_format)
            output.append(
                {
                    "id": assessment.id,
                    "slug": assessment.slug,
                    "title_label": " • ".join(title_parts),
                    "course_id": assessment.course_id,
                    "academic_session_id": assessment.academic_session_id,
                    "semester_id": assessment.semester_id,
                    "year_label": assessment.year_label,
                    "assessment_type": assessment.assessment_type,
                    "question_format": assessment.question_format,
                    "source_type": assessment.source_type,
                    "created_by_user_id": assessment.created_by_user_id,
                    "default_duration_minutes": assessment.default_duration_minutes,
                    "total_available_questions": int(total_questions),
                }
            )
        return output

    def get_assessment(self, assessment_id: int) -> Assessment:
        assessment = self.repository.get(assessment_id)
        if assessment is None:
            raise not_found("assessment", assessment_id)
        return assessment

    def list_assessment_questions(
        self,
        *,
        assessment_id: int,
        question_type: str | None,
        source_type: str | None,
        skip: int,
        limit: int,
    ):
        self.get_assessment(assessment_id)
        return self.repository.list_questions(
            assessment_id=assessment_id,
            question_type=question_type,
            source_type=source_type,
            skip=skip,
            limit=limit,
        )

    def get_practice_config(self, assessment_id: int) -> dict:
        assessment = self.get_assessment(assessment_id)
        total_questions = self.repository.count_questions(assessment_id=assessment.id)
        topics = self.repository.list_topics_for_assessment(assessment.id)

        title_parts = [assessment.assessment_type]
        if assessment.year_label:
            title_parts.insert(0, assessment.year_label)
        title_parts.append(assessment.question_format)

        max_duration = min(settings.MAX_ATTEMPT_DURATION_MINUTES, max(assessment.default_duration_minutes * 2, assessment.default_duration_minutes))
        return {
            "assessment": {
                "id": assessment.id,
                "slug": assessment.slug,
                "title_label": " • ".join(title_parts),
                "course_id": assessment.course_id,
                "academic_session_id": assessment.academic_session_id,
                "semester_id": assessment.semester_id,
                "year_label": assessment.year_label,
                "assessment_type": assessment.assessment_type,
                "question_format": assessment.question_format,
                "source_type": assessment.source_type,
                "created_by_user_id": assessment.created_by_user_id,
                "default_duration_minutes": assessment.default_duration_minutes,
                "total_available_questions": total_questions,
            },
            "selectable_topics": [
                {"id": topic.id, "name": topic.name, "slug": topic.slug}
                for topic in topics
            ],
            "constraints": {
                "min_questions": 1,
                "max_questions": total_questions,
                "min_duration_minutes": 1,
                "max_duration_minutes": max_duration,
            },
        }

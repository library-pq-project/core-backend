from fastapi import HTTPException, status
from sqlalchemy import update

from src.common.utils import generate_slug
from src.modules.academic.models import (
    AcademicCalendarState,
    AcademicSession,
    Assessment,
    Program,
    ProgramCourseOffering,
    Semester,
)
from src.modules.academic.repository import AcademicRepository
from src.modules.academic.schemas import (
    AcademicSessionCreate,
    ActiveCalendarUpdate,
    AssessmentCreate,
    ProgramCourseOfferingCreate,
    ProgramCreate,
    SemesterCreate,
)
from src.modules.auth.models import User
from src.modules.questions.models import Question


class AcademicService:
    def __init__(self, repository: AcademicRepository):
        self.repository = repository

    def create_session(self, payload: AcademicSessionCreate) -> AcademicSession:
        return self.repository.create(
            AcademicSession(name=payload.name, slug=generate_slug(payload.name), is_active=False)
        )

    def create_semester(self, payload: SemesterCreate) -> Semester:
        return self.repository.create(
            Semester(name=payload.name, slug=generate_slug(payload.name), is_active=False)
        )

    def create_program(self, payload: ProgramCreate) -> Program:
        return self.repository.create(
            Program(
                code=payload.code,
                name=payload.name,
                slug=generate_slug(f"{payload.code}-{payload.name}"),
                description=payload.description,
            )
        )

    def set_active_calendar(self, payload: ActiveCalendarUpdate):
        session = self.repository.get_session(payload.academic_session_id)
        semester = self.repository.get_semester(payload.semester_id)
        if not session or not semester:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session or semester not found")

        active = self.repository.get_active_calendar()
        if active is None:
            active = AcademicCalendarState(
                academic_session_id=payload.academic_session_id,
                semester_id=payload.semester_id,
            )
            self.repository.create(active)
        else:
            active.academic_session_id = payload.academic_session_id
            active.semester_id = payload.semester_id
            self.repository.save(active)

        db = self.repository.db
        db.execute(update(AcademicSession).values(is_active=False))
        db.execute(update(Semester).values(is_active=False))
        db.execute(
            update(AcademicSession)
            .where(AcademicSession.id == payload.academic_session_id)
            .values(is_active=True)
        )
        db.execute(update(Semester).where(Semester.id == payload.semester_id).values(is_active=True))
        db.execute(update(User).where(User.role == "student").values(profile_update_required=True))
        db.commit()
        return active

    def create_offering(self, payload: ProgramCourseOfferingCreate) -> ProgramCourseOffering:
        return self.repository.create(
            ProgramCourseOffering(
                program_id=payload.program_id,
                course_id=payload.course_id,
                level=payload.level,
                academic_session_id=payload.academic_session_id,
                semester_id=payload.semester_id,
            )
        )

    def list_sessions(self, *, skip: int, limit: int):
        return self.repository.list_sessions(skip=skip, limit=limit)

    def list_semesters(self, *, skip: int, limit: int):
        return self.repository.list_semesters(skip=skip, limit=limit)

    def list_programs(self, *, skip: int, limit: int):
        return self.repository.list_programs(skip=skip, limit=limit)

    def list_offerings(
        self,
        *,
        program_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        level: str | None,
        skip: int,
        limit: int,
    ):
        return self.repository.list_offerings(
            program_id=program_id,
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            level=level,
            skip=skip,
            limit=limit,
        )

    def create_assessment(self, payload: AssessmentCreate) -> Assessment:
        slug = generate_slug(
            f"{payload.course_id}-{payload.academic_session_id}-{payload.semester_id}-{payload.assessment_type}-{payload.question_format}-{payload.year_label or ''}"
        )
        return self.repository.create(
            Assessment(
                course_id=payload.course_id,
                academic_session_id=payload.academic_session_id,
                semester_id=payload.semester_id,
                assessment_type=payload.assessment_type,
                question_format=payload.question_format,
                default_duration_minutes=payload.default_duration_minutes,
                year_label=payload.year_label,
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
        skip: int,
        limit: int,
    ):
        return self.repository.list_assessments(
            course_id=course_id,
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            assessment_type=assessment_type,
            skip=skip,
            limit=limit,
        )

    def get_active_calendar(self) -> AcademicCalendarState:
        active = self.repository.get_active_calendar()
        if not active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active calendar is not configured")
        return active

    def list_student_offered_courses(self, *, student: User, skip: int, limit: int):
        if student.program_id is None or student.current_level is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student profile is incomplete. Update program and level first.",
            )
        active = self.get_active_calendar()
        return self.repository.list_offered_courses_for_student(
            student=student,
            academic_session_id=active.academic_session_id,
            semester_id=active.semester_id,
            skip=skip,
            limit=limit,
        )

    def list_questions_in_assessment(
        self,
        *,
        assessment_id: int,
        question_type: str | None,
        source_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Question]:
        assessment = self.repository.get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        return self.repository.list_assessment_questions(
            assessment_id=assessment_id,
            question_type=question_type,
            source_type=source_type,
            skip=skip,
            limit=limit,
        )

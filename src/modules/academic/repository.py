from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.academic.models import (
    AcademicCalendarState,
    AcademicSession,
    Assessment,
    Program,
    ProgramCourseOffering,
    Semester,
)
from src.modules.auth.models import User
from src.modules.courses.models import Course


class AcademicRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_sessions(self, *, skip: int, limit: int) -> list[AcademicSession]:
        stmt = select(AcademicSession).order_by(AcademicSession.name.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def list_semesters(self, *, skip: int, limit: int) -> list[Semester]:
        stmt = select(Semester).order_by(Semester.name).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def list_programs(self, *, skip: int, limit: int) -> list[Program]:
        stmt = select(Program).order_by(Program.name).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def list_offerings(
        self,
        *,
        program_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        level: str | None,
        skip: int,
        limit: int,
    ) -> list[ProgramCourseOffering]:
        stmt = select(ProgramCourseOffering)
        if program_id is not None:
            stmt = stmt.where(ProgramCourseOffering.program_id == program_id)
        if academic_session_id is not None:
            stmt = stmt.where(ProgramCourseOffering.academic_session_id == academic_session_id)
        if semester_id is not None:
            stmt = stmt.where(ProgramCourseOffering.semester_id == semester_id)
        if level is not None:
            stmt = stmt.where(ProgramCourseOffering.level == level)
        stmt = stmt.order_by(ProgramCourseOffering.id.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def list_assessments(
        self,
        *,
        course_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        assessment_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Assessment]:
        stmt = select(Assessment)
        if course_id is not None:
            stmt = stmt.where(Assessment.course_id == course_id)
        if academic_session_id is not None:
            stmt = stmt.where(Assessment.academic_session_id == academic_session_id)
        if semester_id is not None:
            stmt = stmt.where(Assessment.semester_id == semester_id)
        if assessment_type is not None:
            stmt = stmt.where(Assessment.assessment_type == assessment_type)
        stmt = stmt.order_by(Assessment.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_session(self, session_id: int) -> AcademicSession | None:
        return self.db.get(AcademicSession, session_id)

    def get_semester(self, semester_id: int) -> Semester | None:
        return self.db.get(Semester, semester_id)

    def get_program(self, program_id: int) -> Program | None:
        return self.db.get(Program, program_id)

    def get_active_calendar(self) -> AcademicCalendarState | None:
        return self.db.scalar(select(AcademicCalendarState).order_by(AcademicCalendarState.id.asc()))

    def save(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_assessment(self, assessment_id: int) -> Assessment | None:
        return self.db.get(Assessment, assessment_id)

    def list_offered_courses_for_student(
        self,
        *,
        student: User,
        academic_session_id: int,
        semester_id: int,
        skip: int,
        limit: int,
    ) -> list[Course]:
        stmt = (
            select(Course)
            .join(ProgramCourseOffering, ProgramCourseOffering.course_id == Course.id)
            .where(
                ProgramCourseOffering.program_id == student.program_id,
                ProgramCourseOffering.level == student.current_level,
                ProgramCourseOffering.academic_session_id == academic_session_id,
                ProgramCourseOffering.semester_id == semester_id,
            )
            .order_by(Course.code)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

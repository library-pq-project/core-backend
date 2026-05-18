from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.common.utils import generate_slug
from src.core.security import hash_password
from src.modules.academic.models import AcademicCalendarState, AcademicSession, Assessment, Program, Semester
from src.modules.auth.models import User
from src.modules.courses.models import Course
from src.modules.topics.models import Topic


def _sync_pk_sequence(db: Session, table_name: str) -> None:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    # table_name is only used internally with trusted constant values in this module.
    db.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
        )
    )


def ensure_prototype_user_with_prerequisites(db: Session, *, user_id: int, role: str = "admin") -> User:
    created_user = False
    program = db.scalar(select(Program).where(Program.code == "PROTO-CSE"))
    if program is None:
        program = Program(
            code="PROTO-CSE",
            name="Prototype Computer Science",
            slug=generate_slug("prototype-computer-science"),
            description="Auto-bootstraped program for local prototype mode",
            is_active=True,
        )
        db.add(program)
        db.flush()

    session = db.scalar(select(AcademicSession).where(AcademicSession.name == "2025/2026"))
    if session is None:
        session = AcademicSession(name="2025/2026", slug=generate_slug("2025-2026"), is_active=True)
        db.add(session)
        db.flush()

    semester = db.scalar(select(Semester).where(Semester.name == "First"))
    if semester is None:
        semester = Semester(name="First", slug=generate_slug("First"), is_active=True)
        db.add(semester)
        db.flush()

    active = db.scalar(select(AcademicCalendarState).order_by(AcademicCalendarState.id.asc()))
    if active is None:
        active = AcademicCalendarState(academic_session_id=session.id, semester_id=semester.id)
        db.add(active)
    else:
        active.academic_session_id = session.id
        active.semester_id = semester.id

    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            first_name="Prototype",
            last_name="User",
            email=f"prototype{user_id}@local.dev",
            password_hash=hash_password("prototype123"),
            role=role,
            program_id=program.id,
            current_level="400",
            profile_update_required=False,
            is_active=True,
        )
        db.add(user)
        created_user = True
    else:
        user.role = role
        user.program_id = user.program_id or program.id
        user.current_level = user.current_level or "400"
        user.is_active = True
        user.profile_update_required = False

    db.flush()
    if created_user:
        _sync_pk_sequence(db, "users")
    db.commit()
    db.refresh(user)
    return user


def ensure_prototype_course(db: Session, *, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is not None:
        return course

    code = f"PROTO{course_id}"
    course = Course(
        id=course_id,
        code=code,
        slug=generate_slug(code),
        title=f"Prototype Course {course_id}",
        description="Auto-created course for prototype AI generation",
        level="400",
        semester="First",
    )
    db.add(course)
    db.flush()
    _sync_pk_sequence(db, "courses")
    db.commit()
    db.refresh(course)
    return course


def ensure_prototype_topic(db: Session, *, course_id: int, topic_id: int | None) -> Topic | None:
    if topic_id is None:
        return None
    topic = db.get(Topic, topic_id)
    if topic is not None:
        return topic

    topic = Topic(
        id=topic_id,
        course_id=course_id,
        name=f"Prototype Topic {topic_id}",
        slug=generate_slug(f"prototype-topic-{topic_id}"),
        description="Auto-created topic for prototype mode",
    )
    db.add(topic)
    db.flush()
    _sync_pk_sequence(db, "topics")
    db.commit()
    db.refresh(topic)
    return topic


def ensure_prototype_assessment(
    db: Session,
    *,
    assessment_id: int | None,
    course_id: int,
    question_format: str,
) -> Assessment | None:
    if assessment_id is None:
        return None

    assessment = db.get(Assessment, assessment_id)
    if assessment is not None:
        return assessment

    session = db.scalar(select(AcademicSession).where(AcademicSession.name == "2025/2026"))
    semester = db.scalar(select(Semester).where(Semester.name == "First"))
    if session is None:
        session = AcademicSession(name="2025/2026", slug=generate_slug("2025-2026"), is_active=True)
        db.add(session)
        db.flush()
    if semester is None:
        semester = Semester(name="First", slug=generate_slug("First"), is_active=True)
        db.add(semester)
        db.flush()

    assessment = Assessment(
        id=assessment_id,
        course_id=course_id,
        academic_session_id=session.id,
        semester_id=semester.id,
        assessment_type="Prototype",
        question_format=question_format,
        default_duration_minutes=60,
        year_label="2025/2026",
        slug=generate_slug(f"prototype-assessment-{assessment_id}-{course_id}"),
    )
    db.add(assessment)
    db.flush()
    _sync_pk_sequence(db, "assessments")
    db.commit()
    db.refresh(assessment)
    return assessment

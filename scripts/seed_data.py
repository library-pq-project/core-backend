import argparse
import random

from sqlalchemy import delete, select

from src.common.utils import generate_slug
from src.core.security import hash_password
from src.db import models as _models  # noqa: F401  # Ensure all ORM models are registered
from src.db.session import SessionLocal
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
from src.modules.questions.models import Question, QuestionOption
from src.modules.topics.models import Topic

DEFAULT_TOPICS = [
    "Search Algorithms",
    "Knowledge Representation",
    "Machine Learning Basics",
    "Constraint Satisfaction",
    "Game Playing",
    "Expert Systems",
]


def _get_or_create_session(db, name: str) -> AcademicSession:
    session = db.scalar(select(AcademicSession).where(AcademicSession.name == name))
    if session:
        return session
    session = AcademicSession(name=name, slug=generate_slug(name.replace("/", "-")), is_active=True)
    db.add(session)
    db.flush()
    return session


def _get_or_create_semester(db, name: str) -> Semester:
    semester = db.scalar(select(Semester).where(Semester.name == name))
    if semester:
        return semester
    semester = Semester(name=name, slug=generate_slug(name), is_active=True)
    db.add(semester)
    db.flush()
    return semester


def _ensure_active_calendar(db, session_id: int, semester_id: int) -> None:
    active = db.scalar(select(AcademicCalendarState).order_by(AcademicCalendarState.id.asc()))
    if active is None:
        db.add(AcademicCalendarState(academic_session_id=session_id, semester_id=semester_id))
    else:
        active.academic_session_id = session_id
        active.semester_id = semester_id


def _get_or_create_program(db) -> Program:
    program = db.scalar(select(Program).where(Program.code == "CSE"))
    if program:
        return program
    program = Program(
        code="CSE",
        name="Computer Science and Engineering",
        slug=generate_slug("CSE Computer Science and Engineering"),
        description="Undergraduate CSE track",
    )
    db.add(program)
    db.flush()
    return program


def _get_or_create_user(
    db,
    *,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    role: str,
    program_id: int | None = None,
    current_level: str | None = None,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.program_id = program_id
        user.current_level = current_level
        user.is_active = True
        user.profile_update_required = False
        if not user.password_hash:
            user.password_hash = hash_password(password)
        return user

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        program_id=program_id,
        current_level=current_level,
        profile_update_required=False,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_course(db, *, code: str, title: str, description: str, level: str, semester: str) -> Course:
    semester_record = _get_or_create_semester(db, semester)
    course = db.scalar(select(Course).where(Course.code == code))
    if course:
        course.title = title
        course.description = description
        course.level = level
        course.semester = semester
        course.semester_id = semester_record.id
        return course

    course = Course(
        code=code,
        slug=generate_slug(code),
        title=title,
        description=description,
        level=level,
        semester=semester,
        semester_id=semester_record.id,
    )
    db.add(course)
    db.flush()
    return course


def _ensure_offering(db, *, program_id: int, course_id: int, level: str, session_id: int, semester_id: int) -> None:
    exists = db.scalar(
        select(ProgramCourseOffering).where(
            ProgramCourseOffering.program_id == program_id,
            ProgramCourseOffering.course_id == course_id,
            ProgramCourseOffering.level == level,
            ProgramCourseOffering.academic_session_id == session_id,
            ProgramCourseOffering.semester_id == semester_id,
        )
    )
    if exists:
        return

    db.add(
        ProgramCourseOffering(
            program_id=program_id,
            course_id=course_id,
            level=level,
            academic_session_id=session_id,
            semester_id=semester_id,
        )
    )


def _ensure_topics(db, *, course_id: int, topic_names: list[str]) -> list[Topic]:
    topics: list[Topic] = []
    for name in topic_names:
        clean = name.strip()
        if not clean:
            continue
        topic = db.scalar(select(Topic).where(Topic.course_id == course_id, Topic.name == clean))
        if not topic:
            topic = Topic(
                course_id=course_id,
                name=clean,
                slug=generate_slug(clean),
                description=f"{clean} for seeded practice questions",
            )
            db.add(topic)
            db.flush()
        topics.append(topic)
    return topics


def _get_or_create_assessment(
    db,
    *,
    course_id: int,
    session_id: int,
    semester_id: int,
    assessment_type: str,
    question_format: str,
    year_label: str,
) -> Assessment:
    slug = generate_slug(f"{course_id}-{year_label}-{assessment_type}-{question_format}")
    assessment = db.scalar(select(Assessment).where(Assessment.slug == slug))
    if assessment:
        assessment.default_duration_minutes = assessment.default_duration_minutes or 60
        return assessment

    assessment = Assessment(
        course_id=course_id,
        academic_session_id=session_id,
        semester_id=semester_id,
        assessment_type=assessment_type,
        question_format=question_format,
        year_label=year_label,
        default_duration_minutes=60,
        slug=slug,
    )
    db.add(assessment)
    db.flush()
    return assessment


def _create_objective_question(
    *,
    index: int,
    course_id: int,
    topic_id: int,
    assessment_id: int,
    source_type: str,
    difficulty: str,
) -> Question:
    q = Question(
        assessment_id=assessment_id,
        course_id=course_id,
        topic_id=topic_id,
        question_text=f"Seeded objective question {index}: Select the most appropriate concept for scenario {index}.",
        source_text=f"Seeded objective question {index}: Select the most appropriate concept for scenario {index}.",
        content_format="plain_text",
        question_type="objective",
        source_type=source_type,
        difficulty_level=difficulty,
        mark_allocation=2,
        marking_scheme="2 marks for selecting the most accurate option.",
        solution_text="Option C",
        explanation="Option C best fits the scenario assumptions.",
        is_active=True,
    )
    q.options = [
        QuestionOption(option_text=f"Option A for question {index}", is_correct=False, position=1),
        QuestionOption(option_text=f"Option B for question {index}", is_correct=False, position=2),
        QuestionOption(option_text=f"Option C for question {index}", is_correct=True, position=3),
        QuestionOption(option_text=f"Option D for question {index}", is_correct=False, position=4),
    ]
    return q


def _create_theory_question(
    *,
    index: int,
    course_id: int,
    topic_id: int,
    assessment_id: int,
    source_type: str,
    difficulty: str,
) -> Question:
    prompt = f"Seeded theory question {index}: Explain the core principle and give one practical example."
    return Question(
        assessment_id=assessment_id,
        course_id=course_id,
        topic_id=topic_id,
        question_text=prompt,
        source_text=prompt,
        content_format="markdown_latex",
        question_type="theory",
        source_type=source_type,
        difficulty_level=difficulty,
        mark_allocation=5,
        marking_scheme="5 marks: definition (2), explanation (2), practical example (1).",
        solution_text="Expected answer covers principle, mechanism, and one valid example.",
        explanation="Theory grading should reward conceptual clarity and relevance.",
        is_active=True,
    )


def _reset_all(db) -> None:
    db.execute(delete(QuestionOption))
    db.execute(delete(Question))
    db.execute(delete(Assessment))
    db.execute(delete(ProgramCourseOffering))
    db.execute(delete(AcademicCalendarState))
    db.execute(delete(Topic))
    db.execute(delete(Course))
    db.execute(delete(User))
    db.execute(delete(Program))
    db.execute(delete(Semester))
    db.execute(delete(AcademicSession))
    db.commit()


def seed(args) -> None:
    db = SessionLocal()
    try:
        if args.reset:
            _reset_all(db)

        session = _get_or_create_session(db, args.session_name)
        semester = _get_or_create_semester(db, args.semester_name)
        _ensure_active_calendar(db, session.id, semester.id)

        program = _get_or_create_program(db)
        _get_or_create_user(
            db,
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="admin123",
            role="admin",
        )
        _get_or_create_user(
            db,
            email="raphael@example.com",
            first_name="Raphael",
            last_name="Student",
            password="password123",
            role="student",
            program_id=program.id,
            current_level=args.level,
        )

        course = _get_or_create_course(
            db,
            code=args.course_code,
            title=args.course_title,
            description=args.course_description,
            level=args.level,
            semester=args.semester_name,
        )

        _ensure_offering(
            db,
            program_id=program.id,
            course_id=course.id,
            level=args.level,
            session_id=session.id,
            semester_id=semester.id,
        )

        topics = _ensure_topics(db, course_id=course.id, topic_names=args.topics)
        if not topics:
            raise ValueError("At least one topic is required to seed questions.")

        assessment = _get_or_create_assessment(
            db,
            course_id=course.id,
            session_id=session.id,
            semester_id=semester.id,
            assessment_type=args.assessment_type,
            question_format=args.question_format,
            year_label=args.year_label,
        )

        difficulties = ["easy", "medium", "hard"]
        questions: list[Question] = []
        for index in range(1, args.question_count + 1):
            topic = random.choice(topics)
            difficulty = difficulties[index % len(difficulties)]

            question_type = args.question_type
            if question_type == "mixed":
                question_type = "objective" if index % 2 else "theory"

            if question_type == "objective":
                q = _create_objective_question(
                    index=index,
                    course_id=course.id,
                    topic_id=topic.id,
                    assessment_id=assessment.id,
                    source_type=args.source_type,
                    difficulty=difficulty,
                )
            else:
                q = _create_theory_question(
                    index=index,
                    course_id=course.id,
                    topic_id=topic.id,
                    assessment_id=assessment.id,
                    source_type=args.source_type,
                    difficulty=difficulty,
                )
            questions.append(q)

        db.add_all(questions)
        db.commit()

        print("Seed completed successfully.")
        print(f"Course: {course.code} - {course.title}")
        print(f"Assessment: {assessment.assessment_type} ({assessment.question_format})")
        print(f"Questions added: {len(questions)}")
        print("Admin login: admin@example.com / admin123")
        print("Student login: raphael@example.com / password123")
    finally:
        db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Seed exam prep backend data")
    parser.add_argument("--reset", action="store_true", help="Delete existing seeded entities before inserting new data")
    parser.add_argument("--course-code", default="CSC411")
    parser.add_argument("--course-title", default="Artificial Intelligence")
    parser.add_argument("--course-description", default="Introductory AI course")
    parser.add_argument("--level", default="400")
    parser.add_argument("--session-name", default="2024/2025")
    parser.add_argument("--semester-name", default="First")
    parser.add_argument("--year-label", default="2024/2025")
    parser.add_argument("--assessment-type", default="Test1")
    parser.add_argument("--question-format", default="Objective")
    parser.add_argument("--source-type", default="actual", choices=["actual", "ai_generated"])
    parser.add_argument("--question-type", default="mixed", choices=["objective", "theory", "mixed"])
    parser.add_argument("--question-count", type=int, default=200)
    parser.add_argument(
        "--topics",
        nargs="+",
        default=DEFAULT_TOPICS,
        help="Space-separated topic names, e.g. --topics 'Search Algorithms' 'Game Playing'",
    )
    return parser.parse_args()


if __name__ == "__main__":
    seed(parse_args())

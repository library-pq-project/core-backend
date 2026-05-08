from sqlalchemy import delete

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


def seed() -> None:
    db = SessionLocal()
    try:
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

        session = AcademicSession(name="2024/2025", slug=generate_slug("2024-2025"), is_active=True)
        semester = Semester(name="First", slug=generate_slug("First"), is_active=True)
        db.add_all([session, semester])
        db.flush()

        db.add(
            AcademicCalendarState(
                academic_session_id=session.id,
                semester_id=semester.id,
            )
        )

        program = Program(
            code="CSE",
            name="Computer Science and Engineering",
            slug=generate_slug("CSE Computer Science and Engineering"),
            description="Undergraduate CSE track",
        )
        db.add(program)
        db.flush()

        admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        student = User(
            first_name="Raphael",
            last_name="Student",
            email="raphael@example.com",
            password_hash=hash_password("password123"),
            role="student",
            program_id=program.id,
            current_level="400",
            profile_update_required=False,
        )

        course = Course(
            code="CSC411",
            slug=generate_slug("CSC411"),
            title="Artificial Intelligence",
            description="Introductory AI course",
            level="400",
            semester="First",
        )
        db.add(course)
        db.flush()

        db.add(
            ProgramCourseOffering(
                program_id=program.id,
                course_id=course.id,
                level="400",
                academic_session_id=session.id,
                semester_id=semester.id,
            )
        )

        topic = Topic(
            course_id=course.id,
            name="Search Algorithms",
            slug=generate_slug("Search Algorithms"),
            description="BFS, DFS, A*",
        )
        db.add(topic)
        db.flush()

        assessment = Assessment(
            course_id=course.id,
            academic_session_id=session.id,
            semester_id=semester.id,
            assessment_type="Test1",
            question_format="Objective",
            year_label="2024/2025",
            slug=generate_slug("CSC411 2024/2025 Test1 Objective"),
        )
        db.add(assessment)
        db.flush()

        question = Question(
            assessment_id=assessment.id,
            course_id=course.id,
            topic_id=topic.id,
            question_text="Which algorithm guarantees optimality with admissible heuristics?",
            question_type="objective",
            source_type="actual",
            difficulty_level="medium",
            mark_allocation=2,
            solution_text="A*",
            explanation="A* is optimal when heuristic is admissible.",
            is_active=True,
        )
        question.options = [
            QuestionOption(option_text="DFS", is_correct=False, position=1),
            QuestionOption(option_text="BFS", is_correct=False, position=2),
            QuestionOption(option_text="A*", is_correct=True, position=3),
            QuestionOption(option_text="Greedy Best-First", is_correct=False, position=4),
        ]

        db.add_all([admin, student, question])
        db.commit()
        print("Seed data inserted.")
        print("Admin login: admin@example.com / admin123")
        print("Student login: raphael@example.com / password123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

from sqlalchemy import delete

from src.common.utils import generate_slug
from src.core.security import hash_password
from src.db.session import SessionLocal
from src.modules.auth.models import User
from src.modules.courses.models import Course
from src.modules.questions.models import Question, QuestionOption
from src.modules.topics.models import Topic


def seed() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(QuestionOption))
        db.execute(delete(Question))
        db.execute(delete(Topic))
        db.execute(delete(Course))
        db.execute(delete(User))
        db.commit()

        user = User(
            first_name="Raphael",
            last_name="Student",
            email="raphael@example.com",
            password_hash=hash_password("password123"),
        )

        course = Course(
            code="CSC411",
            slug=generate_slug("CSC411"),
            title="Artificial Intelligence",
            description="Introductory AI course",
            level="400",
            semester="First",
        )

        topic = Topic(
            course=course,
            name="Search Algorithms",
            slug=generate_slug("Search Algorithms"),
            description="BFS, DFS, A*",
        )

        question = Question(
            course=course,
            topic=topic,
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

        db.add_all([user, course, topic, question])
        db.commit()
        print("Seed data inserted.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

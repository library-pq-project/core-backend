from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    question_source_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    question_type_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="quizzes")
    quiz_questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    result = relationship("QuizResult", back_populates="quiz", uselist=False, cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("quiz_id", "sequence_number", name="uq_quiz_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question_snapshot_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    marks: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="quiz_questions")
    question = relationship("Question")
    options = relationship("QuizQuestionOption", back_populates="quiz_question", cascade="all, delete-orphan")
    responses = relationship("QuizResponse", back_populates="quiz_question", cascade="all, delete-orphan")


class QuizQuestionOption(Base):
    __tablename__ = "quiz_question_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_question_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    question_option_id: Mapped[int] = mapped_column(
        ForeignKey("question_options.id", ondelete="CASCADE"), nullable=False
    )
    option_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct_snapshot: Mapped[bool] = mapped_column(nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)

    quiz_question = relationship("QuizQuestion", back_populates="options")


class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_question_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    selected_quiz_question_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("quiz_question_options.id", ondelete="SET NULL"), nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    score_awarded: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    answered_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    graded_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz_question = relationship("QuizQuestion", back_populates="responses")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    percentage_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unanswered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="result")

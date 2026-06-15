from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    semester: Mapped[str | None] = mapped_column(String(50), nullable=True)
    semester_id: Mapped[int | None] = mapped_column(
        ForeignKey("semesters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topics = relationship("Topic", back_populates="course", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="course")
    compacts = relationship("CourseCompact", back_populates="course", cascade="all, delete-orphan")


class CourseCompact(Base):
    __tablename__ = "course_compacts"
    __table_args__ = (
        UniqueConstraint("course_id", "version", name="uq_course_compact_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(30), nullable=False, default="local")
    storage_bucket: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    compact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    taxonomy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_terms_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pitfalls_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="compacts")

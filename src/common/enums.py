from enum import StrEnum


class QuestionType(StrEnum):
    OBJECTIVE = "objective"
    THEORY = "theory"
    PRACTICAL = "practical"
    CASE_BASED = "case_based"


class QuestionSourceType(StrEnum):
    ACTUAL = "actual"
    AI_GENERATED = "ai_generated"


class QuizStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"


class QuestionSourceMode(StrEnum):
    ACTUAL_ONLY = "actual_only"
    AI_ONLY = "ai_only"
    MIXED = "mixed"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class GradedBy(StrEnum):
    AUTO = "auto"
    AI = "ai"

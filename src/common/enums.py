from enum import Enum


class QuestionType(str, Enum):
    OBJECTIVE = "objective"
    THEORY = "theory"
    PRACTICAL = "practical"
    CASE_BASED = "case_based"


class QuestionSourceType(str, Enum):
    ACTUAL = "actual"
    AI_GENERATED = "ai_generated"


class QuizStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"


class QuestionSourceMode(str, Enum):
    ACTUAL_ONLY = "actual_only"
    AI_ONLY = "ai_only"
    MIXED = "mixed"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class GradedBy(str, Enum):
    AUTO = "auto"
    AI = "ai"

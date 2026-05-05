from __future__ import annotations

import json
from dataclasses import dataclass

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None

from src.core.config import settings


@dataclass
class TheoryGradeResult:
    score_ratio: float
    strengths: str
    missing_points: str
    feedback: str
    explanation: str
    confidence: float


class TheoryAIGrader:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = settings.GEMINI_MAX_RETRIES

    def _fallback(self, model_solution: str, student_answer: str) -> TheoryGradeResult:
        normalized_solution = (model_solution or "").strip().lower()
        normalized_answer = (student_answer or "").strip().lower()
        if normalized_solution and normalized_answer and normalized_solution in normalized_answer:
            return TheoryGradeResult(
                score_ratio=1.0,
                strengths="Answer contains the expected model solution.",
                missing_points="None",
                feedback="Strong answer.",
                explanation="Heuristic fallback detected direct inclusion of model solution.",
                confidence=0.45,
            )
        if normalized_answer:
            return TheoryGradeResult(
                score_ratio=0.5,
                strengths="Student attempted the question.",
                missing_points="Model solution concepts are incomplete.",
                feedback="Expand key concepts and include clearer justification.",
                explanation="Heuristic fallback awarded partial credit for non-empty response.",
                confidence=0.3,
            )
        return TheoryGradeResult(
            score_ratio=0.0,
            strengths="No valid response detected.",
            missing_points="Core concepts and final answer are missing.",
            feedback="Provide a complete written answer.",
            explanation="No submitted text available for grading.",
            confidence=0.9,
        )

    def grade_theory_answer(
        self,
        *,
        question_text: str,
        marking_scheme: str,
        model_solution: str,
        student_answer: str,
        marks: float,
    ) -> TheoryGradeResult:
        if not self.api_key or httpx is None:
            return self._fallback(model_solution, student_answer)

        prompt = (
            "Grade the student answer against the model solution and marking scheme. "
            "Return strict JSON object with keys: score_ratio (0-1), strengths, missing_points, feedback, explanation, confidence (0-1). "
            f"Question: {question_text}\n"
            f"Marking scheme: {marking_scheme}\n"
            f"Model solution: {model_solution}\n"
            f"Student answer: {student_answer}\n"
            f"Maximum marks: {marks}\n"
        )

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        for _ in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                parsed = json.loads(text)
                score_ratio = float(parsed.get("score_ratio", 0.0))
                score_ratio = min(1.0, max(0.0, score_ratio))
                confidence = float(parsed.get("confidence", 0.0))
                confidence = min(1.0, max(0.0, confidence))
                return TheoryGradeResult(
                    score_ratio=score_ratio,
                    strengths=str(parsed.get("strengths", "")),
                    missing_points=str(parsed.get("missing_points", "")),
                    feedback=str(parsed.get("feedback", "")),
                    explanation=str(parsed.get("explanation", "")),
                    confidence=confidence,
                )
            except Exception:  # noqa: BLE001
                continue

        return self._fallback(model_solution, student_answer)

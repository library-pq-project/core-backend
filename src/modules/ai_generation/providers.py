from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None

from src.core.config import settings


@dataclass
class GeneratedQuestionPayload:
    question_text: str
    options: list[str]
    correct_index: int
    solution_text: str
    explanation: str


@dataclass
class AIUsageTelemetry:
    model_name: str
    estimated_input_tokens: int
    estimated_output_tokens: int


class AIQuestionGenerator(Protocol):
    def generate_questions(
        self,
        *,
        context_text: str,
        question_type: str,
        exam_type: str,
        difficulty_level: str,
        user_prompt: str,
        requested_count: int,
    ) -> tuple[list[GeneratedQuestionPayload], AIUsageTelemetry]:
        ...


class GeminiQuestionGenerator:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = settings.GEMINI_MAX_RETRIES

    def _fallback(
        self,
        *,
        question_type: str,
        requested_count: int,
        context_text: str,
    ) -> tuple[list[GeneratedQuestionPayload], AIUsageTelemetry]:
        output = [
            GeneratedQuestionPayload(
                question_text=f"[{question_type.upper()}] Generated question {idx}: {context_text[:120]}",
                options=["Option A", "Option B", "Option C", "Option D"],
                correct_index=1,
                solution_text="Model answer placeholder",
                explanation="AI-generated explanation placeholder",
            )
            for idx in range(1, requested_count + 1)
        ]
        telemetry = AIUsageTelemetry(
            model_name=self.model,
            estimated_input_tokens=max(1, len(context_text) // 4),
            estimated_output_tokens=max(1, requested_count * 120),
        )
        return output, telemetry

    def generate_questions(
        self,
        *,
        context_text: str,
        question_type: str,
        exam_type: str,
        difficulty_level: str,
        user_prompt: str,
        requested_count: int,
    ) -> tuple[list[GeneratedQuestionPayload], AIUsageTelemetry]:
        if not self.api_key:
            return self._fallback(question_type=question_type, requested_count=requested_count, context_text=context_text)
        if httpx is None:
            return self._fallback(question_type=question_type, requested_count=requested_count, context_text=context_text)

        prompt = (
            "You are generating university exam preparation questions. "
            "Return strict JSON array only. Each item must include fields: "
            "question_text, options (exactly 4), correct_index (0-3), solution_text, explanation. "
            f"question_type={question_type}, exam_type={exam_type}, difficulty={difficulty_level}, requested_count={requested_count}. "
            f"user_prompt={user_prompt}. "
            f"context={context_text[:4000]}"
        )

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        last_error: Exception | None = None
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
                import json

                parsed = json.loads(text)
                output: list[GeneratedQuestionPayload] = []
                for item in parsed[:requested_count]:
                    output.append(
                        GeneratedQuestionPayload(
                            question_text=item["question_text"],
                            options=item["options"][:4],
                            correct_index=int(item["correct_index"]),
                            solution_text=item["solution_text"],
                            explanation=item["explanation"],
                        )
                    )
                if output:
                    telemetry = AIUsageTelemetry(
                        model_name=self.model,
                        estimated_input_tokens=max(1, len(prompt) // 4),
                        estimated_output_tokens=max(1, len(text) // 4),
                    )
                    return output, telemetry
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error:
            return self._fallback(question_type=question_type, requested_count=requested_count, context_text=context_text)
        return self._fallback(question_type=question_type, requested_count=requested_count, context_text=context_text)

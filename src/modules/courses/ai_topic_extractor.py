from __future__ import annotations

import json
import re
from typing import Protocol

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None

from src.core.config import settings


class CourseTopicExtractor(Protocol):
    def extract_topics(self, *, course_title: str, compact_text: str) -> list[str]:
        ...


class GeminiCourseTopicExtractor:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = settings.GEMINI_MAX_RETRIES

    def _fallback(self, *, compact_text: str) -> list[str]:
        topics: list[str] = []
        seen: set[str] = set()
        for raw_line in compact_text.splitlines():
            line = raw_line.strip(" -*\t\r\n")
            if not line:
                continue
            if line.lower() in {"course topics", "topics", "topic outline", "contents", "course outline"}:
                continue
            if len(line) > 80:
                continue
            if len(line.split()) < 2 or len(line.split()) > 8:
                continue
            if not re.search(r"[A-Za-z]", line):
                continue
            if line.endswith((".", ":", ";", "?", "!")):
                line = line[:-1].strip()
            normalized = re.sub(r"\s+", " ", line)
            slug = normalized.lower()
            if slug in seen:
                continue
            seen.add(slug)
            topics.append(normalized.title())
            if len(topics) >= 20:
                break
        return topics

    def extract_topics(self, *, course_title: str, compact_text: str) -> list[str]:
        if not compact_text.strip():
            return []

        if not self.api_key or httpx is None:
            return self._fallback(compact_text=compact_text)

        prompt = (
            "Extract the main academic course topics from the provided course compact. "
            "Return strict JSON array only. Each array item must be a short topic name string. "
            "Do not include explanations, numbering, markdown, or duplicates. "
            f"Course title: {course_title}\n"
            f"Compact text: {compact_text[:12000]}"
        )
        url = f"{self.BASE_URL}/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers={
                            "x-goog-api-key": self.api_key,
                            "Content-Type": "application/json",
                        },
                    )
                response.raise_for_status()
                data = response.json()
                parts = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
                if text.startswith("```"):
                    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    break
                cleaned: list[str] = []
                seen: set[str] = set()
                for item in parsed:
                    topic = str(item).strip()
                    if not topic:
                        continue
                    slug = re.sub(r"\s+", " ", topic.lower())
                    if slug in seen:
                        continue
                    seen.add(slug)
                    cleaned.append(topic)
                if cleaned:
                    return cleaned
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if settings.AI_ALLOW_STUB_FALLBACK:
            return self._fallback(compact_text=compact_text)
        if last_error:
            raise RuntimeError(f"Gemini topic extraction failed: {last_error}") from last_error
        raise RuntimeError("Gemini topic extraction failed without a captured exception")

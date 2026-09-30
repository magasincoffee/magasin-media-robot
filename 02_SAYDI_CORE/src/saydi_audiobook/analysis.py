from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re
from typing import Any
from urllib import request as urllib_request

from .contracts import BookProfile


class AnalysisProvider(ABC):
    @abstractmethod
    def analyze_book(self, text: str) -> BookProfile:
        raise NotImplementedError


class RuleBasedAnalysisProvider(AnalysisProvider):
    """Deterministic fallback so the workflow remains runnable without any LLM."""

    BUSINESS = {
        "kinh doanh", "doanh nghiệp", "quản trị", "chiến lược", "khách hàng",
        "thị trường", "lợi nhuận", "doanh thu", "marketing", "đầu tư",
    }
    FICTION = {
        "cô ấy", "anh ấy", "nhân vật", "căn phòng", "mỉm cười", "thì thầm",
        "hét lên", "nước mắt", "trái tim", "bóng tối",
    }

    def analyze_book(self, text: str) -> BookProfile:
        low = text.lower()
        business_hits = sum(low.count(token) for token in self.BUSINESS)
        fiction_hits = sum(low.count(token) for token in self.FICTION)
        dialogue_marks = len(re.findall(r"(^|\n)\s*[–—-]\s+|[“\"]", text))
        technical_hits = len(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:%|kg|km|usd|vnd|triệu|tỷ)\b", low))

        if business_hits >= max(2, fiction_hits + 1):
            genre, subgenre, profile = "BUSINESS", "GENERAL_BUSINESS", "BUSINESS_CLEAR"
            tone = ["clear", "authoritative", "practical"]
            confidence = min(0.9, 0.62 + 0.04 * business_hits)
        elif fiction_hits >= 2 or dialogue_marks >= 4:
            genre, subgenre, profile = "FICTION", "GENERAL_FICTION", "STORY_NARRATIVE"
            tone = ["narrative", "expressive", "warm"]
            confidence = min(0.9, 0.62 + 0.03 * max(fiction_hits, dialogue_marks))
        else:
            genre, subgenre, profile = "GENERAL", "UNCLASSIFIED", "GENERAL_CLEAR"
            tone = ["clear", "neutral"]
            confidence = 0.55

        profile_obj = BookProfile(
            genre=genre,
            subgenre=subgenre,
            tone=tone,
            dialogue_density="high" if dialogue_marks >= 8 else "medium" if dialogue_marks >= 3 else "low",
            technical_density="high" if technical_hits >= 8 else "medium" if technical_hits >= 3 else "low",
            recommended_narration_profiles=[profile],
            confidence=confidence,
            analysis_provider="rules-v0.1",
            evidence=[
                f"business_hits={business_hits}",
                f"fiction_hits={fiction_hits}",
                f"dialogue_marks={dialogue_marks}",
                f"technical_hits={technical_hits}",
            ],
        )
        profile_obj.validate()
        return profile_obj


class OllamaAnalysisProvider(AnalysisProvider):
    """Local-LLM adapter. No cloud dependency; endpoint defaults to local Ollama."""

    def __init__(
        self,
        model: str,
        endpoint: str = "http://127.0.0.1:11434/api/generate",
        timeout: float = 60.0,
    ):
        if not model.strip():
            raise ValueError("model is required")
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    def analyze_book(self, text: str) -> BookProfile:
        excerpt = text[:12000]
        prompt = (
            "Analyze this Vietnamese/English audiobook source and return ONLY JSON with keys: "
            "genre, subgenre, tone (array), dialogue_density (low|medium|high), "
            "technical_density (low|medium|high), recommended_narration_profiles (array), "
            "confidence (0..1), evidence (array of short strings). "
            "Do not rewrite the book. Use GENERAL/UNCLASSIFIED when uncertain.\n\nSOURCE:\n"
            + excerpt
        )
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        raw = body.get("response")
        if not isinstance(raw, str):
            raise RuntimeError("Ollama response missing string 'response'")
        data: dict[str, Any] = json.loads(raw)
        profile = BookProfile(
            genre=str(data.get("genre", "GENERAL")),
            subgenre=str(data.get("subgenre", "UNCLASSIFIED")),
            tone=[str(x) for x in data.get("tone", ["neutral"])],
            dialogue_density=str(data.get("dialogue_density", "low")),
            technical_density=str(data.get("technical_density", "low")),
            recommended_narration_profiles=[
                str(x) for x in data.get("recommended_narration_profiles", ["GENERAL_CLEAR"])
            ],
            confidence=float(data.get("confidence", 0.5)),
            analysis_provider=f"ollama:{self.model}",
            evidence=[str(x) for x in data.get("evidence", [])],
        )
        profile.validate()
        return profile

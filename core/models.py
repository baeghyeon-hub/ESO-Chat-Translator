"""
공유 데이터 타입 정의.
의존하는 모듈 없음 — 순환 import 위험 차단.

흐름:
  parser  → ChatMessage
  pipeline → TranslationResult (+ PipelineTrace)
  coordinator → 두 타입 모두 사용
"""
from __future__ import annotations
from dataclasses import dataclass, field


# ── 채팅 메시지 ───────────────────────────────────────────────

@dataclass
class ChatMessage:
    """watcher/parser가 생성, dispatcher/coordinator가 소비."""
    time_str: str
    channel:  str    # "say" | "group" | "guild" | "whisper" | "zone" | "system"
    speaker:  str
    text:     str


# ── 번역 결과 ─────────────────────────────────────────────────

# source 값 상수
SRC_TM      = "tm"       # Translation Memory 히트
SRC_PATTERN = "pattern"  # 패턴 번역
SRC_CACHE   = "cache"    # 파일 캐시 히트
SRC_DEEPL   = "deepl"    # DeepL API 호출
SRC_ERROR   = "error"    # 오류


@dataclass
class PipelineTrace:
    """파이프라인 단계별 타이밍 (debug=True 일 때만 채워짐)."""
    tm_ms:       float | None = None
    pattern_ms:  float | None = None
    tokenize_ms: float | None = None
    deepl_ms:    float | None = None

    def summary(self) -> str:
        parts = []
        if self.tm_ms       is not None: parts.append(f"tm={self.tm_ms:.1f}ms")
        if self.pattern_ms  is not None: parts.append(f"pat={self.pattern_ms:.1f}ms")
        if self.tokenize_ms is not None: parts.append(f"tok={self.tokenize_ms:.1f}ms")
        if self.deepl_ms    is not None: parts.append(f"deepl={self.deepl_ms:.1f}ms")
        return " | ".join(parts)


@dataclass
class TranslationResult:
    """pipeline이 생성, dispatcher/coordinator/ui가 소비."""
    original:   str
    translated: str
    source:     str              # SRC_* 상수 중 하나
    elapsed_ms: float = 0.0
    trace:      PipelineTrace | None = None

    @property
    def is_error(self) -> bool:
        return self.source == SRC_ERROR

    def log_line(self) -> str:
        """디버그 출력용 한 줄 요약."""
        preview = self.original[:40].replace("\n", " ")
        trace_str = f" ({self.trace.summary()})" if self.trace else ""
        return f"[{self.source}] {preview!r} → {self.translated!r}{trace_str}"

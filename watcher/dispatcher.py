"""
메시지 디스패처.
  - 즉시 처리 (한국어 / 캐시 / 패턴)
  - 배치 버퍼링 후 ThreadPoolExecutor로 DeepL 병렬 호출
  - 채널별 문맥 버퍼 관리

coordinator가 생성하고, ChatMessage를 넘겨받아
TranslationResult를 콜백으로 돌려줌.
"""
from __future__ import annotations
import concurrent.futures
import threading
import time
from typing import Callable

from core.models  import ChatMessage, TranslationResult, SRC_CACHE
from core.pattern import try_pattern, quick_match
from core.pipeline import translate_to_korean, is_error_translation

# ── 배치 설정 ─────────────────────────────────────────────────
BATCH_WINDOW   = 0.12   # 메시지 묶음 대기 (초)
BATCH_MAX_SIZE = 20     # 배치 최대 크기

# ── 채널별 문맥 윈도우 ────────────────────────────────────────
_CTX_WINDOW: dict[str, int] = {
    "whisper": 6,
    "group":   5,
    "guild":   4,
    "say":     3,
    "zone":    2,
    "system":  0,
}

# 콜백 타입: (ChatMessage, TranslationResult) → None
ResultCallback = Callable[[ChatMessage, TranslationResult], None]


class Dispatcher:
    def __init__(
        self,
        cfg:      dict,
        cache,                    # LRUCache
        glossary: dict,
        on_result: ResultCallback,
        debug:    bool = False,
    ):
        self._cfg       = cfg
        self._cache     = cache
        self._glossary  = glossary
        self._on_result = on_result
        self._debug     = debug

        # 문맥 버퍼: {channel: [text, ...]}
        self._ctx_buf:  dict[str, list[str]] = {}
        self._ctx_lock  = threading.Lock()

        # 배치 버퍼
        self._batch:     list[ChatMessage] = []
        self._batch_lock = threading.Lock()
        self._last_time  = 0.0

        # 스레드풀 재사용
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    # ── 공개 API ──────────────────────────────────────────────

    def feed(self, msg: ChatMessage) -> None:
        """파싱된 ChatMessage 하나를 받아 처리 경로 결정."""
        from watcher.parser import is_korean  # 순환 방지용 지연 import

        text = msg.text

        # 1. 한국어 → 번역 불필요
        if is_korean(text):
            self._emit(msg, TranslationResult(
                original=text, translated=text,
                source="korean", elapsed_ms=0.0,
            ))
            return

        # 2. 파일 캐시 히트
        if text in self._cache:
            self._emit(msg, TranslationResult(
                original=text, translated=self._cache[text],
                source=SRC_CACHE, elapsed_ms=0.0,
            ))
            return

        # 3. 패턴 번역 (즉시)
        pattern_result = try_pattern(text, self._glossary)
        if pattern_result:
            self._cache[text] = pattern_result
            self._emit(msg, TranslationResult(
                original=text, translated=pattern_result,
                source="pattern", elapsed_ms=0.0,
            ))
            return

        # 4. DeepL 배치 버퍼
        with self._batch_lock:
            self._batch.append(msg)
            self._last_time = time.monotonic()

    def flush_if_ready(self, api_key: str) -> None:
        """배치 조건(타임아웃 or 최대 크기) 충족 시 병렬 번역 실행."""
        with self._batch_lock:
            if not self._batch:
                return
            elapsed = time.monotonic() - self._last_time
            full    = len(self._batch) >= BATCH_MAX_SIZE
            if not (elapsed >= BATCH_WINDOW or full):
                return
            pending = self._batch[:]
            self._batch.clear()

        self._translate_parallel(pending, api_key)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    # ── 내부 ──────────────────────────────────────────────────

    def _emit(self, msg: ChatMessage, result: TranslationResult) -> None:
        self._on_result(msg, result)

    def _get_context(self, channel: str) -> str:
        window = _CTX_WINDOW.get(channel, 3)
        if window == 0:
            return ""
        with self._ctx_lock:
            buf = self._ctx_buf.get(channel, [])
            return " ".join(buf[-window:])

    def _push_context(self, channel: str, text: str) -> None:
        window = _CTX_WINDOW.get(channel, 3)
        if window == 0:
            return
        with self._ctx_lock:
            buf = self._ctx_buf.setdefault(channel, [])
            buf.append(text)
            if len(buf) > window:
                buf.pop(0)

    def _translate_parallel(self, pending: list[ChatMessage], api_key: str) -> None:
        def translate_one(msg: ChatMessage) -> tuple[ChatMessage, TranslationResult]:
            ctx    = self._get_context(msg.channel)
            result = translate_to_korean(
                msg.text, api_key, self._glossary, ctx, debug=self._debug
            )
            if not result.is_error:
                self._cache[msg.text] = result.translated
                self._push_context(msg.channel, msg.text)
            return msg, result

        futures = [self._executor.submit(translate_one, msg) for msg in pending]
        for fut in concurrent.futures.as_completed(futures):
            try:
                msg, result = fut.result()
                self._emit(msg, result)
            except Exception as e:
                # 개별 실패는 조용히 로그만
                if self._debug:
                    print(f"[dispatcher] 번역 오류: {e}")

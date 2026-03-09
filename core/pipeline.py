"""
번역 파이프라인 오케스트레이터.
memory → pattern → tokenize → deepl → restore 순서를 조합.
각 단계 타이밍을 PipelineTrace에 기록 (debug=True 시 로그 출력).

외부에서 사용하는 진입점:
  translate_to_korean(text, api_key, glossary, context, debug) → TranslationResult
  translate_to_english(text, api_key, glossary, reverse_glossary) → TranslationResult
  is_error_translation(text) → bool
"""
from __future__ import annotations
import time
import threading

from core.models import (
    TranslationResult, PipelineTrace,
    SRC_TM, SRC_PATTERN, SRC_CACHE, SRC_DEEPL, SRC_ERROR,
)
from core.memory  import tm_get, tm_set
from core.pattern import try_pattern
from core.deepl   import DeepLClient, is_error
from core.glossary import (
    tokenize, restore_tokens,
    apply_reverse_glossary, restore_reverse_terms,
)

# DeepL 클라이언트 캐시 {api_key: DeepLClient}
_clients: dict[str, DeepLClient] = {}
_clients_lock = threading.Lock()


def _get_client(api_key: str) -> DeepLClient:
    with _clients_lock:
        if api_key not in _clients:
            _clients[api_key] = DeepLClient(api_key)
        return _clients[api_key]


def reset_session(api_key: str) -> None:
    client = _get_client(api_key)
    client.reset_session()


# ── 영→한 파이프라인 ──────────────────────────────────────────

def translate_to_korean(
    text:     str,
    api_key:  str,
    glossary: dict,
    context:  str  = "",
    debug:    bool = False,
) -> TranslationResult:
    """
    영→한 번역 파이프라인.

    단계:
      1. Translation Memory
      2. 패턴 번역 (QUICK_CACHE + PATTERNS)
      3. 토큰화 → DeepL → 토큰 복원
    """
    original  = text.strip()
    t_start   = time.perf_counter()
    trace     = PipelineTrace() if debug else None

    # ── 1. Translation Memory ──────────────────────────────
    t0     = time.perf_counter()
    cached = tm_get(original)
    if trace:
        trace.tm_ms = (time.perf_counter() - t0) * 1000

    if cached:
        result = TranslationResult(
            original   = original,
            translated = cached,
            source     = SRC_TM,
            elapsed_ms = (time.perf_counter() - t_start) * 1000,
            trace      = trace,
        )
        if debug:
            print(f"[pipeline] {result.log_line()}")
        return result

    # ── 2. 패턴 번역 ──────────────────────────────────────
    t0             = time.perf_counter()
    pattern_result = try_pattern(original, glossary)
    if trace:
        trace.pattern_ms = (time.perf_counter() - t0) * 1000

    if pattern_result:
        tm_set(original, pattern_result)
        result = TranslationResult(
            original   = original,
            translated = pattern_result,
            source     = SRC_PATTERN,
            elapsed_ms = (time.perf_counter() - t_start) * 1000,
            trace      = trace,
        )
        if debug:
            print(f"[pipeline] {result.log_line()}")
        return result

    # ── 3. 토큰화 ─────────────────────────────────────────
    t0                   = time.perf_counter()
    tokenized, token_map = tokenize(original, glossary)
    if trace:
        trace.tokenize_ms = (time.perf_counter() - t0) * 1000

    # ── 4. DeepL 호출 ─────────────────────────────────────
    t0         = time.perf_counter()
    client     = _get_client(api_key)
    raw        = client.translate(
        text        = tokenized,
        target_lang = "KO",
        source_lang = "EN",
        context     = context,
        use_xml     = bool(token_map),
    )
    if trace:
        trace.deepl_ms = (time.perf_counter() - t0) * 1000

    if is_error(raw):
        result = TranslationResult(
            original   = original,
            translated = raw,
            source     = SRC_ERROR,
            elapsed_ms = (time.perf_counter() - t_start) * 1000,
            trace      = trace,
        )
        if debug:
            print(f"[pipeline] {result.log_line()}")
        return result

    # ── 5. 토큰 복원 (여기서만 한국어 등장) ──────────────
    translated = restore_tokens(raw, token_map)
    tm_set(original, translated)

    result = TranslationResult(
        original   = original,
        translated = translated,
        source     = SRC_DEEPL,
        elapsed_ms = (time.perf_counter() - t_start) * 1000,
        trace      = trace,
    )
    if debug:
        print(f"[pipeline] {result.log_line()}")
    return result


# ── 한→영 파이프라인 ──────────────────────────────────────────

def translate_to_english(
    text:             str,
    api_key:          str,
    glossary:         dict = {},
    reverse_glossary: dict = {},
) -> TranslationResult:
    """한→영 번역."""
    original = text.strip()
    t_start  = time.perf_counter()

    preprocessed, protected = apply_reverse_glossary(
        original, glossary, reverse_glossary
    )
    client = _get_client(api_key)
    raw    = client.translate(
        text        = preprocessed,
        target_lang = "EN-US",
        source_lang = "KO",
        use_xml     = bool(protected),
    )

    if is_error(raw):
        return TranslationResult(
            original   = original,
            translated = raw,
            source     = SRC_ERROR,
            elapsed_ms = (time.perf_counter() - t_start) * 1000,
        )

    translated = restore_reverse_terms(raw, protected)
    return TranslationResult(
        original   = original,
        translated = translated,
        source     = SRC_DEEPL,
        elapsed_ms = (time.perf_counter() - t_start) * 1000,
    )


# ── 유틸 ─────────────────────────────────────────────────────

def is_error_translation(text: str) -> bool:
    return is_error(text)

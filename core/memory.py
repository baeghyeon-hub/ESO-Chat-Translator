"""
Translation Memory.
파이프라인 내부 단기 메모리 — 파일 캐시(cache.py)와 별개.

- 키: 원문 소문자 strip
- LRU 2000개
- thread-safe
- 향후 파일 영속화 / 멀티캐릭터 공유 캐시 붙일 자리
"""
from __future__ import annotations
import threading
from collections import OrderedDict

_TM_MAX = 2000


class TranslationMemory:
    def __init__(self, max_size: int = _TM_MAX):
        self._max  = max_size
        self._data: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, text: str) -> str | None:
        key = text.strip().lower()
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def set(self, text: str, result: str) -> None:
        key = text.strip().lower()
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = result
            if len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# 모듈 레벨 싱글턴 — pipeline에서 import해서 사용
_TM = TranslationMemory()


def tm_get(text: str) -> str | None:
    return _TM.get(text)


def tm_set(text: str, result: str) -> None:
    _TM.set(text, result)


def tm_clear() -> None:
    _TM.clear()

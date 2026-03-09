import json
import os
import sys
from collections import OrderedDict


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__ + "/../../"))


CACHE_FILE = os.path.join(_base_dir(), "translation_cache.json")
CACHE_MAX   = 5000   # LRU 최대 항목 수


class LRUCache:
    """
    OrderedDict 기반 LRU 캐시.
    - 조회 시 항목을 맨 뒤로 이동 → 가장 최근 사용 순 유지
    - CACHE_MAX 초과 시 가장 오래된 항목부터 삭제
    - dict 인터페이스를 모방하여 기존 코드와 호환
    """

    def __init__(self, max_size: int = CACHE_MAX):
        self._max  = max_size
        self._data: OrderedDict[str, str] = OrderedDict()

    # ── dict 호환 인터페이스 ─────────────────────────────────

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> str:
        self._data.move_to_end(key)
        return self._data[key]

    def __setitem__(self, key: str, value: str) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._max:
            self._data.popitem(last=False)   # 가장 오래된 항목 제거

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default=None):
        if key not in self._data:
            return default
        return self[key]

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def clear(self) -> None:
        self._data.clear()

    # ── 직렬화 ──────────────────────────────────────────────

    def to_dict(self) -> dict:
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: dict, max_size: int = CACHE_MAX) -> "LRUCache":
        cache = cls(max_size)
        # 저장 순서대로 삽입 (가장 마지막 = 가장 최근)
        for k, v in data.items():
            cache._data[k] = v
        # 용량 초과분 정리
        while len(cache._data) > max_size:
            cache._data.popitem(last=False)
        return cache


# ── 파일 I/O ────────────────────────────────────────────────

def load_cache() -> LRUCache:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cache = LRUCache.from_dict(data)
            print(f"캐시 {len(cache)}개 로드")
            return cache
        except Exception:
            pass
    return LRUCache()


def save_cache(cache: LRUCache) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache.to_dict(), f, ensure_ascii=False)
    except Exception as e:
        print(f"캐시 저장 실패: {e}")

import json
import os
import sys

def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__ + "/../../"))

CACHE_FILE = os.path.join(_base_dir(), "translation_cache.json")
CACHE_MAX   = 5000
CACHE_PRUNE = 1000


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"캐시 {len(data)}개 로드")
            return data
        except Exception:
            pass
    return {}


def save_cache(cache: dict) -> None:
    try:
        if len(cache) > CACHE_MAX:
            keys = list(cache.keys())
            for k in keys[:CACHE_PRUNE]:
                del cache[k]
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        print(f"캐시 저장 실패: {e}")

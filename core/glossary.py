import csv
import os
import re
from collections import defaultdict

# ── 토큰 타입 ────────────────────────────────────────────────
META = "META"   # LFG, WTB, GG — 문장 앞일 때 뒤로 이동 가능
MOD  = "MOD"    # Magicka, Dragonknight — 수식어, 제자리 유지
NAME = "NAME"   # vHRC, Falkreath Hold — 고유명사, 제자리 유지


# ── 용어집 로드 ──────────────────────────────────────────────

def load_glossary(path: str = "eso_glossary.csv") -> dict:
    """
    English → (Korean, Type) 매핑 로드.
    같은 EN 키에 여러 KO가 있으면 첫 번째(가장 대표적인) 것 사용.
    긴 표현 우선 정렬 + 패턴 사전 컴파일.
    반환: {en: {"ko": str, "type": str, "pattern": re.Pattern}}
    """
    raw: dict[str, dict] = {}
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                en   = row.get("English", "").strip()
                ko   = row.get("Korean",  "").strip()
                typ  = row.get("Type",    "MOD").strip().upper()
                if en and ko and en not in raw:   # 첫 번째 KO 우선
                    raw[en] = {"ko": ko, "type": typ}
    except Exception as e:
        print(f"용어집 로드 실패: {e}")
        return {}

    # 긴 표현 우선 정렬
    sorted_items = sorted(raw.items(), key=lambda x: -len(x[0]))

    result = {}
    for en, meta in sorted_items:
        pattern = re.compile(
            r'(?<![^\W])' + re.escape(en) + r'(?![^\W])',
            re.IGNORECASE
        )
        result[en] = {
            "ko":      meta["ko"],
            "type":    meta["type"],
            "pattern": pattern,
        }
    return result


def load_reverse_glossary(path: str = "eso_glossary_reverse.csv") -> dict[str, str]:
    """Korean → English 역방향 용어집 로드."""
    reverse: dict[str, str] = {}
    if not os.path.exists(path):
        return reverse
    try:
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                ko = row.get("Korean",  "").strip()
                en = row.get("English", "").strip()
                if ko and en and ko not in reverse:
                    reverse[ko] = en
    except Exception as e:
        print(f"역방향 용어집 로드 실패: {e}")
    return dict(sorted(reverse.items(), key=lambda x: -len(x[0])))


# ── 토큰화 (영→한 번역 전) ───────────────────────────────────

def tokenize(text: str, glossary: dict) -> tuple[str, dict]:
    """
    원문에서 용어집 표현을 <x id="N"></x> 토큰으로 교체.
    META 토큰이 문장 맨 앞에 있으면 위치를 뒤로 이동.

    반환:
        tokenized  : 토큰이 삽입된 텍스트 (한국어 없음)
        token_map  : {N: {"ko": str, "type": str, "original": str}}
    """
    token_map: dict[int, dict] = {}
    result = text
    idx = 0

    for en, meta in glossary.items():
        pattern = meta["pattern"]

        def replacer(m, en=en, meta=meta):
            nonlocal idx
            i = idx
            idx += 1
            token_map[i] = {
                "ko":       meta["ko"],
                "type":     meta["type"],
                "original": m.group(0),
                "start":    m.start(),
            }
            return f'<x id="{i}"></x>'

        result = pattern.sub(replacer, result)

    # META 토큰 이동: 문장 맨 앞(공백 무시) META 토큰을 문장 끝으로
    result = _relocate_leading_meta(result, token_map)

    return result, token_map


def _relocate_leading_meta(text: str, token_map: dict) -> str:
    """문장 맨 앞의 META 토큰을 문장 끝으로 이동.
    이동 후 본문이 비어있으면 이동하지 않음 (META만 있는 문장).
    """
    leading = re.match(r'^(\s*<x id="\d+"></x>\s*)+', text)
    if not leading:
        return text

    moved = []
    for m in re.finditer(r'<x id="(\d+)"></x>', leading.group(0)):
        tid = int(m.group(1))
        if token_map.get(tid, {}).get("type") == META:
            moved.append(f'<x id="{tid}"></x>')

    if not moved:
        return text

    remainder = text[leading.end():].strip()

    # 본문이 비어있으면 이동하지 않음
    if not remainder:
        return text

    suffix = " " + " ".join(moved)
    return remainder + suffix


def restore_tokens(text: str, token_map: dict) -> str:
    """<x id="N"></x> 토큰을 한국어로 복원."""
    for i, meta in token_map.items():
        text = text.replace(f'<x id="{i}"></x>', meta["ko"])
    return text


# ── 역방향 토큰화 (한→영 번역 전) ───────────────────────────

def apply_reverse_glossary(text: str, glossary: dict,
                            reverse_glossary: dict = {}) -> tuple[str, list[str]]:
    """
    한→영 번역 전처리.
    역방향 전용 CSV가 있으면 우선 적용, 없으면 기존 용어집 역방향으로 폴백.
    한국어 단어 경계(lookahead/lookbehind)로 부분 오탐 방지.
    """
    if reverse_glossary:
        reverse = reverse_glossary
    else:
        reverse = dict(sorted(
            ((v["ko"], en) for en, v in glossary.items()),
            key=lambda x: -len(x[0])
        ))

    result = text
    protected_terms: list[str] = []

    for ko, en in reverse.items():
        pattern = re.compile(
            r'(?<![가-힣\w])' + re.escape(ko) + r'(?![가-힣\w])'
        )

        def replacer(m, en=en):
            i = len(protected_terms)
            protected_terms.append(en)
            return f'<m id="{i}"/>'

        result = pattern.sub(replacer, result)

    return result, protected_terms


def restore_reverse_terms(text: str, protected_terms: list[str]) -> str:
    for i, en in enumerate(protected_terms):
        text = text.replace(f'<m id="{i}"/>', en)
    return text

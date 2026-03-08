import csv
import os
import re


def load_glossary(path: str = "eso_glossary.csv") -> dict[str, str]:
    """English→Korean 용어집 로드. 긴 표현이 먼저 매칭되도록 정렬."""
    glossary: dict[str, str] = {}
    if not os.path.exists(path):
        return glossary
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                en = row.get("English", "").strip()
                ko = row.get("Korean",  "").strip()
                if en and ko:
                    glossary[en] = ko
    except Exception as e:
        print(f"용어집 로드 실패: {e}")
    return dict(sorted(glossary.items(), key=lambda x: -len(x[0])))


def protect_glossary_terms(text: str, glossary: dict) -> tuple[str, list[str]]:
    """원문의 ESO 용어를 <m id=N/> 태그로 보호 → DeepL이 번역하지 않음."""
    replacements: list[str] = []
    protected = text
    for en, ko in glossary.items():
        pattern = re.compile(r'(?<![^\W])' + re.escape(en) + r'(?![^\W])', re.IGNORECASE)
        def replacer(m, ko=ko):
            idx = len(replacements)
            replacements.append(ko)
            return f'<m id="{idx}"/>'
        protected = pattern.sub(replacer, protected)
    return protected, replacements


def restore_glossary_terms(text: str, replacements: list[str]) -> str:
    """<m id=N/> 태그를 저장된 한국어로 복원."""
    for i, ko in enumerate(replacements):
        text = text.replace(f'<m id="{i}"/>', ko)
    return text


def load_reverse_glossary(path: str = "eso_glossary_reverse.csv") -> dict[str, str]:
    """Korean→English 역방향 전용 용어집 로드.
    같은 한국어 표현 여러 개가 하나의 영어로 매핑 가능.
    파일 없으면 빈 dict 반환.
    """
    reverse: dict[str, str] = {}
    if not os.path.exists(path):
        return reverse
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                ko = row.get("Korean", "").strip()
                en = row.get("English", "").strip()
                if ko and en:
                    reverse[ko] = en
    except Exception as e:
        print(f"역방향 용어집 로드 실패: {e}")
    return dict(sorted(reverse.items(), key=lambda x: -len(x[0])))


def apply_reverse_glossary(text: str, glossary: dict,
                            reverse_glossary: dict = {}) -> tuple[str, list[str]]:
    """한→영 번역 전처리.
    역방향 전용 CSV가 있으면 우선 적용, 없으면 기존 용어집 역방향으로 폴백.
    """
    # 역방향 전용 CSV 우선 사용, 없으면 기존 용어집에서 역방향 생성
    if reverse_glossary:
        reverse = reverse_glossary
    else:
        reverse = dict(sorted(
            ((ko, en) for en, ko in glossary.items()),
            key=lambda x: -len(x[0])
        ))
    result = text
    protected_terms = []
    for ko, en in reverse.items():
        pattern = re.compile(re.escape(ko))
        def replacer(m, en=en):
            idx = len(protected_terms)
            protected_terms.append(en)
            return f'<m id="{idx}"/>'
        result = pattern.sub(replacer, result)
    return result, protected_terms


def restore_reverse_terms(text: str, protected_terms: list[str]) -> str:
    """<m id=N/> 태그를 영어 용어로 복원."""
    for i, en in enumerate(protected_terms):
        text = text.replace(f'<m id="{i}"/>', en)
    return text

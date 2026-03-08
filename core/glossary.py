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
    # 긴 표현 우선 매칭 (예: "Major Brutality" > "Brutality")
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

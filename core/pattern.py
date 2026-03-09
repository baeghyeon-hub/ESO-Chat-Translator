"""
패턴 기반 번역.
API 호출 없이 즉시 처리할 수 있는 MMO 채팅 구조를 담당.

처리 순서:
  1. QUICK_CACHE  — 완전 일치 (constants.py에서 이관)
  2. PATTERNS     — 정규식 구조 매칭 (LFG/Need/WTB 등)

캡처 그룹 안의 영어는 용어집으로 치환 후,
미번역 영어가 남으면 DeepL로 위임 (None 반환).
"""
from __future__ import annotations
import re


# ── QUICK_CACHE (완전 일치) ───────────────────────────────────
QUICK_CACHE: dict[str, str] = {
    "lfg":           "파티 구합니다",
    "lf1m":          "1명 구합니다",
    "lf2m":          "2명 구합니다",
    "lf3m":          "3명 구합니다",
    "lf group":      "파티 구합니다",
    "lfm":           "멤버 구합니다",
    "wtb":           "삽니다",
    "wts":           "팝니다",
    "wtt":           "교환합니다",
    "pst":           "귓말 주세요",
    "wb":            "월드 보스",
    "any healers":   "힐러 있나요",
    "any tanks":     "탱커 있나요",
    "any dps":       "딜러 있나요",
    "inv pls":       "초대해주세요",
    "inv please":    "초대해주세요",
    "need inv":      "초대 필요합니다",
    "grp full":      "파티 꽉 찼습니다",
    "group full":    "파티 꽉 찼습니다",
    "ty":            "감사합니다",
    "thx":           "감사합니다",
    "thanks":        "감사합니다",
    "np":            "괜찮아요",
    "gj":            "잘했어요",
    "gg":            "수고했습니다",
    "gf":            "잘 싸웠습니다",
    "wp":            "잘하셨어요",
    "gg wp":         "수고했습니다 잘하셨어요",
    "gf wp":         "잘 싸웠습니다 잘하셨어요",
    "good fight":    "잘 싸웠습니다",
    "rip":           "아이고",
    "ez":            "쉬웠네요",
    "gl":            "화이팅",
    "glhf":          "화이팅 즐거운 게임 되세요",
    "brb":           "잠깐 자리 비웁니다",
    "afk":           "잠시 자리 비움",
    "back":          "돌아왔습니다",
    "rdy":           "준비됐습니다",
    "ready":         "준비됐습니다",
    "not rdy":       "아직 준비 안 됐습니다",
    "wait":          "잠깐요",
    "wait pls":      "잠깐만요",
    "1 sec":         "잠깐요",
    "one sec":       "잠깐요",
    "on my way":     "가고 있습니다",
    "omw":           "가고 있습니다",
    "at wp":         "웨이포인트 있습니다",
    "at wayshrine":  "웨이쉬라인 있습니다",
}


# ── PATTERNS (구조 매칭) ──────────────────────────────────────
_W    = r'[^\s]+'
_REST = rf'(?:{_W})(?:\s+(?:{_W}))*'

_PATTERNS: list[tuple[re.Pattern, callable]] = [
    # 구인
    (re.compile(rf'^lfg\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 파티 구함"),
    (re.compile(rf'^lf\s*(\d+)\s*m\s+({_REST})$',                re.I), lambda g: f"{g[1]} {g[0]}명 구함"),
    (re.compile(rf'^lf\s+({_REST})\s+for\s+({_REST})$',          re.I), lambda g: f"{g[1]}용 {g[0]} 구함"),
    (re.compile(rf'^lf\s+({_REST})$',                            re.I), lambda g: f"{g[0]} 구함"),
    (re.compile(rf'^need\s+(\d+)\s+({_REST})\s+for\s+({_REST})$',re.I), lambda g: f"{g[2]}용 {g[1]} {g[0]}명 필요"),
    (re.compile(rf'^need\s+({_REST})\s+for\s+({_REST})$',        re.I), lambda g: f"{g[1]}용 {g[0]} 필요"),
    (re.compile(rf'^need\s+(\d+)\s+({_REST})$',                  re.I), lambda g: f"{g[1]} {g[0]}명 필요"),
    (re.compile(rf'^need\s+({_REST})$',                          re.I), lambda g: f"{g[0]} 필요"),
    # 거래
    (re.compile(rf'^wtb\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 삽니다"),
    (re.compile(rf'^wts\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 팝니다"),
    (re.compile(rf'^wtt\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 교환합니다"),
    # lfm = looking for members (for 절 포함 버전 먼저)
    (re.compile(rf'^lfm\s+({_REST})\s+for\s+({_REST})$',       re.I), lambda g: f"{g[1]}용 {g[0]} 멤버 구함"),
    (re.compile(rf'^lfm\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 멤버 구함"),
    # 초대
    (re.compile(rf'^inv\s+({_REST})$',                           re.I), lambda g: f"{g[0]} 초대합니다"),
    # 반응/인사 (고정 출력)
    (re.compile(r'^gg\s*wp$',                                    re.I), lambda g: "잘 싸웠어요"),
    (re.compile(r'^gg\s+everyone$',                              re.I), lambda g: "모두 수고했어요"),
    (re.compile(r'^gg\s+guys$',                                  re.I), lambda g: "모두 수고했어요"),
    (re.compile(r'^gg$',                                         re.I), lambda g: "잘 했어요"),
    (re.compile(r'^gf\s+everyone$',                              re.I), lambda g: "모두 수고했어요"),
    (re.compile(r'^well\s+played$',                              re.I), lambda g: "잘 하셨어요"),
    (re.compile(r'^good\s+fight$',                               re.I), lambda g: "잘 싸웠어요"),
    (re.compile(r'^good\s+game$',                                re.I), lambda g: "좋은 게임이었어요"),
    (re.compile(r'^nice\s+run$',                                 re.I), lambda g: "수고했어요"),
    (re.compile(r'^good\s+run$',                                 re.I), lambda g: "수고했어요"),
]


# ── STOPWORDS ─────────────────────────────────────────────────
# 캡처 그룹 치환 후 남아있어도 허용하는 영어 단어
_STOPWORDS: frozenset[str] = frozenset({
    # 문법어
    "a", "an", "the", "for", "in", "of", "to", "and", "or", "on",
    "at", "by", "is", "be", "if", "as", "it", "up", "me", "my", "we", "us",
    # MMO 채팅 상용어
    "run", "runs", "doing", "do", "need", "lf", "looking",
    "group", "slot", "spot", "spots", "open", "full",
    "help", "carry", "clear", "prog", "progression",
    "attempt", "tonight", "now", "soon", "asap", "today",
    "anyone", "someone", "please", "pst", "msg",
    "join", "invite", "inv", "want", "have", "with", "can",
    "gear", "build", "set", "meta",
    "quick", "fast", "ez", "easy", "hard",
    "hi", "hey", "hello", "thanks", "ty", "thx", "np", "ok", "okay",
    "guys", "everyone", "all", "team", "party",
    "good", "great", "nice", "well", "done", "gg", "wp", "gf",
})

_EN_WORD = re.compile(r'[a-zA-Z]{2,}')


# ── 내부 헬퍼 ─────────────────────────────────────────────────

def _apply_glossary(text: str, glossary: dict) -> str:
    """캡처 그룹 내 영어를 용어집으로 한국어 치환 후 후처리."""
    result = text
    for en, meta in glossary.items():
        result = meta["pattern"].sub(meta["ko"], result)
    # 'and' / 'or' 접속사 처리: 용어집에 없는 영어 접속사를 자연스럽게 제거
    result = re.sub(r'\s+and\s+', ' ', result, flags=re.I)
    result = re.sub(r'\s+or\s+',  ' ', result, flags=re.I)
    return result.strip()


def _strip_trailing_meta(text: str, glossary: dict) -> str:
    """캡처그룹 끝에 붙은 META 단어(PST, LFG 등)를 제거.
    'Need tank for vHRC PST' 에서 PST가 for 목적어로 흡수되는 버그 방지."""
    meta_set = {en.lower() for en, v in glossary.items() if v.get("type") == "META"}
    words = text.split()
    while words and words[-1].lower() in meta_set:
        words.pop()
    return ' '.join(words)


def _has_untranslated(text: str) -> bool:
    """용어집 치환 후에도 미번역 영어 단어가 남으면 True."""
    words = _EN_WORD.findall(text)
    return any(w.lower() not in _STOPWORDS for w in words)


# ── 공개 API ──────────────────────────────────────────────────

def quick_match(text: str) -> str | None:
    """QUICK_CACHE 완전 일치 체크."""
    return QUICK_CACHE.get(text.strip().lower())


def pattern_match(text: str, glossary: dict) -> str | None:
    """
    정규식 패턴 매칭.
    캡처 그룹에 용어집 치환 후 미번역 영어 잔류 시 None 반환 (DeepL 위임).
    """
    stripped = text.strip()
    for pattern, formatter in _PATTERNS:
        m = pattern.match(stripped)
        if not m:
            continue
        try:
            raw_groups = list(m.groups())
            # 모든 캡처그룹 끝의 META 단어 제거
            # ex) "Need tank for vHRC PST" → g[1]="vHRC PST" → "vHRC"
            # ex) "WTB Magicka gear PST"   → g[0]="Magicka gear PST" → "Magicka gear"
            raw_groups = [_strip_trailing_meta(g, glossary) for g in raw_groups]
            if any(g == "" for g in raw_groups if not g.isdigit()):
                continue  # 제거 후 비어버린 캡처그룹 있으면 기각
            groups = [_apply_glossary(g, glossary) for g in raw_groups]
            non_numeric = [g for g in groups if not g.isdigit()]
            if any(_has_untranslated(g) for g in non_numeric):
                continue
            return formatter(groups)
        except Exception:
            continue
    return None


def try_pattern(text: str, glossary: dict) -> str | None:
    """
    QUICK_CACHE → PATTERNS 순서로 시도.
    둘 다 실패하면 None.
    """
    return quick_match(text) or pattern_match(text, glossary)

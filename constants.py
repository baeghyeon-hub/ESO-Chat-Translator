# ── 채널 정보 ─────────────────────────────────────────────────
CHANNEL_INFO = {
    "say":     {"color": "#e0e0e0", "badge": "#3f3f46", "label": "일반"},
    "group":   {"color": "#88dd88", "badge": "#14532d", "label": "파티"},
    "zone":    {"color": "#88bbff", "badge": "#1e3a5f", "label": "지역"},
    "guild":   {"color": "#ffcc55", "badge": "#451a03", "label": "길드"},
    "whisper": {"color": "#ff99dd", "badge": "#4a1942", "label": "귓말"},
    "system":  {"color": "#aaaaaa", "badge": "#27272a", "label": "시스템"},
}

CHANNEL_NUM_MAP = {
    1: "say", 2: "say", 3: "say",
    4: "zone", 5: "zone",
    6: "group", 7: "group",
    8: "guild", 9: "guild", 10: "guild", 11: "guild", 12: "guild",
    13: "whisper", 14: "whisper",
    31: "zone", 32: "system",
}

def get_channel(n: int) -> str:
    return CHANNEL_NUM_MAP.get(n, "say")


# ── 상용구 즉시 번역 테이블 ────────────────────────────────────
QUICK_CACHE: dict[str, str] = {
    "lfg": "파티 구합니다",
    "lf1m": "1명 구합니다",
    "lf2m": "2명 구합니다",
    "lf3m": "3명 구합니다",
    "lf group": "파티 구합니다",
    "lfm": "멤버 구합니다",
    "wtb": "삽니다",
    "wts": "팝니다",
    "wtt": "교환합니다",
    "pst": "귓말 주세요",
    "wb": "월드 보스",
    "any healers": "힐러 있나요",
    "any tanks": "탱커 있나요",
    "any dps": "딜러 있나요",
    "inv pls": "초대해주세요",
    "inv please": "초대해주세요",
    "need inv": "초대 필요합니다",
    "grp full": "파티 꽉 찼습니다",
    "group full": "파티 꽉 찼습니다",
    "ty": "감사합니다",
    "thx": "감사합니다",
    "thanks": "감사합니다",
    "np": "괜찮아요",
    "gj": "잘했어요",
    "gg": "수고했습니다",
    "gf": "잘 싸웠습니다",
    "wp": "잘하셨어요",
    "gg wp": "수고했습니다 잘하셨어요",
    "gf wp": "잘 싸웠습니다 잘하셨어요",
    "good fight": "잘 싸웠습니다",
    "rip": "아이고",
    "ez": "쉬웠네요",
    "gl": "화이팅",
    "glhf": "화이팅 즐거운 게임 되세요",
    "brb": "잠깐 자리 비웁니다",
    "afk": "잠시 자리 비움",
    "back": "돌아왔습니다",
    "rdy": "준비됐습니다",
    "ready": "준비됐습니다",
    "not rdy": "아직 준비 안 됐습니다",
    "wait": "잠깐요",
    "wait pls": "잠깐만요",
    "1 sec": "잠깐요",
    "one sec": "잠깐요",
    "on my way": "가고 있습니다",
    "omw": "가고 있습니다",
    "at wp": "웨이포인트 있습니다",
    "at wayshrine": "웨이쉬라인 있습니다",
}

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

"""
ESO Chat.log 라인 파싱.
raw 문자열 → ChatMessage (또는 None).
외부 의존: constants, core/models.
"""
from __future__ import annotations
import re

from constants  import get_channel
from core.models import ChatMessage

# ESO 로그 포맷:
# 2024-01-01T11:24:00.000+09:00 13,PlayerName,"message text"
LOG_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}):\d{2}\.\d+[+\-]\d{2}:\d{2})\s+"
    r"(\d+),([^,]+),(.+)"
)

# ESO 인라인 컬러/링크 태그
_COLOR_TAG  = re.compile(r'\|c[0-9a-fA-F]{6}')
_RESET_TAG  = re.compile(r'\|r')
_LINK_TAG   = re.compile(r'\|H[^|]*\|h([^|]*)\|h')
_ICON_TAG   = re.compile(r'\|t[^|]*\|t')


def is_korean(text: str) -> bool:
    return bool(re.search(r'[\uAC00-\uD7A3]', text))


def is_broken(text: str) -> bool:
    """중국어 비율이 높으면 깨진 텍스트로 판단."""
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return len(text) > 0 and cjk / len(text) > 0.3


def _strip_tags(text: str) -> str:
    text = _COLOR_TAG.sub('', text)
    text = _RESET_TAG.sub('', text)
    text = _LINK_TAG.sub(r'\1', text)
    text = _ICON_TAG.sub('', text)
    return text.strip()


def parse_line(line: str, cfg: dict) -> ChatMessage | None:
    """
    로그 한 줄을 파싱해 ChatMessage 반환.
    필터 조건(채널 비활성, 내 캐릭터)에 걸리면 None.
    """
    m = LOG_PATTERN.match(line.strip())
    if not m:
        return None

    _ts, time_str, ch_str, speaker, raw_msg = m.groups()
    speaker = speaker.strip()
    message = _strip_tags(raw_msg.strip().strip('"'))

    if not message or is_broken(message):
        return None

    try:
        ch_num = int(ch_str)
    except ValueError:
        ch_num = 0

    channel = get_channel(ch_num)

    # 채널 필터
    if not cfg.get("channels", {}).get(channel, True):
        return None

    # 내 캐릭터 메시지 숨기기
    if cfg.get("hide_my_chat", False):
        my_name = cfg.get("my_character_name", "").strip()
        if my_name and speaker == my_name:
            return None

    return ChatMessage(
        time_str = time_str,
        channel  = channel,
        speaker  = speaker,
        text     = message,
    )

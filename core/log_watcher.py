import concurrent.futures
import os
import re
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from constants import QUICK_CACHE, get_channel
from core.translator import translate_to_korean

LOG_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}):\d{2}\.\d+[+\-]\d{2}:\d{2})\s+"
    r"(\d+),([^,]+),(.+)"
)


def is_korean(t: str) -> bool:
    return bool(re.search(r'[\uAC00-\uD7A3]', t))


def is_broken(t: str) -> bool:
    """중국어 비율이 높으면 깨진 텍스트로 판단."""
    w = sum(1 for c in t if '\u4e00' <= c <= '\u9fff')
    return len(t) > 0 and w / len(t) > 0.3


class WatchThread(QThread):
    new_message = pyqtSignal(str, str, str, str, object)  # time, ch, speaker, orig, translated
    status      = pyqtSignal(str)
    cache_count = pyqtSignal(int)

    def __init__(self, cfg: dict, cache: dict, glossary: dict):
        super().__init__()
        self.cfg      = cfg
        self.cache    = cache
        self.glossary = glossary
        self.running  = False
        self.last_pos = 0
        self.recent: list[str] = []
        self._lock = threading.Lock()

    def run(self):
        self.running = True
        log_path = self.cfg["log_path"]
        api_key  = self.cfg["api_key"]
        self.last_pos = os.path.getsize(log_path)

        while self.running:
            try:
                size = os.path.getsize(log_path)
                if size > self.last_pos:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self.last_pos)
                        lines = f.readlines()
                        self.last_pos = f.tell()

                    pending = []
                    for line in lines:
                        result = self._parse_line(line.strip())
                        if result is None:
                            continue
                        time_str, ch_key, speaker, message = result

                        if is_korean(message):
                            self.new_message.emit(time_str, ch_key, speaker, message, None)
                        elif message.lower() in QUICK_CACHE:
                            self.new_message.emit(time_str, ch_key, speaker, message,
                                                  QUICK_CACHE[message.lower()])
                        elif message in self.cache:
                            self.new_message.emit(time_str, ch_key, speaker, message,
                                                  self.cache[message])
                        else:
                            pending.append((time_str, ch_key, speaker, message))

                    if pending:
                        self._translate_parallel(pending, api_key)

            except Exception as e:
                self.status.emit(f"오류: {e}")
            time.sleep(0.05)

    def _parse_line(self, line: str):
        m = LOG_PATTERN.match(line)
        if not m:
            return None
        _ts, time_str, ch_str, speaker, message = m.groups()
        speaker = speaker.strip()
        message = message.strip().strip('"')
        # ESO 색상 코드 제거
        message = re.sub(r'\|c[0-9a-fA-F]{6}', '', message)
        message = re.sub(r'\|r', '', message)
        message = re.sub(r'\|H[^|]*\|h([^|]*)\|h', r'\1', message)
        message = re.sub(r'\|t[^|]*\|t', '', message)
        message = message.strip()
        if not message or is_broken(message):
            return None
        try:
            ch_num = int(ch_str)
        except ValueError:
            ch_num = 0
        ch_key = get_channel(ch_num)
        if not self.cfg["channels"].get(ch_key, True):
            return None
        # 내 채팅 필터
        if self.cfg.get("hide_my_chat", False):
            my_name = self.cfg.get("my_character_name", "").strip()
            if my_name and speaker.strip() == my_name:
                return None
        return time_str, ch_key, speaker, message

    def _translate_parallel(self, pending: list, api_key: str):
        def translate_one(item):
            time_str, ch_key, speaker, message = item
            with self._lock:
                ctx = " ".join(self.recent[-3:])
            translated = translate_to_korean(message, api_key, self.glossary, ctx)
            with self._lock:
                self.cache[message] = translated
                self.recent.append(message)
                if len(self.recent) > 5:
                    self.recent.pop(0)
            return time_str, ch_key, speaker, message, translated

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(translate_one, item) for item in pending]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    time_str, ch_key, speaker, message, translated = fut.result()
                    self.new_message.emit(time_str, ch_key, speaker, message, translated)
                    self.cache_count.emit(len(self.cache))
                except Exception as e:
                    self.status.emit(f"번역오류: {e}")

    def stop(self):
        self.running = False

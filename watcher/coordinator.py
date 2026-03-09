"""
WatchThread — 파일 감시 + parser/dispatcher/pipeline 연결.
QThread를 상속해 UI 시그널 emit.

단일 책임: 파일 폴링 + 컴포넌트 조합.
파싱은 parser, 번역 라우팅은 dispatcher가 담당.
"""
from __future__ import annotations
import os
import time

from PyQt6.QtCore import QThread, pyqtSignal

from core.models import ChatMessage, TranslationResult
from watcher.parser     import parse_line
from watcher.dispatcher import Dispatcher


class WatchThread(QThread):
    # (time_str, channel, speaker, original, translated | None)
    new_message = pyqtSignal(str, str, str, str, object)
    status      = pyqtSignal(str)
    cache_count = pyqtSignal(int)

    def __init__(self, cfg: dict, cache, glossary: dict, debug: bool = False):
        super().__init__()
        self._cfg     = cfg
        self._cache   = cache
        self._debug   = debug
        self.running  = False

        # 파일 위치 추적
        self._last_pos   = 0
        self._last_inode = None

        # Dispatcher 생성 — on_result 콜백으로 시그널 emit
        self._dispatcher = Dispatcher(
            cfg       = cfg,
            cache     = cache,
            glossary  = glossary,
            on_result = self._on_result,
            debug     = debug,
        )

    # ── QThread 진입점 ────────────────────────────────────────

    def run(self) -> None:
        self.running = True
        log_path = self._cfg["log_path"]
        api_key  = self._cfg["api_key"]

        # 시작 위치: 현재 파일 끝 (과거 로그 무시)
        try:
            stat = os.stat(log_path)
            self._last_pos   = stat.st_size
            self._last_inode = stat.st_ino
        except Exception:
            self._last_pos   = 0
            self._last_inode = None

        while self.running:
            try:
                self._poll(log_path, api_key)
            except Exception as e:
                self.status.emit(f"오류: {e}")
            time.sleep(0.05)

    def stop(self) -> None:
        self.running = False
        self._dispatcher.shutdown()

    # ── 파일 폴링 ─────────────────────────────────────────────

    def _poll(self, log_path: str, api_key: str) -> None:
        try:
            stat = os.stat(log_path)
        except FileNotFoundError:
            return

        size  = stat.st_size
        inode = stat.st_ino

        # 파일 재생성 / 로그 회전 감지
        if inode != self._last_inode or size < self._last_pos:
            self.status.emit("로그 파일 재생성 감지 — 위치 초기화")
            self._last_pos   = size
            self._last_inode = inode
            return

        if size <= self._last_pos:
            self._dispatcher.flush_if_ready(api_key)
            return

        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self._last_pos)
            lines = f.readlines()
            self._last_pos = f.tell()

        self._last_inode = inode

        for line in lines:
            msg = parse_line(line, self._cfg)
            if msg is None:
                continue
            self._dispatcher.feed(msg)

        self._dispatcher.flush_if_ready(api_key)

    # ── 결과 콜백 (Dispatcher → UI) ──────────────────────────

    def _on_result(self, msg: ChatMessage, result: TranslationResult) -> None:
        translated = None if result.source == "korean" else result.translated
        self.new_message.emit(
            msg.time_str,
            msg.channel,
            msg.speaker,
            msg.text,
            translated,
        )
        self.cache_count.emit(len(self._cache))

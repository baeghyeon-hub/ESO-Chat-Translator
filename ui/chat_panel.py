import time

from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QFont, QTextCursor
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QTextBrowser, QVBoxLayout

from constants import CHANNEL_INFO
from ui.base_panel import FloatingPanel

# 재시도 앵커 prefix — original 텍스트를 URL-encode 없이 구분자로 감쌈
_RETRY_SCHEME = "retry"


class ChatPanel(FloatingPanel):
    # 재시도 요청: (original_text, ch_key)
    retry_requested = pyqtSignal(str, str)

    def __init__(self, cfg: dict):
        self._user_bg_alpha = int(cfg.get("chat_opacity", 0.75) * 255)
        super().__init__("chat", cfg, bg_color=(13, 13, 26),
                         bg_alpha=self._user_bg_alpha, collapsible=False)
        self._msg_times: list[tuple[float, int]] = []
        self._faded        = False
        self._was_hovering = False
        # 앵커 ID → (original, ch_key) 매핑
        self._retry_map: dict[str, tuple[str, str]] = {}
        self._retry_seq = 0
        self._build()
        self._start_timers()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        self.text = QTextBrowser()
        self.text.setOpenLinks(False)
        self.text.anchorClicked.connect(self._on_anchor)
        self.text.setStyleSheet("""
            QTextBrowser{
                background:transparent;color:#e0e0e0;border:none;
                font-family:'맑은 고딕';font-size:11px;
                selection-background-color:#533483;
            }
            QScrollBar:vertical{background:#0d0d1a;width:8px;border-radius:4px;}
            QScrollBar::handle:vertical{background:#3f3f46;border-radius:4px;min-height:20px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        self._opacity_effect = QGraphicsOpacityEffect()
        self._opacity_effect.setOpacity(1.0)
        self.text.setGraphicsEffect(self._opacity_effect)
        lay.addWidget(self.text)

    def _start_timers(self):
        self._fade_timer = QTimer()
        self._fade_timer.timeout.connect(self._check_fade)
        self._fade_timer.start(500)

        self._hover_timer = QTimer()
        self._hover_timer.timeout.connect(self._check_hover)
        self._hover_timer.start(100)

    # ── 앵커 클릭 처리 ───────────────────────────────────────
    def _on_anchor(self, url: QUrl):
        if url.scheme() == _RETRY_SCHEME:
            key = url.host()
            if key in self._retry_map:
                original, ch_key = self._retry_map[key]
                self.retry_requested.emit(original, ch_key)

    # ── 메시지 추가 ───────────────────────────────────────────
    def append(self, time_str: str, ch_key: str, speaker: str,
               original: str, translated, show_orig: bool, font_size: int):
        info = CHANNEL_INFO.get(ch_key, {"color": "#e0e0e0", "label": ch_key})
        c = self.text.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        block_pos = c.position()

        def ins(text, color, bold=False, size=None, href=None):
            fmt = c.charFormat()
            fmt.setForeground(QColor(color))
            f = QFont("맑은 고딕", size or font_size)
            f.setBold(bold)
            fmt.setFont(f)
            if href:
                fmt.setAnchor(True)
                fmt.setAnchorHref(href)
                fmt.setFontUnderline(True)
            else:
                fmt.setAnchor(False)
                fmt.setFontUnderline(False)
            c.setCharFormat(fmt)
            c.insertText(text)

        is_error = isinstance(translated, str) and translated.startswith(
            ("[오류", "[시간초과]", "[연결오류]", "[레이트리밋]")
        )

        ins(f"[{time_str}] ", "#444466", size=9)
        ins(f"[{info['label']}] ", info["color"], bold=True)
        ins(f"{speaker}: ", info["color"])

        if is_error:
            ins(f"{translated} ", "#ff6b6b")
            # 재시도 앵커 링크 삽입
            key = f"r{self._retry_seq}"
            self._retry_seq += 1
            self._retry_map[key] = (original, ch_key)
            ins("↻재시도", "#60a5fa",
                href=f"{_RETRY_SCHEME}://{key}")
            ins("\n", "#ffffff")
        elif translated:
            ins(f"{translated}\n", "#ffffff")
            if show_orig:
                ins(f"      ↳ {original}\n", "#555577", size=font_size - 1)
        else:
            ins(f"{original}\n", "#e0e0e0")

        self.text.setTextCursor(c)
        self.text.ensureCursorVisible()
        self._msg_times.append((time.time(), block_pos))

        # 200줄 초과 시 앞부분 삭제 (오래된 retry_map 항목도 정리)
        doc = self.text.document()
        while doc.lineCount() > 200:
            cur = QTextCursor(doc)
            cur.movePosition(QTextCursor.MoveOperation.Start)
            cur.movePosition(QTextCursor.MoveOperation.Down,
                             QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
        # retry_map 크기 제한 (최근 100개만 유지)
        if len(self._retry_map) > 100:
            oldest = list(self._retry_map.keys())[:50]
            for k in oldest:
                del self._retry_map[k]

    def wake_up(self):
        self._faded = False
        if not self._was_hovering:
            self.bg_alpha = self._user_bg_alpha
            self._opacity_effect.setOpacity(1.0)
            self.update()

    def clear(self):
        self.text.clear()
        self._msg_times.clear()
        self._retry_map.clear()

    # ── 투명도 ────────────────────────────────────────────────
    def set_opacity(self, val_0_100: int):
        self._user_bg_alpha = max(0, int(val_0_100 * 2.55))
        if not self._faded:
            self.bg_alpha = self._user_bg_alpha
            # 텍스트도 bg_alpha에 비례해서 함께 투명해짐
            opacity = val_0_100 / 100.0
            self._opacity_effect.setOpacity(opacity)
            self.update()

    # ── 페이드 / 호버 타이머 ──────────────────────────────────
    def _check_hover(self):
        pos = QCursor.pos()
        hovering = self.geometry().contains(pos)
        if hovering and not self._was_hovering:
            self._was_hovering = True
            self.bg_alpha = self._user_bg_alpha
            self._opacity_effect.setOpacity(1.0)
            self.update()
        elif not hovering and self._was_hovering:
            self._was_hovering = False
            if self._faded:
                self.bg_alpha = max(10, self._user_bg_alpha // 6)
                self._opacity_effect.setOpacity(0.08)
                self.update()

    def _check_fade(self):
        fade_sec = self.cfg.get("fade_seconds", 0)
        if not fade_sec or self._was_hovering or not self._msg_times:
            return
        now = time.time()
        age = now - self._msg_times[-1][0]
        if age < fade_sec:
            if self._faded:
                self._faded = False
                self.bg_alpha = self._user_bg_alpha
                self._opacity_effect.setOpacity(1.0)
                self.update()
            return
        fade_ratio = min(1.0, (age - fade_sec) / 5.0)
        self.bg_alpha = max(0, int(self._user_bg_alpha * (1.0 - fade_ratio)))
        self._opacity_effect.setOpacity(max(0.0, 1.0 - fade_ratio))
        self.update()
        self._faded = (fade_ratio >= 1.0)

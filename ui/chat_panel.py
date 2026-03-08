import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QTextCursor
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QTextEdit, QVBoxLayout

from constants import CHANNEL_INFO
from ui.base_panel import FloatingPanel


class ChatPanel(FloatingPanel):
    def __init__(self, cfg: dict):
        self._user_bg_alpha = int(cfg.get("chat_opacity", 0.75) * 255)
        super().__init__("chat", cfg, bg_color=(13, 13, 26),
                         bg_alpha=self._user_bg_alpha, collapsible=False)
        self._msg_times: list[tuple[float, int]] = []
        self._faded       = False
        self._was_hovering = False
        self._build()
        self._start_timers()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("""
            QTextEdit{
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

    # ── 메시지 추가 ───────────────────────────────────────────
    def append(self, time_str: str, ch_key: str, speaker: str,
               original: str, translated, show_orig: bool, font_size: int):
        info = CHANNEL_INFO.get(ch_key, {"color": "#e0e0e0", "label": ch_key})
        c = self.text.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        block_pos = c.position()

        def ins(text, color, bold=False, size=None):
            fmt = c.charFormat()
            fmt.setForeground(QColor(color))
            f = QFont("맑은 고딕", size or font_size)
            f.setBold(bold)
            fmt.setFont(f)
            c.setCharFormat(fmt)
            c.insertText(text)

        ins(f"[{time_str}] ", "#444466", size=9)
        ins(f"[{info['label']}] ", info["color"], bold=True)
        ins(f"{speaker}: ", info["color"])
        if translated:
            ins(f"{translated}\n", "#ffffff")
            if show_orig:
                ins(f"      ↳ {original}\n", "#555577", size=font_size - 1)
        else:
            ins(f"{original}\n", "#e0e0e0")

        self.text.setTextCursor(c)
        self.text.ensureCursorVisible()
        self._msg_times.append((time.time(), block_pos))

        # 200줄 초과 시 앞부분 삭제
        doc = self.text.document()
        while doc.lineCount() > 200:
            cur = QTextCursor(doc)
            cur.movePosition(QTextCursor.MoveOperation.Start)
            cur.movePosition(QTextCursor.MoveOperation.Down,
                             QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()

    def wake_up(self):
        self._faded = False
        if not self._was_hovering:
            self.bg_alpha = self._user_bg_alpha
            self._opacity_effect.setOpacity(1.0)
            self.update()

    def clear(self):
        self.text.clear()
        self._msg_times.clear()

    # ── 투명도 ────────────────────────────────────────────────
    def set_opacity(self, val_0_100: int):
        self._user_bg_alpha = max(20, int(val_0_100 * 2.55))
        if not self._faded:
            self.bg_alpha = self._user_bg_alpha
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

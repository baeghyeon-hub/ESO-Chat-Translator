from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSlider

from ui.base_panel import FloatingPanel


class TitlePanel(FloatingPanel):
    close_requested    = pyqtSignal()
    minimize_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    opacity_changed    = pyqtSignal(int)
    fade_changed       = pyqtSignal(int)
    passthrough_toggled = pyqtSignal()

    def __init__(self, cfg: dict):
        super().__init__("title", cfg, bg_color=(15, 15, 25), bg_alpha=230,
                         collapsible=False)
        self._restore_btns: dict = {}
        self._build()

    def _build(self):
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(10, 0, 8, 0)
        self._lay.setSpacing(4)

        self.title_lbl = QLabel("⚔  ESO 번역기")
        self.title_lbl.setStyleSheet(
            "color:#e4e4e7;font-family:'맑은 고딕';font-size:13px;"
            "font-weight:bold;background:transparent;")
        self._lay.addWidget(self.title_lbl)

        # 복원 버튼 영역 (동적)
        self._restore_area = QHBoxLayout()
        self._restore_area.setSpacing(3)
        self._lay.addLayout(self._restore_area)

        self._lay.addStretch()

        self.orig_cb = QCheckBox("원문")
        self.orig_cb.setChecked(self.cfg.get("show_original", False))
        self.orig_cb.setStyleSheet(
            "color:#71717a;background:transparent;font-size:11px;")
        self._lay.addWidget(self.orig_cb)

        # 페이드 슬라이더
        fade_lbl = QLabel("페이드")
        fade_lbl.setStyleSheet("color:#52525b;font-size:10px;background:transparent;")
        self._lay.addWidget(fade_lbl)

        self.fade_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_slider.setRange(0, 60)
        self.fade_slider.setValue(self.cfg.get("fade_seconds", 10))
        self.fade_slider.setFixedWidth(70)
        self.fade_slider.setToolTip("0=끔 / N초 후 채팅 페이드")
        self.fade_slider.setStyleSheet("""
            QSlider::groove:horizontal{height:4px;background:#3f2a1a;border-radius:2px;}
            QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;
                background:#f97316;border-radius:6px;}
            QSlider::sub-page:horizontal{background:#f97316;border-radius:2px;}
        """)
        self._lay.addWidget(self.fade_slider)

        self.fade_val_lbl = QLabel(self._fade_label(self.cfg.get("fade_seconds", 10)))
        self.fade_val_lbl.setStyleSheet(
            "color:#f97316;font-size:10px;background:transparent;min-width:28px;")
        self._lay.addWidget(self.fade_val_lbl)
        self.fade_slider.valueChanged.connect(self._on_fade_change)

        # 투명도 슬라이더
        op_lbl = QLabel("투명도")
        op_lbl.setStyleSheet("color:#52525b;font-size:10px;background:transparent;")
        self._lay.addWidget(op_lbl)

        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(10, 100)
        self.op_slider.setValue(int(self.cfg.get("chat_opacity", 0.75) * 100))
        self.op_slider.setFixedWidth(80)
        self.op_slider.setStyleSheet("""
            QSlider::groove:horizontal{height:4px;background:#1e3a5f;border-radius:2px;}
            QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;
                background:#3b82f6;border-radius:6px;}
            QSlider::sub-page:horizontal{background:#3b82f6;border-radius:2px;}
        """)
        self.op_slider.valueChanged.connect(self.opacity_changed)
        self._lay.addWidget(self.op_slider)

        # 투과 버튼
        self.passthrough_btn = QPushButton("🖱 투과")
        self.passthrough_btn.setFixedSize(54, 26)
        self.passthrough_btn.setCheckable(True)
        self.passthrough_btn.setToolTip("클릭 투과 ON/OFF")
        self.passthrough_btn.setStyleSheet("""
            QPushButton{background:#27272a;color:#a1a1aa;border:none;border-radius:4px;
                font-family:'맑은 고딕';font-size:10px;}
            QPushButton:hover{background:#3f3f46;}
            QPushButton:checked{background:#c2410c;color:white;font-weight:bold;}
        """)
        self.passthrough_btn.clicked.connect(self.passthrough_toggled)
        self._lay.addWidget(self.passthrough_btn)

        # ⚙ ─ ✕ 버튼
        for text, color, signal in [
            ("⚙", "#71717a", self.settings_requested),
            ("─", "#71717a", self.minimize_requested),
            ("✕", "#ef4444", self.close_requested),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"""
                QPushButton{{background:#27272a;color:{color};border:none;
                    border-radius:6px;font-size:14px;}}
                QPushButton:hover{{background:#3f3f46;}}
            """)
            btn.clicked.connect(signal)
            self._lay.addWidget(btn)

    def _fade_label(self, v: int) -> str:
        return "끔" if v == 0 else f"{v}s"

    def _on_fade_change(self, v: int):
        self.fade_val_lbl.setText(self._fade_label(v))
        self.fade_changed.emit(v)

    def set_passthrough_state(self, active: bool):
        self.passthrough_btn.setChecked(active)
        if active:
            self.title_lbl.setText("🔒 투과 ON")
            self.title_lbl.setStyleSheet(
                "color:#f97316;font-weight:bold;font-size:12px;"
                "font-family:'맑은 고딕';background:transparent;")
        else:
            self.title_lbl.setText("⚔  ESO 번역기")
            self.title_lbl.setStyleSheet(
                "color:#4ecca3;font-weight:bold;font-size:12px;"
                "font-family:'맑은 고딕';background:transparent;")

    # ── 패널 복원 버튼 동적 추가/제거 ────────────────────────
    def add_restore_btn(self, panel, on_click):
        key = panel.panel_key
        if key in self._restore_btns:
            return
        label = panel._collapse_label or key
        btn = QPushButton(f"↩ {label}")
        btn.setFixedHeight(22)
        btn.setToolTip(f"{label} 패널 복원")
        btn.setStyleSheet("""
            QPushButton{background:#1e3a5f;color:#93c5fd;border:none;
                border-radius:4px;font-family:'맑은 고딕';font-size:10px;padding:0 7px;}
            QPushButton:hover{background:#2563eb;color:white;}
        """)
        btn.clicked.connect(on_click)
        self._restore_area.addWidget(btn)
        self._restore_btns[key] = btn

    def remove_restore_btn(self, panel):
        key = panel.panel_key
        btn = self._restore_btns.pop(key, None)
        if btn:
            self._restore_area.removeWidget(btn)
            btn.deleteLater()

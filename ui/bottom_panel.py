from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from ui.base_panel import FloatingPanel


class BottomPanel(FloatingPanel):
    start_requested = pyqtSignal()
    clear_requested = pyqtSignal()

    def __init__(self, cfg: dict):
        super().__init__("bottom", cfg, bg_color=(15, 15, 25), bg_alpha=220,
                         collapsible=True, collapse_label="컨트롤")
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 8, 0)
        lay.setSpacing(6)

        self._make_collapse_btn(lay)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#2a2a3e;")
        lay.addWidget(sep)

        self.start_btn = QPushButton("▶  번역 시작")
        self.start_btn.setFixedHeight(30)
        self.start_btn.setStyleSheet("""
            QPushButton{background:#16a34a;color:white;border:none;border-radius:6px;
                font-family:'맑은 고딕';font-size:12px;font-weight:bold;padding:0 12px;}
            QPushButton:hover{background:#15803d;}
        """)
        self.start_btn.clicked.connect(self.start_requested)
        lay.addWidget(self.start_btn)

        clear_btn = QPushButton("지우기")
        clear_btn.setFixedHeight(30)
        clear_btn.setStyleSheet("""
            QPushButton{background:#27272a;color:#aaaacc;border:none;border-radius:6px;
                font-family:'맑은 고딕';font-size:11px;padding:0 10px;}
            QPushButton:hover{background:#3f3f46;}
        """)
        clear_btn.clicked.connect(self.clear_requested)
        lay.addWidget(clear_btn)

        self.status_lbl = QLabel("대기 중...")
        self.status_lbl.setStyleSheet(
            "color:#52525b;font-size:11px;background:transparent;font-family:'Consolas';")
        lay.addWidget(self.status_lbl)

        lay.addStretch()

        self.cache_lbl = QLabel("캐시: 0")
        self.cache_lbl.setStyleSheet(
            "color:#3f3f46;font-size:10px;background:transparent;font-family:'Consolas';")
        lay.addWidget(self.cache_lbl)

    def set_running(self, running: bool):
        if running:
            self.start_btn.setText("⏹  중지")
            self.start_btn.setStyleSheet("""
                QPushButton{background:#dc2626;color:white;border:none;border-radius:6px;
                    font-family:'맑은 고딕';font-size:12px;font-weight:bold;padding:0 12px;}
                QPushButton:hover{background:#b91c1c;}""")
            self.status_lbl.setText("번역 중...")
        else:
            self.start_btn.setText("▶  번역 시작")
            self.start_btn.setStyleSheet("""
                QPushButton{background:#16a34a;color:white;border:none;border-radius:6px;
                    font-family:'맑은 고딕';font-size:12px;font-weight:bold;padding:0 12px;}
                QPushButton:hover{background:#15803d;}""")
            self.status_lbl.setText("중지됨")

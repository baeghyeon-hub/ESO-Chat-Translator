from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton

from ui.base_panel import FloatingPanel


class InputPanel(FloatingPanel):
    translate_requested = pyqtSignal(str)   # 입력 텍스트 전달

    def __init__(self, cfg: dict):
        super().__init__("input", cfg, bg_color=(15, 15, 25), bg_alpha=220,
                         collapsible=True, collapse_label="입력")
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(6)

        self._make_collapse_btn(lay)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#2a2a3e;")
        lay.addWidget(sep)

        lbl = QLabel("한→영")
        lbl.setStyleSheet(
            "color:#3b82f6;font-family:'맑은 고딕';font-size:11px;"
            "font-weight:bold;background:transparent;")
        lay.addWidget(lbl)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("한국어 입력 후 Enter...")
        self.entry.setStyleSheet("""
            QLineEdit{background:#0f0f18;color:white;border:1px solid #2a2a2e;
                border-radius:6px;padding:4px 8px;font-family:'맑은 고딕';font-size:11px;}
            QLineEdit:focus{border:1px solid #3b82f6;}
        """)
        self.entry.returnPressed.connect(self._emit)
        lay.addWidget(self.entry)

        btn = QPushButton("번역+복사")
        btn.setFixedHeight(30)
        btn.setStyleSheet("""
            QPushButton{background:#312e81;color:white;border:none;border-radius:6px;
                font-family:'맑은 고딕';font-size:11px;padding:0 10px;}
            QPushButton:hover{background:#3730a3;}
        """)
        btn.clicked.connect(self._emit)
        lay.addWidget(btn)

        self.result_lbl = QLineEdit("")
        self.result_lbl.setReadOnly(True)
        self.result_lbl.setPlaceholderText("번역 결과...")
        self.result_lbl.setStyleSheet("""
            QLineEdit{color:#93c5fd;font-size:10px;background:transparent;
                border:none;font-family:'맑은 고딕';padding:0;}
            QLineEdit:focus{border-bottom:1px solid #3b82f6;}
        """)
        lay.addWidget(self.result_lbl)

    def _emit(self):
        text = self.entry.text().strip()
        if text:
            self.translate_requested.emit(text)

    def show_result(self, result: str):
        self.result_lbl.setText(result)
        self.entry.clear()

    def show_status(self, msg: str):
        self.result_lbl.setText(msg)

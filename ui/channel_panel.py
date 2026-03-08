from PyQt6.QtWidgets import QCheckBox, QFrame, QHBoxLayout

from constants import CHANNEL_INFO
from ui.base_panel import FloatingPanel


class ChannelPanel(FloatingPanel):
    def __init__(self, cfg: dict):
        super().__init__("channel", cfg, bg_color=(15, 15, 25), bg_alpha=220,
                         collapsible=True, collapse_label="채널")
        self.ch_vars: dict[str, QCheckBox] = {}
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 10, 0)
        lay.setSpacing(6)

        self._make_collapse_btn(lay)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#2a2a3e;")
        lay.addWidget(sep)

        for key, info in CHANNEL_INFO.items():
            cb = QCheckBox(info["label"])
            cb.setChecked(self.cfg["channels"].get(key, True))
            cb.setStyleSheet(f"""
                QCheckBox{{color:{info['color']};background:transparent;
                    font-family:'맑은 고딕';font-size:11px;spacing:4px;}}
                QCheckBox::indicator{{width:16px;height:16px;border-radius:3px;
                    border:1px solid {info['badge']};background:#18181b;}}
                QCheckBox::indicator:checked{{background:{info['badge']};}}
            """)
            self.ch_vars[key] = cb
            lay.addWidget(cb)

        lay.addStretch()

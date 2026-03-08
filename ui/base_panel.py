from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QPushButton, QSizeGrip, QWidget

BASE_FLAGS = (
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool
)


class FloatingPanel(QWidget):
    """드래그 가능한 반투명 패널 베이스."""

    def __init__(self, panel_key: str, cfg: dict,
                 bg_color: tuple = (18, 18, 27), bg_alpha: int = 220,
                 collapsible: bool = True, collapse_label: str = ""):
        super().__init__()
        self.panel_key       = panel_key
        self.cfg             = cfg
        self.bg_color        = bg_color
        self.bg_alpha        = bg_alpha
        self._drag_pos       = None
        self._collapsed      = False
        self._collapse_label = collapse_label
        self._collapsible    = collapsible
        self._mini_btn       = None
        self._on_collapse_cb = None
        self._on_expand_cb   = None

        p = cfg["panels"][panel_key]
        self.setWindowFlags(BASE_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(p["x"], p["y"], p["w"], p["h"])

        grip = QSizeGrip(self)
        grip.setFixedSize(12, 12)
        grip.setStyleSheet("background:transparent;")
        self._grip = grip
        self._grip.raise_()

    # ── 최소화 / 복원 ─────────────────────────────────────────
    def _make_collapse_btn(self, parent_layout):
        btn = QPushButton("─")
        btn.setFixedSize(22, 22)
        btn.setToolTip("패널 숨기기 (타이틀바에서 복원)")
        btn.setStyleSheet("""
            QPushButton{background:#27272a;color:#71717a;border:none;
                border-radius:5px;font-size:11px;}
            QPushButton:hover{background:#3f3f46;color:#e11d48;}
        """)
        btn.clicked.connect(self.do_collapse)
        self._mini_btn = btn
        parent_layout.addWidget(btn)
        return btn

    def do_collapse(self):
        if not self._collapsible:
            return
        self._collapsed = True
        self.hide()
        if self._on_collapse_cb:
            self._on_collapse_cb(self)

    def do_expand(self):
        self._collapsed = False
        self.show()
        if self._on_expand_cb:
            self._on_expand_cb(self)

    def set_collapse_callbacks(self, on_collapse, on_expand):
        self._on_collapse_cb = on_collapse
        self._on_expand_cb   = on_expand

    # ── 윈도우 플래그 안전 교체 ───────────────────────────────
    def apply_flags(self, extra_flags=None):
        """BASE_FLAGS에 extra_flags를 더해 안전하게 교체. collapsed 상태 유지."""
        flags = BASE_FLAGS
        if extra_flags:
            flags |= extra_flags
        self.setWindowFlags(flags)
        if not self._collapsed:
            self.show()

    # ── Qt 이벤트 ─────────────────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, '_grip') and self._grip:
            self._grip.move(self.width() - 12, self.height() - 12)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r, g, b = self.bg_color
        p.setBrush(QColor(r, g, b, self.bg_alpha))
        p.setPen(QColor(50, 50, 60, 180))
        p.drawRoundedRect(self.rect(), 10, 10)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def set_opacity(self, alpha_0_255: int):
        self.bg_alpha = alpha_0_255
        self.update()

    def save_geometry(self):
        g = self.geometry()
        self.cfg["panels"][self.panel_key].update(
            {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()}
        )

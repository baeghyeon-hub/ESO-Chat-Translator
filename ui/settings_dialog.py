import threading
from pathlib import Path

import requests
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QFrame,
)

DEEPL_USAGE_URL = "https://api-free.deepl.com/v2/usage"


def _find_chatlog() -> str:
    candidates = []
    docs = Path.home() / "Documents" / "Elder Scrolls Online"
    if docs.exists():
        for pattern in ("Chat.log", "ChatLog.log", "chat.log", "chatlog.log"):
            for log in docs.rglob(pattern):
                candidates.append(log)
    if candidates:
        return str(max(candidates, key=lambda p: p.stat().st_mtime))
    return ""


def _fetch_usage(api_key: str) -> dict:
    try:
        r = requests.get(
            DEEPL_USAGE_URL,
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            timeout=6,
        )
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "시간 초과"}
    except Exception as e:
        return {"error": str(e)}


class _Bridge(QObject):
    result_ready = pyqtSignal(dict)


class SettingsDialog(QWidget):
    saved = pyqtSignal(dict)

    _LBL = "color:#a1a1aa;font-family:'맑은 고딕';font-size:11px;"
    _INP = ("background:#27272a;color:white;border:1px solid #3f3f46;"
            "border-radius:4px;padding:6px;font-family:'맑은 고딕';")
    _BTN = ("background:#3f3f46;color:white;border:none;"
            "border-radius:4px;padding:6px 12px;font-family:'맑은 고딕';font-size:11px;")

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self._bridge = _Bridge()
        self._bridge.result_ready.connect(self._on_usage_result)
        self._api_visible = False

        self.setWindowTitle("설정")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background:#18181b;color:#e4e4e7;")
        self.setMinimumWidth(480)
        self.resize(480, 410)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        # API 키
        lay.addWidget(self._lbl("DeepL API 키"))
        api_row = QHBoxLayout()
        self.api_edit = QLineEdit(self.cfg.get("api_key", ""))
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_edit.setStyleSheet(self._INP)
        api_row.addWidget(self.api_edit)
        self.eye_btn = QPushButton("👁 표시")
        self.eye_btn.setFixedWidth(70)
        self.eye_btn.setStyleSheet(self._BTN)
        self.eye_btn.clicked.connect(self._toggle_api_visibility)
        api_row.addWidget(self.eye_btn)
        lay.addLayout(api_row)

        # 테스트 버튼 + 결과
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("🔌 API 연결 테스트")
        self.test_btn.setStyleSheet(
            "background:#0e7490;color:white;border:none;border-radius:4px;"
            "padding:6px 14px;font-family:'맑은 고딕';font-size:11px;")
        self.test_btn.clicked.connect(self._run_test)
        test_row.addWidget(self.test_btn)
        self.test_lbl = QLabel("─")
        self.test_lbl.setStyleSheet("color:#52525b;font-size:11px;font-family:'맑은 고딕';")
        test_row.addWidget(self.test_lbl)
        test_row.addStretch()
        lay.addLayout(test_row)

        # 사용량
        usage_row = QHBoxLayout()
        usage_title = QLabel("사용량")
        usage_title.setStyleSheet("color:#a1a1aa;font-size:11px;font-family:'맑은 고딕';min-width:40px;")
        usage_row.addWidget(usage_title)
        self.usage_lbl = QLabel("테스트 버튼을 눌러 확인하세요")
        self.usage_lbl.setStyleSheet("color:#71717a;font-size:11px;font-family:'Consolas';")
        usage_row.addWidget(self.usage_lbl)
        usage_row.addStretch()
        lay.addLayout(usage_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#27272a;")
        lay.addWidget(sep)

        # Chat.log 경로
        lay.addWidget(self._lbl("Chat.log 경로"))
        row = QHBoxLayout()
        self.log_edit = QLineEdit(self.cfg.get("log_path", ""))
        self.log_edit.setStyleSheet(self._INP)
        row.addWidget(self.log_edit)
        auto_btn = QPushButton("🔍 자동 찾기")
        auto_btn.setStyleSheet(self._BTN)
        auto_btn.clicked.connect(self._auto_find_log)
        row.addWidget(auto_btn)
        b1 = QPushButton("찾기")
        b1.setStyleSheet(self._BTN)
        b1.clicked.connect(self._browse_log)
        row.addWidget(b1)
        lay.addLayout(row)
        self.log_status_lbl = QLabel("")
        self.log_status_lbl.setStyleSheet("color:#71717a;font-size:10px;font-family:'맑은 고딕';")
        lay.addWidget(self.log_status_lbl)

        # 용어집 경로
        lay.addWidget(self._lbl("용어집 CSV 경로 (선택)"))
        row2 = QHBoxLayout()
        self.glossary_edit = QLineEdit(self.cfg.get("glossary_path", "eso_glossary.csv"))
        self.glossary_edit.setStyleSheet(self._INP)
        row2.addWidget(self.glossary_edit)
        b2 = QPushButton("찾기")
        b2.setStyleSheet(self._BTN)
        b2.clicked.connect(self._browse_glossary)
        row2.addWidget(b2)
        lay.addLayout(row2)

        hint = QLabel("※ English, Korean 두 열로 된 CSV 파일")
        hint.setStyleSheet("color:#52525b;font-size:10px;font-family:'맑은 고딕';")
        lay.addWidget(hint)

        lay.addStretch()

        save_btn = QPushButton("저장")
        save_btn.setStyleSheet(
            "background:#2563eb;color:white;border:none;border-radius:6px;"
            "padding:8px;font-size:13px;font-family:'맑은 고딕';")
        save_btn.clicked.connect(self._save)
        lay.addWidget(save_btn)

    def _toggle_api_visibility(self):
        self._api_visible = not self._api_visible
        if self._api_visible:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText("🙈 숨김")
        else:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setText("👁 표시")

    def _auto_find_log(self):
        self.log_status_lbl.setText("스캔 중...")
        path = _find_chatlog()
        if path:
            self.log_edit.setText(path)
            self.log_status_lbl.setText("✅ 자동 감지됨")
            self.log_status_lbl.setStyleSheet("color:#22c55e;font-size:10px;font-family:'맑은 고딕';")
        else:
            self.log_status_lbl.setText("❌ Chat.log를 찾지 못했습니다. 직접 찾기를 이용하세요.")
            self.log_status_lbl.setStyleSheet("color:#ef4444;font-size:10px;font-family:'맑은 고딕';")

    def _run_test(self):
        api = self.api_edit.text().strip()
        if not api:
            self.test_lbl.setText("❌ API 키를 먼저 입력하세요")
            self.test_lbl.setStyleSheet("color:#ef4444;font-size:11px;font-family:'맑은 고딕';")
            return
        self.test_btn.setEnabled(False)
        self.test_lbl.setText("확인 중...")
        self.test_lbl.setStyleSheet("color:#71717a;font-size:11px;font-family:'맑은 고딕';")
        self.usage_lbl.setText("─")
        threading.Thread(target=lambda: self._bridge.result_ready.emit(_fetch_usage(api)), daemon=True).start()

    def _on_usage_result(self, result: dict):
        self.test_btn.setEnabled(True)
        if "error" in result:
            self.test_lbl.setText(f"❌ 연결 실패: {result['error']}")
            self.test_lbl.setStyleSheet("color:#ef4444;font-size:11px;font-family:'맑은 고딕';")
            self.usage_lbl.setText("─")
            return
        used  = result.get("character_count", 0)
        limit = result.get("character_limit", 0)
        if limit > 0:
            pct   = used / limit * 100
            color = "#22c55e" if pct < 80 else ("#f97316" if pct < 95 else "#ef4444")
            self.test_lbl.setText("✅ 연결 성공")
            self.test_lbl.setStyleSheet("color:#22c55e;font-size:11px;font-family:'맑은 고딕';font-weight:bold;")
            self.usage_lbl.setText(f"{used:,} / {limit:,} 자  ({pct:.1f}%)  |  잔여 {limit - used:,} 자")
            self.usage_lbl.setStyleSheet(f"color:{color};font-size:11px;font-family:'Consolas';")
        else:
            self.test_lbl.setText("✅ 연결 성공")
            self.test_lbl.setStyleSheet("color:#22c55e;font-size:11px;font-family:'맑은 고딕';")

    def _browse_log(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "ESO Chat.log 선택",
            str(Path.home() / "Documents"), "Log files (*.log);;All files (*.*)")
        if path:
            self.log_edit.setText(path)
            self.log_status_lbl.setText("")

    def _browse_glossary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "용어집 CSV 선택",
            str(Path.cwd()), "CSV files (*.csv);;All files (*.*)")
        if path:
            self.glossary_edit.setText(path)

    def _save(self):
        self.cfg["api_key"]       = self.api_edit.text().strip()
        self.cfg["log_path"]      = self.log_edit.text().strip()
        self.cfg["glossary_path"] = self.glossary_edit.text().strip()
        self.saved.emit(self.cfg)
        self.close()

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(self._LBL)
        return l

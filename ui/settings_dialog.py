import threading
from pathlib import Path

import requests
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QFrame,
)

DEEPL_USAGE_FREE = "https://api-free.deepl.com/v2/usage"
DEEPL_USAGE_PRO  = "https://api.deepl.com/v2/usage"


def _find_usersettings() -> str:
    """ESO UserSettings.txt 경로 탐색"""
    docs = Path.home() / "Documents" / "Elder Scrolls Online"
    if docs.exists():
        for f in docs.rglob("UserSettings.txt"):
            return str(f)
    return ""


def _enable_chatlog(settings_path: str) -> bool:
    """UserSettings.txt 에서 CHAT_LOG_ENABLED 를 1로 설정. 없으면 추가."""
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.strip().upper().startswith("SET CHAT_LOG_ENABLED"):
                new_lines.append('SET CHAT_LOG_ENABLED "1"\n')
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append('\nSET CHAT_LOG_ENABLED "1"\n')

        with open(settings_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception:
        return False


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
            DEEPL_USAGE_FREE if api_key.strip().endswith(":fx") else DEEPL_USAGE_PRO,
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
        self.resize(480, 560)
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

        # ChatLog 미활성화 안내 (기본 숨김)
        chatlog_notice = QLabel("※ ESO에서 ChatLog 기능을 활성화해야 로그 파일이 생성됩니다.")
        chatlog_notice.setStyleSheet("color:#f97316;font-size:10px;font-family:'맑은 고딕';")
        chatlog_notice.setWordWrap(True)
        lay.addWidget(chatlog_notice)

        enable_row = QHBoxLayout()
        self.enable_btn = QPushButton("⚡ ChatLog 자동 활성화")
        self.enable_btn.setStyleSheet(
            "background:#7c3aed;color:white;border:none;border-radius:4px;"
            "padding:6px 14px;font-family:'맑은 고딕';font-size:11px;")
        self.enable_btn.clicked.connect(self._enable_chatlog_clicked)
        enable_row.addWidget(self.enable_btn)
        self.enable_lbl = QLabel("ESO 재시작 후 적용됩니다")
        self.enable_lbl.setStyleSheet("color:#52525b;font-size:10px;font-family:'맑은 고딕';")
        enable_row.addWidget(self.enable_lbl)
        enable_row.addStretch()
        lay.addLayout(enable_row)

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

        # 역방향 용어집 경로
        lay.addWidget(self._lbl("한→영 역방향 용어집 CSV (선택)"))
        row3 = QHBoxLayout()
        self.rev_glossary_edit = QLineEdit(self.cfg.get("reverse_glossary_path", "eso_glossary_reverse.csv"))
        self.rev_glossary_edit.setStyleSheet(self._INP)
        row3.addWidget(self.rev_glossary_edit)
        b3 = QPushButton("찾기")
        b3.setStyleSheet(self._BTN)
        b3.clicked.connect(self._browse_rev_glossary)
        row3.addWidget(b3)
        lay.addLayout(row3)
        hint2 = QLabel("※ Korean, English 두 열 / 한국어 여러 표현 → 하나의 영어 약어 매핑 가능")
        hint2.setStyleSheet("color:#52525b;font-size:10px;font-family:'맑은 고딕';")
        lay.addWidget(hint2)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color:#27272a;")
        lay.addWidget(sep2)

        # 내 채팅 필터
        my_row = QHBoxLayout()
        from PyQt6.QtWidgets import QCheckBox
        self.hide_my_cb = QCheckBox("내 채팅 숨기기")
        self.hide_my_cb.setChecked(self.cfg.get("hide_my_chat", False))
        self.hide_my_cb.setStyleSheet("color:#a1a1aa;font-family:'맑은 고딕';font-size:11px;")
        my_row.addWidget(self.hide_my_cb)
        self.my_name_edit = QLineEdit(self.cfg.get("my_character_name", ""))
        self.my_name_edit.setPlaceholderText("캐릭터명 입력 (예: Ricci Curvature)")
        self.my_name_edit.setStyleSheet(self._INP)
        my_row.addWidget(self.my_name_edit)
        lay.addLayout(my_row)
        my_hint = QLabel("※ 체크 시 해당 캐릭터의 채팅은 번역 패널에 표시되지 않습니다")
        my_hint.setStyleSheet("color:#52525b;font-size:10px;font-family:'맑은 고딕';")
        lay.addWidget(my_hint)

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
            self.enable_lbl.setText("ESO 재시작 후 적용됩니다")
        else:
            self.log_status_lbl.setText("❌ ChatLog 파일 없음 — 아래 버튼으로 활성화 후 ESO 재시작하세요.")
            self.log_status_lbl.setStyleSheet("color:#ef4444;font-size:10px;font-family:'맑은 고딕';")

    def _enable_chatlog_clicked(self):
        settings_path = _find_usersettings()
        if not settings_path:
            self.enable_lbl.setText("❌ UserSettings.txt 를 찾지 못했습니다")
            self.enable_lbl.setStyleSheet("color:#ef4444;font-size:10px;font-family:'맑은 고딕';")
            return
        ok = _enable_chatlog(settings_path)
        if ok:
            self.enable_lbl.setText("✅ 활성화 완료 — ESO 재시작 후 다시 자동 찾기를 눌러보세요")
            self.enable_lbl.setStyleSheet("color:#22c55e;font-size:10px;font-family:'맑은 고딕';")
        else:
            self.enable_lbl.setText("❌ 파일 수정 실패 — 직접 수정하거나 관리자 권한으로 실행하세요")
            self.enable_lbl.setStyleSheet("color:#ef4444;font-size:10px;font-family:'맑은 고딕';")

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

    def _browse_rev_glossary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "역방향 용어집 CSV 선택",
            str(Path.cwd()), "CSV files (*.csv);;All files (*.*)")
        if path:
            self.rev_glossary_edit.setText(path)

    def _browse_glossary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "용어집 CSV 선택",
            str(Path.cwd()), "CSV files (*.csv);;All files (*.*)")
        if path:
            self.glossary_edit.setText(path)

    def _save(self):
        self.cfg["api_key"]            = self.api_edit.text().strip()
        self.cfg["log_path"]           = self.log_edit.text().strip()
        self.cfg["glossary_path"]         = self.glossary_edit.text().strip()
        self.cfg["reverse_glossary_path"] = self.rev_glossary_edit.text().strip()
        self.cfg["my_character_name"]  = self.my_name_edit.text().strip()
        self.cfg["hide_my_chat"]       = self.hide_my_cb.isChecked()
        self.saved.emit(self.cfg)
        self.close()

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(self._LBL)
        return l

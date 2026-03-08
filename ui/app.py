import datetime
import threading
import time

from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from constants import get_channel
from core.cache import load_cache, save_cache
from core.config import load_config, save_config
from core.glossary import load_glossary
from core.log_watcher import WatchThread
from core.translator import translate_to_english
from ui.base_panel import BASE_FLAGS
from ui.bottom_panel import BottomPanel
from ui.channel_panel import ChannelPanel
from ui.chat_panel import ChatPanel
from ui.input_panel import InputPanel
from ui.settings_dialog import SettingsDialog
from ui.title_panel import TitlePanel

try:
    from pathlib import Path
    import os
    def find_log():
        for p in [
            Path.home() / "Documents" / "Elder Scrolls Online" / "live" / "Logs" / "Chat.log",
            Path(f"C:/Users/{os.environ.get('USERNAME', '')}/Documents/Elder Scrolls Online/live/Logs/Chat.log"),
        ]:
            if p.exists():
                return str(p)
        return ""
except Exception:
    def find_log(): return ""


class App(QObject):
    # 서브스레드 → 메인스레드 안전 전달용 시그널
    _input_result_ready = pyqtSignal(str, str)  # original_ko, result_en

    def __init__(self):
        super().__init__()
        self.cfg      = load_config()
        self.cache    = load_cache()
        self.glossary = load_glossary(self.cfg.get("glossary_path", "eso_glossary.csv"))
        self.watch_thread: WatchThread | None = None
        self._click_through = False

        # ── 패널 생성 ──────────────────────────────────────────
        self.title_p   = TitlePanel(self.cfg)
        self.channel_p = ChannelPanel(self.cfg)
        self.chat_p    = ChatPanel(self.cfg)
        self.bottom_p  = BottomPanel(self.cfg)
        self.input_p   = InputPanel(self.cfg)

        self._collapsible_panels = {
            "channel": self.channel_p,
            "bottom":  self.bottom_p,
            "input":   self.input_p,
        }

        # ── 시그널 연결 ────────────────────────────────────────
        self._connect_signals()

        # ── 초기 상태 설정 ─────────────────────────────────────
        if not self.cfg["log_path"]:
            found = find_log()
            if found:
                self.cfg["log_path"] = found

        for panel in self._collapsible_panels.values():
            panel.set_collapse_callbacks(
                on_collapse=self._on_panel_collapse,
                on_expand=self._on_panel_expand,
            )

        # ── 트레이 ────────────────────────────────────────────
        px = QPixmap(16, 16)
        px.fill(QColor("#4ecca3"))
        self.tray = QSystemTrayIcon(QIcon(px))
        tray_menu = QMenu()
        tray_menu.addAction("복원").triggered.connect(self._restore_all)
        tray_menu.addAction("종료").triggered.connect(self._on_close)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(
            lambda r: self._restore_all()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )

        # ── 패널 표시 및 collapsed 복원 ────────────────────────
        for p in self._all_panels():
            p.show()

        collapsed_state = self.cfg.get("collapsed", {})
        for key, panel in self._collapsible_panels.items():
            if collapsed_state.get(key, False):
                QTimer.singleShot(80, panel.do_collapse)

    # ── 패널 목록 헬퍼 ────────────────────────────────────────
    def _all_panels(self):
        return [self.title_p, self.channel_p, self.chat_p,
                self.bottom_p, self.input_p]

    def _passthrough_panels(self):
        """투과 대상 패널 (타이틀 제외)"""
        return [self.channel_p, self.chat_p, self.bottom_p]

    # ── 시그널 연결 ───────────────────────────────────────────
    def _connect_signals(self):
        t = self.title_p
        t.close_requested.connect(self._on_close)
        t.minimize_requested.connect(self._minimize_all)
        t.settings_requested.connect(self._open_settings)
        t.opacity_changed.connect(self._set_opacity)
        t.fade_changed.connect(self._set_fade)
        t.passthrough_toggled.connect(self._toggle_click_through)

        self.bottom_p.start_requested.connect(self._toggle_watch)
        self.bottom_p.clear_requested.connect(self.chat_p.clear)
        self.input_p.translate_requested.connect(self._translate_input)
        self._input_result_ready.connect(self._on_input_translated)

    # ── 투과 ──────────────────────────────────────────────────
    def _toggle_click_through(self):
        self._click_through = not self._click_through
        flag = Qt.WindowType.WindowTransparentForInput

        for p in self._passthrough_panels():
            p.apply_flags(flag if self._click_through else None)

        # 타이틀은 항상 클릭 가능
        self.title_p.setWindowFlags(BASE_FLAGS)
        self.title_p.show()
        self.title_p.set_passthrough_state(self._click_through)

    # ── 투명도 / 페이드 ───────────────────────────────────────
    def _set_opacity(self, val: int):
        self.cfg["chat_opacity"] = val / 100
        self.chat_p.set_opacity(val)
        self.chat_p._faded = False
        self.chat_p._opacity_effect.setOpacity(1.0)

    def _set_fade(self, seconds: int):
        self.cfg["fade_seconds"] = seconds
        self.chat_p.cfg["fade_seconds"] = seconds

    # ── 설정 다이얼로그 ───────────────────────────────────────
    def _open_settings(self):
        self.settings_dlg = SettingsDialog(self.cfg)
        self.settings_dlg.saved.connect(self._on_settings_saved)
        self.settings_dlg.show()

    def _on_settings_saved(self, new_cfg: dict):
        self.cfg.update(new_cfg)
        for key, cb in self.channel_p.ch_vars.items():
            self.cfg["channels"][key] = cb.isChecked()
        save_config(self.cfg)
        self.glossary = load_glossary(self.cfg.get("glossary_path", "eso_glossary.csv"))
        self.cache.clear()
        n = len(self.glossary)
        self.bottom_p.status_lbl.setText(f"용어집 {n}개 로드됨 (캐시 초기화)")

    # ── 트레이 최소화 / 복원 ─────────────────────────────────
    def _minimize_all(self):
        for p in self._all_panels():
            p.hide()
        self.tray.show()
        self.tray.showMessage("ESO 번역기", "트레이에서 복원하세요",
                              QSystemTrayIcon.MessageIcon.Information, 1000)

    def _restore_all(self):
        for p in self._all_panels():
            if not getattr(p, '_collapsed', False):
                p.show()
        self.tray.hide()

    # ── 개별 패널 collapse 콜백 ───────────────────────────────
    def _on_panel_collapse(self, panel):
        self.title_p.add_restore_btn(panel, lambda: panel.do_expand())

    def _on_panel_expand(self, panel):
        self.title_p.remove_restore_btn(panel)

    # ── 번역 시작/중지 ────────────────────────────────────────
    def _toggle_watch(self):
        if self.watch_thread and self.watch_thread.isRunning():
            self.watch_thread.stop()
            self.watch_thread = None
            self.bottom_p.set_running(False)
            return

        api = self.cfg.get("api_key", "").strip()
        log = self.cfg.get("log_path", "").strip()
        if not api:
            QMessageBox.warning(None, "설정 오류", "설정(⚙)에서 DeepL API 키를 입력해주세요.")
            return
        import os
        if not log or not os.path.exists(log):
            QMessageBox.warning(None, "설정 오류", "Chat.log 경로가 올바르지 않습니다.")
            return

        for key, cb in self.channel_p.ch_vars.items():
            self.cfg["channels"][key] = cb.isChecked()
        save_config(self.cfg)

        self.glossary = load_glossary(self.cfg.get("glossary_path", "eso_glossary.csv"))
        self.cache.clear()

        self.watch_thread = WatchThread(self.cfg, self.cache, self.glossary)
        self.watch_thread.new_message.connect(self._on_message)
        self.watch_thread.status.connect(self.bottom_p.status_lbl.setText)
        self.watch_thread.cache_count.connect(
            lambda n: self.bottom_p.cache_lbl.setText(f"캐시: {n}"))
        self.watch_thread.start()
        self.bottom_p.set_running(True)

    def _on_message(self, time_str, ch_key, speaker, original, translated):
        self.chat_p.append(
            time_str, ch_key, speaker, original, translated,
            self.title_p.orig_cb.isChecked(),
            self.cfg.get("font_size", 11),
        )
        self.chat_p.wake_up()

    # ── 한→영 입력 번역 ───────────────────────────────────────
    def _translate_input(self, text: str):
        api = self.cfg.get("api_key", "").strip()
        if not api:
            self.input_p.show_status("API 키 없음")
            return
        self.input_p.show_status("번역 중...")

        def do():
            result = translate_to_english(text, api)
            # pyqtSignal은 어느 스레드에서 emit해도 메인스레드로 안전하게 전달됨
            self._input_result_ready.emit(text, result)

        threading.Thread(target=do, daemon=True).start()

    def _on_input_translated(self, original_ko: str, result_en: str):
        is_error = result_en.startswith("[오류") or result_en.startswith("[시간")
        if is_error:
            self.input_p.show_status(result_en)
            return
        try:
            import pyperclip
            pyperclip.copy(result_en)
        except Exception:
            QApplication.clipboard().setText(result_en)
        self.input_p.show_result(result_en)

    def _append_input_to_chat(self, original_ko: str, result_en: str):
        t = datetime.datetime.now().strftime("%H:%M")
        c = self.chat_p.text.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        block_pos = c.position()
        fs = self.cfg.get("font_size", 11)

        def ins(txt, color, bold=False, size=None):
            fmt = c.charFormat()
            fmt.setForeground(QColor(color))
            f = QFont("맑은 고딕", size or fs)
            f.setBold(bold)
            fmt.setFont(f)
            c.setCharFormat(fmt)
            c.insertText(txt)

        ins(f"[{t}] ", "#444466", size=9)
        ins("[한→영] ", "#a78bfa", bold=True)
        ins("나: ", "#a78bfa")
        ins(result_en + "\n", "#ffffff")
        ins("      ↳ " + original_ko + "\n", "#555577", size=fs - 1)

        self.chat_p.text.setTextCursor(c)
        self.chat_p.text.ensureCursorVisible()
        self.chat_p._msg_times.append((time.time(), block_pos))
        self.chat_p.wake_up()

    # ── 종료 ──────────────────────────────────────────────────
    def _on_close(self):
        self.cfg["show_original"] = self.title_p.orig_cb.isChecked()
        self.cfg["fade_seconds"]  = self.title_p.fade_slider.value()
        for key, cb in self.channel_p.ch_vars.items():
            self.cfg["channels"][key] = cb.isChecked()
        for p in self._all_panels():
            p.save_geometry()
        self.cfg["collapsed"] = {
            key: panel._collapsed
            for key, panel in self._collapsible_panels.items()
        }
        save_config(self.cfg)
        save_cache(self.cache)
        if self.watch_thread:
            self.watch_thread.stop()
        QApplication.quit()

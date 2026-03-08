import os
import sys
import json

# exe로 패키징됐을 때와 일반 실행 모두 exe/스크립트 옆 폴더를 기준으로 사용
def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller exe 실행 시
        return os.path.dirname(sys.executable)
    else:
        # 일반 python 실행 시
        return os.path.dirname(os.path.abspath(__file__ + "/../../"))

BASE_DIR    = _base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG: dict = {
    "api_key": "",
    "log_path": "",
    "channels": {
        "say": True, "group": True, "zone": True,
        "guild": True, "whisper": True, "system": False,
    },
    "panels": {
        "title":   {"x": 100, "y":  60, "w": 540, "h":  48},
        "channel": {"x": 100, "y": 114, "w": 540, "h":  44},
        "chat":    {"x": 100, "y": 164, "w": 540, "h": 360},
        "bottom":  {"x": 100, "y": 530, "w": 540, "h":  50},
        "input":   {"x": 100, "y": 586, "w": 540, "h":  46},
    },
    "collapsed": {
        "channel": False,
        "bottom":  False,
        "input":   False,
    },
    "chat_opacity": 0.75,
    "show_original": False,
    "font_size": 11,
    "glossary_path": "eso_glossary.csv",
    "fade_seconds": 10,
    "my_character_name": "",
    "hide_my_chat": False,
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            if "panels" in data:
                for k, v in data["panels"].items():
                    if k in merged["panels"]:
                        merged["panels"][k].update(v)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

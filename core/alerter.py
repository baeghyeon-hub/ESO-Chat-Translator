import threading

# ── 알림 백엔드: winotify 우선, 없으면 plyer, 둘 다 없으면 무음 ──
def _init_notifier():
    try:
        from winotify import Notification, audio
        return "winotify", Notification, audio
    except ImportError:
        pass
    try:
        from plyer import notification
        return "plyer", notification, None
    except ImportError:
        pass
    return "none", None, None

_BACKEND, _NOTIF_CLS, _AUDIO = _init_notifier()


def check_keywords(message: str, translated: str, speaker: str,
                   ch_label: str, keywords: list[str]) -> str | None:
    """메시지/번역문에 키워드가 포함되어 있으면 매칭된 키워드 반환, 없으면 None."""
    text_to_check = f"{message} {translated or ''}".lower()
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.lower() in text_to_check:
            return kw
    return None


def send_alert(speaker: str, ch_label: str, message: str,
               translated: str, keyword: str):
    """Windows 토스트 알림 전송 (별도 스레드)."""
    def _send():
        body  = translated if translated else message
        title = f"🔔 [{ch_label}] {speaker}"
        msg   = f"키워드: {keyword} | {body[:100]}"

        try:
            if _BACKEND == "winotify":
                toast = _NOTIF_CLS(
                    app_id="ESO 번역기",
                    title=title,
                    msg=msg,
                    duration="short",
                )
                toast.set_audio(_AUDIO.Default, loop=False)
                toast.show()

            elif _BACKEND == "plyer":
                _NOTIF_CLS.notify(
                    title=title,
                    message=msg,
                    timeout=5,
                )
        except Exception as e:
            print(f"[알림 오류] {e}")

    threading.Thread(target=_send, daemon=True).start()

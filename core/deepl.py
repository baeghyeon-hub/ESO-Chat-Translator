"""
DeepL API 클라이언트.
Session / Retry / Timeout / 에러처리를 완전히 캡슐화.
pipeline.py만 이 모듈을 사용.
"""
from __future__ import annotations
import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── 설정 상수 ─────────────────────────────────────────────────
CONNECT_TIMEOUT = 3      # 서버 연결 대기 (초)
READ_TIMEOUT    = 7      # 응답 수신 대기 (초)
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

_MAX_RETRIES    = 3
_BACKOFF_FACTOR = 0.4
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

# ── 오류 문자열 상수 ──────────────────────────────────────────
ERR_TIMEOUT     = "[시간초과]"
ERR_CONNECTION  = "[연결오류]"
ERR_RATELIMIT   = "[레이트리밋]"

def err_http(code: int) -> str:
    return f"[오류 {code}]"

def err_unknown(e: Exception) -> str:
    return f"[오류:{e}]"

def is_error(text: str) -> bool:
    return isinstance(text, str) and text.startswith(
        ("[오류", "[시간초과]", "[연결오류]", "[레이트리밋]")
    )


# ── DeepL 클라이언트 ──────────────────────────────────────────

class DeepLClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._lock    = threading.Lock()
        self._session = self._make_session()

    # ── 세션 ──────────────────────────────────────────────────

    @staticmethod
    def _make_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=_MAX_RETRIES,
            backoff_factor=_BACKOFF_FACTOR,
            status_forcelist=_RETRY_STATUSES,
            allowed_methods={"POST"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://",  adapter)
        return session

    def reset_session(self) -> None:
        with self._lock:
            self._session = self._make_session()

    @property
    def _base_url(self) -> str:
        if self._api_key.strip().endswith(":fx"):
            return "https://api-free.deepl.com/v2"
        return "https://api.deepl.com/v2"

    # ── 번역 호출 ─────────────────────────────────────────────

    def translate(
        self,
        text:        str,
        target_lang: str,               # "KO" | "EN-US"
        source_lang: str | None = None, # None → DeepL 자동 감지
        context:     str = "",
        use_xml:     bool = False,
    ) -> str:
        """
        텍스트 번역. 성공 시 번역 결과 반환, 실패 시 오류 문자열 반환.
        예외를 외부로 전파하지 않음.
        """
        payload: dict = {
            "text":        [text],
            "target_lang": target_lang,
        }
        if source_lang:
            payload["source_lang"] = source_lang
        if context:
            payload["context"] = context
        if use_xml:
            payload["tag_handling"] = "xml"
            payload["ignore_tags"]  = ["x", "m"]

        try:
            with self._lock:
                r = self._session.post(
                    f"{self._base_url}/translate",
                    headers={"Authorization": f"DeepL-Auth-Key {self._api_key}"},
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

            if r.status_code == 200:
                return r.json()["translations"][0]["text"]
            if r.status_code == 429:
                return ERR_RATELIMIT
            return err_http(r.status_code)

        except requests.exceptions.Timeout:
            return ERR_TIMEOUT
        except requests.exceptions.ConnectionError:
            return ERR_CONNECTION
        except Exception as e:
            return err_unknown(e)

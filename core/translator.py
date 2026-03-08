import requests

from core.glossary import protect_glossary_terms, restore_glossary_terms

DEEPL_URL      = "https://api-free.deepl.com/v2/translate"
REQUEST_TIMEOUT = 5


def translate_to_korean(text: str, api_key: str, glossary: dict,
                         context: str = "") -> str:
    """텍스트를 한국어로 번역. 실패 시 오류 문자열 반환."""
    try:
        protected, replacements = protect_glossary_terms(text, glossary)
        payload: dict = {"text": [protected], "target_lang": "KO"}
        if context:
            payload["context"] = context
        if replacements:
            payload["tag_handling"] = "xml"
            payload["ignore_tags"]  = ["m"]

        r = requests.post(
            DEEPL_URL,
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            result = r.json()["translations"][0]["text"]
            return restore_glossary_terms(result, replacements)
        return f"[오류 {r.status_code}]"

    except requests.exceptions.Timeout:
        return "[시간초과]"
    except Exception as e:
        return f"[오류:{e}]"


def translate_to_english(text: str, api_key: str) -> str:
    """텍스트를 영어로 번역 (한→영 입력창용). 실패 시 오류 문자열 반환."""
    try:
        r = requests.post(
            DEEPL_URL,
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            json={"text": [text], "target_lang": "EN-US"},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()["translations"][0]["text"]
        return f"[오류 {r.status_code}]"
    except requests.exceptions.Timeout:
        return "[시간초과]"
    except Exception as e:
        return f"[오류:{e}]"

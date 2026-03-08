import requests

from core.glossary import protect_glossary_terms, restore_glossary_terms, apply_reverse_glossary, restore_reverse_terms

REQUEST_TIMEOUT = 5


def _get_base_url(api_key: str) -> str:
    """API 키 끝에 :fx 있으면 Free, 없으면 Pro 엔드포인트 반환."""
    if api_key.strip().endswith(":fx"):
        return "https://api-free.deepl.com/v2"
    return "https://api.deepl.com/v2"


def translate_to_korean(text: str, api_key: str, glossary: dict,
                         context: str = "") -> str:
    try:
        protected, replacements = protect_glossary_terms(text, glossary)
        payload: dict = {"text": [protected], "target_lang": "KO"}
        if context:
            payload["context"] = context
        if replacements:
            payload["tag_handling"] = "xml"
            payload["ignore_tags"]  = ["m"]

        r = requests.post(
            f"{_get_base_url(api_key)}/translate",
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


def translate_to_english(text: str, api_key: str, glossary: dict = {}, reverse_glossary: dict = {}) -> str:
    try:
        preprocessed, protected_terms = apply_reverse_glossary(text, glossary, reverse_glossary)
        payload: dict = {"text": [preprocessed], "target_lang": "EN-US"}
        if protected_terms:
            payload["tag_handling"] = "xml"
            payload["ignore_tags"] = ["m"]
        r = requests.post(
            f"{_get_base_url(api_key)}/translate",
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            json=payload,
            timeout=8,
        )
        if r.status_code == 200:
            result = r.json()["translations"][0]["text"]
            return restore_reverse_terms(result, protected_terms)
        return f"[오류 {r.status_code}]"
    except requests.exceptions.Timeout:
        return "[시간초과]"
    except Exception as e:
        return f"[오류:{e}]"

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MODEL = "MiniMax-Text-01"
DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RETRIES = 3


class MinimaxError(Exception):
    pass


class MinimaxConfigError(MinimaxError):
    pass


class MinimaxHTTPError(MinimaxError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


class MinimaxJSONError(MinimaxError):
    """模型返回的内容无法解析为 JSON。raw_content 保留原始字符串供 caller 落盘诊断。"""
    def __init__(self, msg: str, raw_content: str):
        super().__init__(msg)
        self.raw_content = raw_content


def _load_dotenv(project_root: Path) -> None:
    env_file = project_root / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


class MinimaxClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        _load_dotenv(_project_root())
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "").strip()
        self.base_url = (base_url or os.environ.get("MINIMAX_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("MINIMAX_MODEL") or DEFAULT_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        if not self.api_key:
            raise MinimaxConfigError(
                "MINIMAX_API_KEY is not set; put it in project root .env or export it before running"
            )

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/text/chatcompletion_v2"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                request = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                response_json = json.loads(raw)
                content = _extract_content(response_json)
                if content is None:
                    raise MinimaxError(f"no content in response: {raw[:300]}")
                try:
                    return _parse_json_content(content)
                except json.JSONDecodeError as e:
                    raise MinimaxJSONError(f"response JSON decode error: {e}", content)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
                last_exc = MinimaxHTTPError(e.code, body)
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_exc
            except (urllib.error.URLError, TimeoutError) as e:
                last_exc = MinimaxError(f"network error: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_exc
            except json.JSONDecodeError as e:
                raise MinimaxError(f"response JSON decode error: {e}")

        if last_exc:
            raise last_exc
        raise MinimaxError("unreachable")


def _extract_content(response_json: Dict[str, Any]) -> Optional[str]:
    base = response_json.get("base_resp") or {}
    status_code = base.get("status_code", 0)
    if status_code not in (0, None):
        raise MinimaxError(f"minimax base_resp error: code={status_code} msg={base.get('status_msg')}")
    choices: List[Dict[str, Any]] = response_json.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for chunk in content:
            if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                parts.append(chunk["text"])
        if parts:
            return "".join(parts)
    return None


def _parse_json_content(content: str) -> Dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def get_client_or_none() -> Optional[MinimaxClient]:
    try:
        return MinimaxClient()
    except MinimaxConfigError:
        return None

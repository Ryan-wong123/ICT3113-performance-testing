"""Synchronous, sequential local-Ollama integration for the baseline."""

import json
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .categories import category_prompt, parse_category
from .config import Settings


class OllamaError(RuntimeError):
    """A local Ollama request failed or did not follow the output contract."""


class OllamaClassifier:
    """One-at-a-time classifier. The lock deliberately prevents parallel inference."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._inference_lock = threading.Lock()

    @property
    def model(self) -> str:
        return self._settings.ollama_model

    def classify(self, narrative: str) -> str:
        # This lock is an explicit baseline constraint, not a throughput optimisation.
        with self._inference_lock:
            return self._classify_once(narrative)

    def _classify_once(self, narrative: str) -> str:
        payload = json.dumps(
            {
                "model": self._settings.ollama_model,
                "prompt": f"{category_prompt()}\n\nTicket narrative:\n{narrative}",
                "stream": False,
                "options": {"num_gpu": 0},
            }
        ).encode("utf-8")
        request = Request(
            f"{self._settings.ollama_base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._settings.ollama_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise OllamaError(f"Could not reach local Ollama: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned malformed JSON") from exc

        response_text = body.get("response")
        if not isinstance(response_text, str):
            raise OllamaError("Ollama response did not contain text")
        try:
            return parse_category(response_text)
        except ValueError as exc:
            raise OllamaError(str(exc)) from exc

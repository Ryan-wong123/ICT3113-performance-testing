"""Configuration for the deliberately simple Assignment 1 baseline."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    database_path: str
    request_log_path: str

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")),
            database_path=os.getenv("TICKETS_DB_PATH", "runtime/tickets.db"),
            request_log_path=os.getenv("REQUEST_LOG_PATH", "logs/requests.jsonl"),
        )

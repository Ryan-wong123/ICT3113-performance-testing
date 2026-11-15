"""Environment configuration for the baseline and optional A2 cascade."""

from dataclasses import dataclass
import os


def _environment_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true/false, yes/no, on/off, or 1/0")


def _optional_positive_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer when set")
    return value


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    database_path: str
    request_log_path: str
    cascade_enabled: bool = False
    cascade_small_model: str = ""
    cascade_large_model: str = ""
    cascade_rule_setting: str = ""
    cascade_rule_type: str = "category"
    cascade_escalate_categories: tuple[str, ...] = ()
    cascade_length_threshold_chars: int | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")),
            database_path=os.getenv("TICKETS_DB_PATH", "runtime/tickets.db"),
            request_log_path=os.getenv("REQUEST_LOG_PATH", "logs/requests.jsonl"),
            cascade_enabled=_environment_flag("CASCADE_ENABLED"),
            cascade_small_model=os.getenv("OLLAMA_SMALL_MODEL", "").strip(),
            cascade_large_model=os.getenv("OLLAMA_LARGE_MODEL", "").strip(),
            cascade_rule_setting=os.getenv("CASCADE_RULE_SETTING", "").strip(),
            cascade_rule_type=os.getenv("CASCADE_RULE_TYPE", "category").strip().lower(),
            cascade_escalate_categories=tuple(
                value.strip()
                for value in os.getenv("CASCADE_ESCALATE_CATEGORIES", "").split("|")
                if value.strip()
            ),
            cascade_length_threshold_chars=_optional_positive_int("CASCADE_LENGTH_THRESHOLD_CHARS"),
        )

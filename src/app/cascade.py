"""Assignment 2 cascade orchestration behind the default-off switch."""

from dataclasses import dataclass
from typing import Protocol

from .categories import CATEGORIES
from .config import Settings
from .ollama_client import OllamaError


class Classifier(Protocol):
    @property
    def model(self) -> str: ...

    def classify(self, narrative: str) -> str: ...

    def classify_with_model(self, narrative: str, model: str) -> str: ...


@dataclass(frozen=True)
class ClassificationOutcome:
    category: str
    public_model: str
    cascade_mode: str
    rule_setting: str | None
    small_model: str | None
    large_model: str | None
    small_category: str | None
    final_model: str
    escalated: bool | None


def validate_cascade_settings(settings: Settings) -> None:
    """Fail clearly when an enabled cascade is not fully configured."""
    if not settings.cascade_enabled:
        return
    if not settings.cascade_small_model or not settings.cascade_large_model:
        raise ValueError("OLLAMA_SMALL_MODEL and OLLAMA_LARGE_MODEL are required when CASCADE_ENABLED=true")
    if settings.cascade_small_model == settings.cascade_large_model:
        raise ValueError("OLLAMA_SMALL_MODEL and OLLAMA_LARGE_MODEL must be different")
    if not settings.cascade_rule_setting:
        raise ValueError("CASCADE_RULE_SETTING is required when CASCADE_ENABLED=true")
    if settings.cascade_rule_type not in {"category", "length", "category_or_length", "always", "never"}:
        raise ValueError(f"Unsupported CASCADE_RULE_TYPE: {settings.cascade_rule_type}")
    unknown = set(settings.cascade_escalate_categories) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"Unknown CASCADE_ESCALATE_CATEGORIES: {sorted(unknown)}")
    if settings.cascade_rule_type in {"length", "category_or_length"} and settings.cascade_length_threshold_chars is None:
        raise ValueError(f"CASCADE_LENGTH_THRESHOLD_CHARS is required for {settings.cascade_rule_type}")


def should_escalate(narrative: str, small_category: str, settings: Settings) -> bool:
    """Apply the configured, tuning-set-derived rule without model calls."""
    rule_type = settings.cascade_rule_type
    category_match = small_category in settings.cascade_escalate_categories
    length_match = (
        settings.cascade_length_threshold_chars is not None
        and len(narrative) > settings.cascade_length_threshold_chars
    )
    if rule_type == "category":
        return category_match
    if rule_type == "length":
        return length_match
    if rule_type == "category_or_length":
        return category_match or length_match
    if rule_type == "always":
        return True
    if rule_type == "never":
        return False
    raise ValueError(f"Unsupported CASCADE_RULE_TYPE: {rule_type}")


def classify_ticket(narrative: str, classifier: Classifier, settings: Settings) -> ClassificationOutcome:
    """Classify once in baseline mode, or small-then-optional-large in cascade mode."""
    if not settings.cascade_enabled:
        category = classifier.classify(narrative)
        return ClassificationOutcome(
            category=category,
            public_model=classifier.model,
            cascade_mode="off",
            rule_setting=None,
            small_model=None,
            large_model=None,
            small_category=None,
            final_model=classifier.model,
            escalated=None,
        )

    validate_cascade_settings(settings)
    small_category = None
    try:
        small_category = classifier.classify_with_model(narrative, settings.cascade_small_model)
        escalate = should_escalate(narrative, small_category, settings)
    except OllamaError:
        # A failed/invalid small answer cannot be returned, so the large model is the safe fallback.
        escalate = True

    if escalate:
        category = classifier.classify_with_model(narrative, settings.cascade_large_model)
        final_model = settings.cascade_large_model
    else:
        category = small_category
        final_model = settings.cascade_small_model

    # Keep the legacy response schema stable without exposing which cascade model answered.
    return ClassificationOutcome(
        category=category,
        public_model=classifier.model,
        cascade_mode="on",
        rule_setting=settings.cascade_rule_setting,
        small_model=settings.cascade_small_model,
        large_model=settings.cascade_large_model,
        small_category=small_category,
        final_model=final_model,
        escalated=escalate,
    )

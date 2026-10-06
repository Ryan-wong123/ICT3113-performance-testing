"""The only labels the baseline may assign."""

CATEGORIES = (
    "Credit reporting",
    "Debt collection",
    "Mortgage",
    "Credit card",
    "Bank account or service",
    "Consumer loan",
    "Money transfer or service",
)


def category_prompt() -> str:
    choices = "\n".join(f"- {category}" for category in CATEGORIES)
    return (
        "You are routing a financial-services customer complaint. "
        "Choose exactly one category from this fixed list. "
        "Reply with only the category text; do not add explanation, punctuation, or markdown.\n\n"
        f"Categories:\n{choices}"
    )


def parse_category(model_text: str) -> str:
    """Accept only one unambiguous category from the model response."""
    normalized = model_text.strip().casefold().rstrip(".")
    matches = [category for category in CATEGORIES if category.casefold() == normalized]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"Ollama returned an invalid category response: {model_text!r}")

import unittest
from unittest.mock import patch
import json

from src.app.cascade import classify_ticket, should_escalate, validate_cascade_settings
from src.app.config import Settings
from src.app.ollama_client import OllamaClassifier, OllamaError


def make_settings(**overrides) -> Settings:
    values = {
        "ollama_base_url": "http://ollama.invalid",
        "ollama_model": "baseline:model",
        "ollama_timeout_seconds": 300,
        "database_path": "unused.db",
        "request_log_path": "unused.jsonl",
    }
    values.update(overrides)
    return Settings(**values)


class StubClassifier:
    def __init__(self, answers=None, failures=None):
        self.model = "baseline:model"
        self.answers = answers or {}
        self.failures = set(failures or [])
        self.calls = []

    def classify(self, narrative):
        self.calls.append((None, narrative))
        return self.answers.get(None, "Mortgage")

    def classify_with_model(self, narrative, model):
        self.calls.append((model, narrative))
        if model in self.failures:
            raise OllamaError("invalid small answer")
        return self.answers[model]


class Assignment2CascadeTests(unittest.TestCase):
    def test_default_off_path_is_one_baseline_call(self):
        classifier = StubClassifier({None: "Mortgage"})
        outcome = classify_ticket("example", classifier, make_settings())
        self.assertEqual(outcome.category, "Mortgage")
        self.assertEqual(outcome.cascade_mode, "off")
        self.assertIsNone(outcome.escalated)
        self.assertEqual(classifier.calls, [(None, "example")])

    def test_category_rule_accepts_or_escalates(self):
        settings = make_settings(
            cascade_enabled=True,
            cascade_small_model="small:model",
            cascade_large_model="large:model",
            cascade_rule_setting="A",
            cascade_escalate_categories=("Debt collection",),
        )
        accepted = StubClassifier({"small:model": "Mortgage", "large:model": "Credit reporting"})
        accepted_outcome = classify_ticket("accepted", accepted, settings)
        self.assertFalse(accepted_outcome.escalated)
        self.assertEqual(accepted.calls, [("small:model", "accepted")])

        escalated = StubClassifier({"small:model": "Debt collection", "large:model": "Credit reporting"})
        escalated_outcome = classify_ticket("escalated", escalated, settings)
        self.assertTrue(escalated_outcome.escalated)
        self.assertEqual(escalated_outcome.category, "Credit reporting")
        self.assertEqual(escalated_outcome.final_model, "large:model")
        self.assertEqual(escalated.calls, [("small:model", "escalated"), ("large:model", "escalated")])

    def test_small_model_error_falls_back_to_large(self):
        settings = make_settings(
            cascade_enabled=True,
            cascade_small_model="small:model",
            cascade_large_model="large:model",
            cascade_rule_setting="B",
        )
        classifier = StubClassifier(
            {"large:model": "Bank account or service"},
            failures={"small:model"},
        )
        outcome = classify_ticket("fallback", classifier, settings)
        self.assertTrue(outcome.escalated)
        self.assertIsNone(outcome.small_category)
        self.assertEqual(outcome.category, "Bank account or service")

    def test_length_and_combined_rules(self):
        settings = make_settings(
            cascade_rule_type="length",
            cascade_length_threshold_chars=5,
        )
        self.assertFalse(should_escalate("12345", "Mortgage", settings))
        self.assertTrue(should_escalate("123456", "Mortgage", settings))
        combined = make_settings(
            cascade_rule_type="category_or_length",
            cascade_length_threshold_chars=100,
            cascade_escalate_categories=("Mortgage",),
        )
        self.assertTrue(should_escalate("short", "Mortgage", combined))

    def test_enabled_configuration_is_validated(self):
        with self.assertRaisesRegex(ValueError, "OLLAMA_SMALL_MODEL"):
            validate_cascade_settings(make_settings(cascade_enabled=True))

    def test_named_model_keeps_cpu_only_inference_option(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"response": "Mortgage"}).encode("utf-8")

        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response()

        classifier = OllamaClassifier(make_settings())
        with patch("src.app.ollama_client.urlopen", fake_urlopen):
            category = classifier.classify_with_model("example", "small:model")
        self.assertEqual(category, "Mortgage")
        self.assertEqual(captured["payload"]["model"], "small:model")
        self.assertEqual(captured["payload"]["options"], {"num_gpu": 0})


if __name__ == "__main__":
    unittest.main()

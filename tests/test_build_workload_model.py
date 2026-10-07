import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_workload_model.py"


class BuildWorkloadModelTests(unittest.TestCase):
    def run_generator(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        output = Path(temporary_directory.name) / "workload_model.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(output), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return result, output

    def test_non_default_peak_hours_produce_matching_window(self) -> None:
        result, output = self.run_generator("--peak-start-hour", "20", "--peak-hours", "6")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["assumptions"]["peak_window"], "20:00-02:00 local time")
        self.assertEqual(report["assumptions"]["peak_hours_per_day"], 6)

    def test_non_finite_float_arguments_are_rejected_without_output(self) -> None:
        for option in ("--client-market-share", "--search-ratio", "--peak-multiplier"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(option=option, value=value):
                    result, output = self.run_generator(option, value)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())

    def test_period_window_volumes_conserve_daily_volume(self) -> None:
        result, output = self.run_generator()

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        for traffic_type in ("submissions", "searches"):
            peak = report["periods"]["peak"][traffic_type]["expected_per_window"]
            off_peak = report["periods"]["off_peak"][traffic_type]["expected_per_window"]
            expected_daily = report["expected_volume"][traffic_type]["per_day"]
            self.assertAlmostEqual(peak + off_peak, expected_daily, places=5)
            self.assertNotIn("per_day", report["periods"]["peak"][traffic_type])
            self.assertNotIn("per_day", report["periods"]["off_peak"][traffic_type])

    def test_generated_output_is_strict_json(self) -> None:
        result, output = self.run_generator()

        self.assertEqual(result.returncode, 0, result.stderr)

        def reject_nonstandard_constant(value: str) -> None:
            raise ValueError(f"non-standard JSON constant: {value}")

        report = json.loads(
            output.read_text(encoding="utf-8"),
            parse_constant=reject_nonstandard_constant,
        )
        stdout_report = json.loads(result.stdout, parse_constant=reject_nonstandard_constant)
        self.assertEqual(stdout_report, report)


if __name__ == "__main__":
    unittest.main()

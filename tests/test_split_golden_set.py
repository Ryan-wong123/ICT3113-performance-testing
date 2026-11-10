import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "split_golden_set.py"
GOLDEN = ROOT / "labelling" / "golden_test_set.csv"
COMMITTED = ROOT / "analysis" / "a2" / "golden_split.csv"


def write_golden(path: Path, rows: list[tuple[int, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["row", "narrative", "final_label"])
        for row, label in rows:
            writer.writerow([row, f"narrative {row}", label])


def read_split(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class SplitGoldenSetTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def run_split(self, golden: Path, *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        output = self.directory / "split.csv"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(golden), "--output", str(output), *extra],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return result, output

    def test_odd_rows_are_tuning_and_even_rows_are_test(self):
        golden = self.directory / "golden.csv"
        write_golden(golden, [(8003, "Mortgage"), (8004, "Credit card"), (8005, "Mortgage"), (8010, "Consumer loan")])
        result, output = self.run_split(golden)
        self.assertEqual(result.returncode, 0, result.stderr)
        split = {int(r["row"]): r["split"] for r in read_split(output)}
        self.assertEqual(split, {8003: "tuning", 8004: "test", 8005: "tuning", 8010: "test"})

    def test_output_is_independent_of_input_order_and_sorted_by_row(self):
        first = self.directory / "a.csv"
        second = self.directory / "b.csv"
        write_golden(first, [(8010, "Mortgage"), (8003, "Credit card"), (8004, "Mortgage")])
        write_golden(second, [(8003, "Credit card"), (8004, "Mortgage"), (8010, "Mortgage")])
        _, out_a = self.run_split(first)
        text_a = out_a.read_text(encoding="utf-8")
        _, out_b = self.run_split(second)
        self.assertEqual(text_a, out_b.read_text(encoding="utf-8"))
        self.assertEqual([int(r["row"]) for r in read_split(out_b)], [8003, 8004, 8010])

    def test_rejects_duplicate_row(self):
        golden = self.directory / "golden.csv"
        write_golden(golden, [(8004, "Mortgage"), (8004, "Mortgage")])
        result, _ = self.run_split(golden)
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_row_outside_team_8_range(self):
        golden = self.directory / "golden.csv"
        write_golden(golden, [(7999, "Mortgage")])
        result, _ = self.run_split(golden)
        self.assertNotEqual(result.returncode, 0)

    def test_check_flags_a_stale_output(self):
        golden = self.directory / "golden.csv"
        write_golden(golden, [(8003, "Mortgage"), (8004, "Credit card")])
        self.run_split(golden)
        write_golden(golden, [(8003, "Mortgage"), (8004, "Credit card"), (8006, "Mortgage")])
        result, _ = self.run_split(golden, "--check")
        self.assertEqual(result.returncode, 1)

    def test_committed_split_matches_the_frozen_golden_set(self):
        self.assertTrue(COMMITTED.exists(), "analysis/a2/golden_split.csv must be committed")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        split = read_split(COMMITTED)
        golden_rows = {int(r["row"]) for r in read_split(GOLDEN)}
        self.assertEqual({int(r["row"]) for r in split}, golden_rows)
        tuning = {int(r["row"]) for r in split if r["split"] == "tuning"}
        test = {int(r["row"]) for r in split if r["split"] == "test"}
        self.assertFalse(tuning & test)
        self.assertEqual(tuning | test, golden_rows)
        self.assertTrue(all(row % 2 == 1 for row in tuning))
        self.assertTrue(all(row % 2 == 0 for row in test))


if __name__ == "__main__":
    unittest.main()

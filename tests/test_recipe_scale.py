import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from recipe_scale import MAX_FILE_BYTES, format_quantity, parse_quantity

ROOT = Path(__file__).resolve().parents[1]


class QuantityTests(unittest.TestCase):
    def test_whole_decimal_fraction_and_mixed(self):
        examples = {"3": Fraction(3), "0.1": Fraction(1, 10), ".5": Fraction(1, 2),
                    "6/4": Fraction(3, 2), "2 1/3": Fraction(7, 3)}
        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(parse_quantity(text), expected)

    def test_invalid_quantities(self):
        for text in ("", "0", "1e-3", "-1", "1/0", "2 5/4", "3 1/0", "9" * 33):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_quantity(text)

    def test_format_keeps_an_exact_reduced_result(self):
        self.assertEqual(format_quantity(Fraction(21, 6)), "3 1/2")
        self.assertEqual(format_quantity(Fraction(3, 9)), "1/3")
        self.assertEqual(format_quantity(Fraction(8, 2)), "4")


class CliTests(unittest.TestCase):
    def run_recipe(self, path, original="4", target="6"):
        return subprocess.run(
            [sys.executable, str(ROOT / "recipe_scale.py"), str(path),
             "--from", original, "--to", target],
            text=True, capture_output=True, cwd=ROOT,
        )

    def run_fixture(self, contents):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recipe.csv"
            path.write_bytes(contents)
            result = self.run_recipe(path)
            self.assertEqual(path.read_bytes(), contents)
            return result

    def test_sample_cli_scales_ingredients_and_keeps_row_order(self):
        result = self.run_recipe(ROOT / "examples" / "pancakes.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "4 to 6 servings", "2 1/4 cups flour", "1 7/8 cups milk",
            "3 eggs", "3/4 tsp salt", "3 tbsp butter, melted",
        ])

    def test_scaling_down_keeps_a_fractional_count(self):
        result = self.run_recipe(ROOT / "examples" / "pancakes.csv", "4", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/2 eggs", result.stdout.splitlines())

    def test_cli_reports_serving_range_errors(self):
        for original, target in [("0", "4"), ("4", "-2"), ("4", "10001")]:
            with self.subTest(original=original, target=target):
                result = self.run_recipe(ROOT / "examples" / "pancakes.csv", original, target)
                self.assertEqual(result.returncode, 2)
                self.assertIn("servings must be a whole number", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_bad_later_row_does_not_print_partial_results(self):
        result = self.run_fixture(b"quantity,unit,ingredient\n1,cup,flour\n1/0,cup,milk\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("line 3: a fraction denominator cannot be zero", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_bad_csv_header_encoding_and_empty_recipe(self):
        for contents, error in [
            (b"quantity,ingredient\n1,flour\n", "expected a quantity,unit,ingredient header"),
            (b"quantity,unit,ingredient\n1,cup,\"flour", "invalid CSV"),
            (b"quantity,unit,ingredient\n1,cup,\xff\n", "must be UTF-8"),
            (b"quantity,unit,ingredient\n", "no ingredients"),
            (b"quantity,unit,ingredient\n1,cup\n", "expected three columns"),
            (b"quantity,unit,ingredient\n1,cup,\"new\nline\"\n", "single-line ingredient"),
        ]:
            with self.subTest(error=error):
                result = self.run_fixture(contents)
                self.assertEqual(result.returncode, 1)
                self.assertIn(error, result.stderr)

    def test_size_limit(self):
        result = self.run_fixture(b"x" * (MAX_FILE_BYTES + 1))
        self.assertEqual(result.returncode, 1)
        self.assertIn("at most 64 KiB", result.stderr)

    def test_bom_crlf_and_blank_unit(self):
        result = self.run_fixture(b"\xef\xbb\xbfquantity,unit,ingredient\r\n2,,eggs\r\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["4 to 6 servings", "3 eggs"])


if __name__ == "__main__":
    unittest.main()

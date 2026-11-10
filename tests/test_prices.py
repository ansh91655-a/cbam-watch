"""인증서 가격표 읽기를 확인한다."""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest

from tools.prices import parse, periods, run

PAGE = """Price of CBAM certificates
In 2026, the Commission will calculate and publish four quarterly prices.

[표의 행]
Quarter of application | Date of publication | Price (€)
Q1 2026 | 7 April 2026 | 75.36
Q2 2026 | 6 July 2026 | 75.28
Q3 2026 | 5 October 2026 | 82.32
Q4 2026 | 4 January 2027 | 
"""


class PeriodTests(unittest.TestCase):
    def test_quarter(self):
        got = periods.read("Q3 2026")
        self.assertEqual((got["period"], got["from"], got["to"], got["kind"]), ("2026-Q3", "2026-07-01", "2026-09-30", "quarter"))

    def test_week_forms_agree(self):
        forms = ["Week 1 2027", "2027-W01", "4 January 2027 - 10 January 2027", "4-10 January 2027", "04/01/2027 – 10/01/2027"]
        self.assertEqual({(periods.read(form)["from"], periods.read(form)["to"]) for form in forms}, {("2027-01-04", "2027-01-10")})
        self.assertNotIn("assumed", periods.read("Week 1 2027"))

    def test_single_date_is_marked_as_assumed(self):
        self.assertTrue(periods.read("11 January 2027")["assumed"])

    def test_unknown(self):
        self.assertIsNone(periods.read("Something else"))


class ParseTests(unittest.TestCase):
    def test_reads_table(self):
        priced, upcoming, unparsed = parse.read(PAGE)
        self.assertEqual([(row["period"], row["value"], row["published"]) for row in priced],
                         [("2026-Q1", 75.36, "2026-04-07"), ("2026-Q2", 75.28, "2026-07-06"), ("2026-Q3", 82.32, "2026-10-05")])
        self.assertEqual([(row["period"], row["published"]) for row in upcoming], [("2026-Q4", "2027-01-04")])
        self.assertEqual(unparsed, [])

    def test_unreadable_row_is_reported(self):
        _, _, unparsed = parse.read("[표의 행]\nPeriod | Price\nFirst half 2027 | 80.10\n")
        self.assertEqual(len(unparsed), 1)

    def test_comma_decimal_and_euro_sign(self):
        row = parse.read_row(["11-17 January 2027", "18 January 2027", "€ 80,5"])
        self.assertEqual((row["value"], row["kind"], row["published"]), (80.5, "week", "2027-01-18"))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.old)
        self.tmp.cleanup()

    def _run(self, text):
        pathlib.Path("page.txt").write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(["--page", "page.txt", "--out", "prices.json"])
        return json.loads(out.getvalue().strip().splitlines()[-1]), json.loads(pathlib.Path("prices.json").read_text(encoding="utf-8"))

    def test_keeps_history_and_records_revisions(self):
        result, body = self._run(PAGE)
        self.assertEqual(result["added"], ["2026-Q1", "2026-Q2", "2026-Q3"])
        self.assertEqual(len(body["upcoming"]), 1)
        again, _ = self._run(PAGE)
        self.assertFalse(again["written"])
        later = "[표의 행]\nWeek | Date of publication | Price (€)\nQ3 2026 | 5 October 2026 | 82.40\nQ4 2026 | 4 January 2027 | 79.15\nWeek 1 2027 | 11 January 2027 | 80.02\n"
        result, body = self._run(later)
        self.assertEqual([row["period"] for row in body["prices"]], ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-01-04"])
        self.assertEqual(result["revised"][0]["was"], 82.32)
        self.assertEqual(body["upcoming"], [])
        self.assertEqual(body["prices"][0]["value"], 75.36)


if __name__ == "__main__":
    unittest.main()

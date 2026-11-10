"""게시 데이터를 다루는 도구를 임시 폴더에서 확인한다."""
import contextlib
import datetime
import io
import json
import os
import pathlib
import tempfile
import unittest

from tools.publish import add_digest, add_items, withdraw
from tools.run import claude_status, week_items


def _write(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _run(function, argv):
    """도구를 돌려 (끝난 값, 마지막 줄의 JSON)을 돌려준다."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = function(argv)
    lines = [line for line in out.getvalue().splitlines() if line.strip()]
    try:
        return code, json.loads(lines[-1])
    except Exception:
        return code, {}


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.folder.name)
        _write("data/items.json", {"items": [{"id": "seed-one", "title": "기존 항목", "summary": "요약", "kind": "소식", "importance": "보통",
                                              "link": "https://example.org/a", "published": "2026-11-09", "listed": "2026-11-10", "authoring": "자동"}]})
        _write("data/events.json", {"events": []})

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def _draft(self, item_id, **extra):
        item = {"id": item_id, "title": "새 가이던스 공개", "summary": "EU 집행위원회가 가이던스를 공개했다.", "impact": "", "kind": "가이던스", "importance": "보통",
                "link": "https://example.org/b", "published": "2026-11-10", "sourceCode": "ec-news", "sourceName": "EC", "facts": [{"label": "x", "value": "y"}],
                "events": [{"date": "2027-01-04", "title": "가격 게시"}]}
        item.update(extra)
        _write(f"db/items/{item_id}.json", item)

    def _verdict(self, item_id, result):
        _write(f"db/verdicts/{item_id}.json", {"id": item_id, "result": result, "at": "2026-11-10T08:30:00+09:00"})

    def test_only_passed_and_well_formed_items_are_added(self):
        self._draft("20261110-ec-news-aaaaaa")
        self._verdict("20261110-ec-news-aaaaaa", "pass")
        self._draft("20261110-ec-news-bbbbbb")
        self._verdict("20261110-ec-news-bbbbbb", "hold")
        self._draft("20261110-ec-news-cccccc", link="http://insecure.example")
        self._verdict("20261110-ec-news-cccccc", "pass")
        self._draft("20261110-ec-news-dddddd")  # 판정이 없다
        code, result = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(code, 0)
        self.assertEqual(result["added"], ["20261110-ec-news-aaaaaa"])
        self.assertEqual([row["id"] for row in result["rejected"]], ["20261110-ec-news-cccccc"])
        items = _read("data/items.json")["items"]
        self.assertEqual(len(items), 2)
        self.assertNotIn("facts", items[-1])  # 내부용 항목은 게시 데이터에 넣지 않는다
        self.assertEqual(_read("data/events.json")["events"][0]["date"], "2027-01-04")
        # 다시 돌려도 겹쳐 더하지 않는다
        _, again = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(again["added"], [])

    def test_numbers_must_be_in_the_source_text(self):
        source = "5Oct2026 Q3 2026 CBAM Certificate price now available! The price is 82.32 EUR."
        pathlib.Path("collected/pages").mkdir(parents=True)
        pathlib.Path("collected/pages/ec-news.txt").write_text(source, encoding="utf-8")
        common = {"sourceTextPath": "collected/pages/ec-news.txt", "tier": "A", "kind": "가격", "title": "3분기 가격 게시"}
        self._draft("20261110-ec-news-good01", summary="2026년 10월 5일에 3분기 가격 82.32유로가 게시됐다.", excerpt="The price is 82.32 EUR.", **common)
        self._draft("20261110-ec-news-bad001", summary="2026년 10월 5일에 3분기 가격 83.32유로가 게시됐다.", **common)
        self._draft("20261110-ec-news-note01", summary="2026년 10월 5일에 가격 82.32유로(약 12만 원)가 게시됐다.", excerpt="The price is 82.33 EUR.", **common)
        for item_id in ("20261110-ec-news-good01", "20261110-ec-news-bad001"):
            self._verdict(item_id, "pass")
        _write("db/verdicts/20261110-ec-news-note01.json", {"id": "20261110-ec-news-note01", "result": "pass", "factNote": "표기 차이: 12는 환산 설명", "at": "2026-11-10T08:30:00+09:00"})
        _, result = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(sorted(result["added"]), ["20261110-ec-news-good01", "20261110-ec-news-note01"])
        self.assertEqual(result["rejected"][0]["id"], "20261110-ec-news-bad001")
        self.assertIn("83.32", result["rejected"][0]["problems"][0])
        self.assertEqual(result["withoutExcerpt"], ["20261110-ec-news-note01"])  # 원문과 다른 발췌는 싣지 않는다
        rows = {row["id"]: row for row in _read("data/items.json")["items"]}
        self.assertEqual(rows["20261110-ec-news-good01"]["excerpt"], "The price is 82.32 EUR.")
        self.assertNotIn("excerpt", rows["20261110-ec-news-note01"])

    def test_excerpt_only_for_eu_official_sources(self):
        pathlib.Path("collected/pages").mkdir(parents=True)
        pathlib.Path("collected/pages/keco.txt").write_text("CBAM 설명회가 열린다는 공지입니다.", encoding="utf-8")
        self._draft("20261110-keco-cbam-aaaa01", sourceTextPath="collected/pages/keco.txt", tier="B", excerpt="CBAM 설명회가 열린다는 공지입니다.", summary="설명회가 열린다.")
        self._verdict("20261110-keco-cbam-aaaa01", "pass")
        _, result = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(result["added"], ["20261110-keco-cbam-aaaa01"])
        self.assertNotIn("excerpt", _read("data/items.json")["items"][-1])

    def test_digest_is_validated_and_replaced(self):
        _write("digest.json", {"from": "2026-11-09", "to": "2026-11-15", "title": "가격과 가이던스", "paragraphs": ["한 문단"], "itemIds": ["seed-one"]})
        code, result = _run(add_digest.main, ["--file", "digest.json"])
        self.assertEqual((code, result["added"]), (0, True))
        _run(add_digest.main, ["--file", "digest.json"])
        self.assertEqual(len(_read("data/digests.json")["digests"]), 1)
        _write("bad.json", {"from": "2026-11-09", "to": "2026-11-15", "title": "", "paragraphs": [], "itemIds": ["nope"]})
        code, result = _run(add_digest.main, ["--file", "bad.json"])
        self.assertEqual(code, 1)
        self.assertEqual(len(result["problems"]), 3)

    def test_withdraw_keeps_the_item(self):
        code, _ = _run(withdraw.main, ["--id", "seed-one", "--reason", "수치가 원문과 다름"])
        self.assertEqual(code, 0)
        item = _read("data/items.json")["items"][0]
        self.assertEqual(item["withdrawn"]["reason"], "수치가 원문과 다름")
        self.assertEqual(_run(withdraw.main, ["--id", "none", "--reason", "x"])[0], 1)

    def test_last_week_and_sample(self):
        self.assertEqual(week_items.last_week(datetime.date(2026, 11, 16)), (datetime.date(2026, 11, 9), datetime.date(2026, 11, 15)))
        self.assertEqual(week_items.last_week(datetime.date(2026, 11, 22)), (datetime.date(2026, 11, 9), datetime.date(2026, 11, 15)))
        _run(week_items.main, ["--out", "week.json", "--date", "2026-11-16", "--audit", "3"])
        week = _read("week.json")
        self.assertEqual((week["id"], len(week["items"]), week["audit"]), ("2026-11-09_2026-11-15", 1, ["seed-one"]))
        self.assertIn("기존 항목", pathlib.Path("week.txt").read_text(encoding="utf-8"))

    def test_claude_status_counts_failures(self):
        _run(claude_status.main, ["council-cbam=ok", "op-europa=fail:403으로 막힘"])
        _run(claude_status.main, ["op-europa=fail:403으로 막힘"])
        book = _read("collected/claude-status.json")["sources"]
        self.assertEqual((book["council-cbam"]["ok"], book["op-europa"]["failCount"], book["op-europa"]["lastOk"]), (True, 2, ""))
        _run(claude_status.main, ["op-europa=ok"])
        self.assertEqual(_read("collected/claude-status.json")["sources"]["op-europa"]["failCount"], 0)


if __name__ == "__main__":
    unittest.main()

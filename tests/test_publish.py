"""게시 데이터를 다루는 도구를 임시 폴더에서 확인한다."""
import contextlib
import datetime
import io
import json
import os
import pathlib
import tempfile
import unittest

from tools.common.jsonio import now_kst, stamp
from tools.publish import add_digest, add_items, merge, withdraw
from tools.run import claude_status, day_summary, feed_title, holds_to_fix, holds_to_recheck, rechecks, week_items


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
        _write("data/topics.json", {"topics": [{"code": "law", "name": "제도·법령"}, {"code": "price", "name": "인증서·가격"}, {"code": "etc", "name": "기타"}]})

    def tearDown(self):
        os.chdir(self.previous)
        self.folder.cleanup()

    def _draft(self, item_id, **extra):
        item = {"id": item_id, "title": "새 가이던스 공개", "summary": "EU 집행위원회가 가이던스를 공개했다.", "impact": "", "kind": "가이던스", "topic": "law", "importance": "보통",
                "link": "https://example.org/b", "published": "2026-11-10", "sourceCode": "ec-news", "sourceName": "EC", "facts": [{"label": "x", "value": "y"}],
                "events": [{"date": "2027-01-04", "title": "가격 게시", "kind": "가격"}, {"date": "2027-02", "title": "판매 시작"}, {"date": "2027", "title": "꼴이 틀린 일정"}]}
        item.update(extra)
        _write(f"db/items/{item_id}.json", item)

    def _verdict(self, item_id, result):
        _write(f"db/verdicts/{item_id}.json", {"id": item_id, "result": result, "at": "2026-11-10T08:30:00+09:00"})

    def test_unknown_topic_becomes_other(self):
        self._draft("20261110-ec-news-topic1", topic="없는주제")
        self._verdict("20261110-ec-news-topic1", "pass")
        self._draft("20261110-ec-news-topic2", topic="price")
        self._verdict("20261110-ec-news-topic2", "pass")
        code, result = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(result["added"], ["20261110-ec-news-topic1", "20261110-ec-news-topic2"])
        self.assertEqual(result["topicDefaulted"], ["20261110-ec-news-topic1"])
        saved = {item["id"]: item["topic"] for item in _read("data/items.json")["items"] if item["id"].startswith("2026")}
        self.assertEqual(saved, {"20261110-ec-news-topic1": "etc", "20261110-ec-news-topic2": "price"})
        events = _read("data/events.json")["events"]
        self.assertEqual([(event["date"], event.get("kind")) for event in events], [("2027-01-04", "가격"), ("2027-02", None)])

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

    def test_held_drafts_get_one_rewrite(self):
        self._draft("20261110-ec-news-hold01")
        _write("db/verdicts/20261110-ec-news-hold01.json", {"id": "20261110-ec-news-hold01", "result": "hold", "gate": "근거", "why": "제목의 '자료 게시'는 원문에 없음"})
        self._draft("20261110-ec-news-hold02")
        _write("db/verdicts/20261110-ec-news-hold02.json", {"id": "20261110-ec-news-hold02", "result": "hold", "gate": "확인 불가", "why": "원문을 열지 못함"})
        _run(holds_to_fix.main, ["--db-dir", "db", "--out", "fix.json"])
        fix = _read("fix.json")["fix"]
        self.assertEqual([(row["item"]["id"], row["newId"]) for row in fix], [("20261110-ec-news-hold01", "20261110-ec-news-hold01-r2")])
        # 다시 쓴 초안이 있으면 더 고르지 않고, 다시 쓴 것이 또 보류돼도 고르지 않는다
        self._draft("20261110-ec-news-hold01-r2", revises="20261110-ec-news-hold01")
        _write("db/verdicts/20261110-ec-news-hold01-r2.json", {"id": "20261110-ec-news-hold01-r2", "result": "hold", "gate": "근거", "why": "여전히 근거 없음"})
        _run(holds_to_fix.main, ["--db-dir", "db", "--out", "fix.json"])
        self.assertEqual(_read("fix.json")["fix"], [])

    def _unopened(self, item_id, at=None):
        _write(f"db/verdicts/{item_id}.json", {"id": item_id, "result": "hold", "gate": "확인 불가", "why": "원문을 열지 못함", "at": at or stamp()})

    def _resubmit(self):
        return _run(holds_to_recheck.main, ["--db-dir", "db", "--out-dir", "out", "--run-id", "collect-test"])[1]["resubmitted"]

    def test_drafts_held_for_an_unopened_source_are_resubmitted_twice(self):
        first = "20261110-carbon-pulse-aaa001"
        self._draft(first, tier="C", title="제목만 옮긴 소식")
        self._unopened(first)
        self._draft("20261110-ec-news-hold01")  # 글을 고쳐야 풀리는 보류는 이 프로그램이 다루지 않는다
        _write("db/verdicts/20261110-ec-news-hold01.json", {"id": "20261110-ec-news-hold01", "result": "hold", "gate": "근거", "why": "원문에 없음", "at": stamp()})
        self.assertEqual(self._resubmit(), [{"id": f"{first}-c2", "rechecks": first, "turn": 2}])
        copy = _read(f"out/items/{first}-c2.json")
        self.assertEqual((copy["id"], copy["rechecks"], copy["runId"], copy["title"], copy["tier"]), (f"{first}-c2", first, "collect-test", "제목만 옮긴 소식", "C"))
        # 이미 다시 낸 것은 또 내지 않는다
        _write(f"db/items/{first}-c2.json", copy)
        self.assertEqual(self._resubmit(), [])
        # 다시 낸 것도 열리지 않으면 한 번 더 내고, 세 번째까지 열리지 않으면 더 내지 않는다
        self._unopened(f"{first}-c2")
        self.assertEqual(self._resubmit(), [{"id": f"{first}-c3", "rechecks": f"{first}-c2", "turn": 3}])
        _write(f"db/items/{first}-c3.json", _read(f"out/items/{first}-c3.json"))
        self._unopened(f"{first}-c3")
        self.assertEqual(self._resubmit(), [])

    def test_old_holds_are_not_resubmitted(self):
        old = (now_kst() - datetime.timedelta(days=30)).isoformat(timespec="seconds")
        self._draft("20261010-carbon-pulse-old001")
        self._unopened("20261010-carbon-pulse-old001", at=old)
        self._draft("20261110-carbon-pulse-nodate")  # 판정 시각을 읽지 못하면 막지 않는다
        _write("db/verdicts/20261110-carbon-pulse-nodate.json", {"id": "20261110-carbon-pulse-nodate", "result": "hold", "gate": "확인 불가", "why": "원문을 열지 못함"})
        self.assertEqual([row["id"] for row in self._resubmit()], ["20261110-carbon-pulse-nodate-c2"])

    def test_recheck_marks(self):
        self.assertEqual([rechecks.attempt(name) for name in ("a", "a-r2", "a-c2", "a-r2-c3")], [1, 1, 2, 3])
        self.assertEqual([rechecks.next_id(name) for name in ("a", "a-c2", "a-c3", "a-r2")], ["a-c2", "a-c3", "", "a-r2-c2"])
        self.assertEqual((rechecks.root("a-r2-c3"), rechecks.is_last("a-c2"), rechecks.is_last("a-c3")), ("a-r2", False, True))

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

    def test_digest_can_take_the_place_of_another(self):
        _write("first.json", {"from": "2026-11-09", "to": "2026-11-15", "title": "첫 요약", "paragraphs": ["문단"], "itemIds": ["seed-one"]})
        _write("wide.json", {"from": "2026-10-12", "to": "2026-11-11", "title": "긴 기간의 요약", "paragraphs": ["문단"], "itemIds": ["seed-one"]})
        _run(add_digest.main, ["--file", "first.json"])
        _write("bad.json", {"from": "2026-10-12", "to": "2026-11-11", "title": "", "paragraphs": ["문단"], "itemIds": []})
        self.assertEqual(_run(add_digest.main, ["--file", "bad.json", "--drop", "2026-11-09_2026-11-15"])[0], 1)
        self.assertEqual([row["id"] for row in _read("data/digests.json")["digests"]], ["2026-11-09_2026-11-15"])  # 검사에 걸리면 빼지도 않는다
        _run(add_digest.main, ["--file", "wide.json", "--drop", "2026-11-09_2026-11-15"])
        self.assertEqual([row["id"] for row in _read("data/digests.json")["digests"]], ["2026-10-12_2026-11-11"])

    def test_withdraw_keeps_the_item(self):
        code, _ = _run(withdraw.main, ["--id", "seed-one", "--reason", "수치가 원문과 다름"])
        self.assertEqual(code, 0)
        item = _read("data/items.json")["items"][0]
        self.assertEqual(item["withdrawn"]["reason"], "수치가 원문과 다름")
        self.assertEqual(_run(withdraw.main, ["--id", "none", "--reason", "x"])[0], 1)

    def test_merge_moves_the_item_aside_and_repoints_digests(self):
        items = _read("data/items.json")
        items["items"].append({"id": "kept", "title": "남길 소식", "summary": "EU 집행위원회는 2026년 11월 6일에 새 가이던스를 알렸습니다.", "published": "2026-11-06", "listed": "2026-11-10"})
        _write("data/items.json", items)
        _write("data/digests.json", {"digests": [{"id": "w", "from": "2026-11-09", "to": "2026-11-15", "title": "t", "paragraphs": ["p"], "itemIds": ["seed-one", "kept"]}]})
        self.assertEqual(_run(merge.main, ["--id", "seed-one", "--into", "nope", "--reason", "같은 일"])[0], 1)
        self.assertEqual(len(_read("data/items.json")["items"]), 2)
        # 새 요약의 날짜가 근거 글에 없으면 묶지 않는다
        _write("language/glossary.json", {"terms": []})
        _write("source.txt", "New guidance. 6 November 2026.")
        pathlib.Path("summary.txt").write_text("EU 집행위원회는 2026년 11월 6일에 새 가이던스를 알렸습니다. CBAM 소식 화면에는 이 소식이 2026년 10월 22일자로 올라 있습니다.", encoding="utf-8")
        self.assertEqual(_run(merge.main, ["--id", "seed-one", "--into", "kept", "--reason", "같은 일", "--summary-file", "summary.txt", "--source-file", "source.txt"])[0], 1)
        self.assertEqual(len(_read("data/items.json")["items"]), 2)
        pathlib.Path("source.txt").write_text("New guidance. 6 November 2026.\n22Oct2026\nNew guidance", encoding="utf-8")
        code, result = _run(merge.main, ["--id", "seed-one", "--into", "kept", "--reason", "같은 일", "--summary-file", "summary.txt", "--source-file", "source.txt"])
        self.assertEqual((code, result["merged"], result["digests"], result["left"]), (0, True, 1, 1))
        kept = _read("data/items.json")["items"][0]
        self.assertEqual(kept["id"], "kept")
        self.assertIn("10월 22일", kept["summary"])
        self.assertEqual(_read("data/digests.json")["digests"][0]["itemIds"], ["kept"])
        record = _read("data/merged.json")["merged"][0]
        self.assertEqual((record["id"], record["into"], record["item"]["title"]), ("seed-one", "kept", "기존 항목"))

    def test_moved_table_follows_chains_to_a_live_item(self):
        records = [{"id": "a", "into": "b"}, {"id": "b", "into": "c"}, {"id": "x", "into": "gone"}]
        self.assertEqual(merge.moved(records, {"c"}), {"a": "c", "b": "c"})

    def test_last_week_and_sample(self):
        self.assertEqual(week_items.last_week(datetime.date(2026, 11, 16)), (datetime.date(2026, 11, 9), datetime.date(2026, 11, 15)))
        self.assertEqual(week_items.last_week(datetime.date(2026, 11, 22)), (datetime.date(2026, 11, 9), datetime.date(2026, 11, 15)))
        _run(week_items.main, ["--out", "week.json", "--date", "2026-11-16", "--audit", "3"])
        week = _read("week.json")
        self.assertEqual((week["id"], len(week["items"]), week["audit"]), ("2026-11-09_2026-11-15", 1, ["seed-one"]))
        self.assertIn("기존 항목", pathlib.Path("week.txt").read_text(encoding="utf-8"))

    def test_week_takes_backfill_by_its_own_date_and_marks_late_items(self):
        start, end = datetime.date(2026, 11, 9), datetime.date(2026, 11, 15)
        rows = [
            {"id": "old-news-listed-now", "published": "2026-08-28", "listed": "2026-11-10"},
            {"id": "weekend-news", "published": "2026-11-07", "listed": "2026-11-09"},
            {"id": "this-week", "published": "2026-11-12", "listed": "2026-11-13"},
            {"id": "filled-this-week", "published": "2026-11-10", "listed": "2026-11-10", "backfill": True},
            {"id": "filled-long-ago", "published": "2026-06-12", "listed": "2026-11-10", "backfill": True},
            {"id": "filled-no-date", "listed": "2026-11-10", "backfill": True},
            {"id": "next-week", "published": "2026-11-16", "listed": "2026-11-16"},
        ]
        found = week_items.of_week(rows, start, end)
        self.assertEqual([(row["id"], row["late"]) for row in found],
                         [("this-week", False), ("filled-this-week", False), ("weekend-news", False), ("old-news-listed-now", True)])

    def test_health_reports_a_missing_web_approval_on_the_first_day(self):
        from tools.run import health
        blocked = {"sources": {"op-europa": {"ok": False, "failCount": 1, "note": "403으로 막힘"},
                               "council-cbam": {"ok": False, "failCount": 1, "note": "웹 읽기 승인 대기 시간 초과"},
                               "ep-train": {"ok": False, "failCount": 1, "note": "웹 읽기 승인 대기 시간 초과"},
                               "oecd-blog": {"ok": True, "failCount": 0, "note": ""}}}
        found = health._source_problems({"sources": {}}, blocked)
        self.assertEqual(len(found), 1)  # 사이트 쪽 사정으로 한 번 못 읽은 것은 아직 알리지 않는다
        self.assertTrue(found[0].startswith("예약 실행이 웹 읽기 승인을 받지 못해 출처 2곳을 열지 못함(council-cbam, ep-train)"))
        blocked["sources"]["op-europa"]["failCount"] = 3
        self.assertIn("출처 op-europa: 직접 열람이 3회 연속 실패(403으로 막힘)", health._source_problems({"sources": {}}, blocked))
        # 도구가 돌려준 오류 이름만 적혀 있어도 같은 문제로 묶는다
        blocked["sources"]["ep-train"]["note"] = "PROVENANCE_REQUIRED"
        self.assertIn("(council-cbam, ep-train)", health._source_problems({"sources": {}}, blocked)[-1])
        # 출처 대장에서 직접 열람을 그만둔 출처의 옛 기록은 알리지 않는다
        only = health._source_problems({"sources": {}}, blocked, {"council-cbam"})
        self.assertEqual(len(only), 1)
        self.assertIn("출처 1곳을 열지 못함(council-cbam)", only[0])
        self.assertEqual(health._source_problems({"sources": {}}, blocked, set()), [])

    def test_claude_status_counts_failures(self):
        _run(claude_status.main, ["council-cbam=ok", "op-europa=fail:403으로 막힘"])
        _run(claude_status.main, ["op-europa=fail:403으로 막힘"])
        book = _read("collected/claude-status.json")["sources"]
        self.assertEqual((book["council-cbam"]["ok"], book["op-europa"]["failCount"], book["op-europa"]["lastOk"]), (True, 2, ""))
        _run(claude_status.main, ["op-europa=ok"])
        self.assertEqual(_read("collected/claude-status.json")["sources"]["op-europa"]["failCount"], 0)
        # 출처 대장이 있으면, 직접 열람을 그만둔 출처의 기록은 다음에 적을 때 지워진다
        _write("sources/registry.json", {"sources": [{"code": "council-cbam", "collector": "claude"}, {"code": "op-europa", "collector": "off"}]})
        _run(claude_status.main, ["council-cbam=fail:검색 결과에 주소가 없음"])
        book = _read("collected/claude-status.json")["sources"]
        self.assertEqual((sorted(book), book["council-cbam"]["failCount"], book["council-cbam"]["note"]), (["council-cbam"], 1, "검색 결과에 주소가 없음"))

    def test_claude_status_without_results_changes_nothing(self):
        _run(claude_status.main, ["council-cbam=ok"])
        before = pathlib.Path("collected/claude-status.json").read_text(encoding="utf-8")
        for argv in (["--help"], [], ["council-cbam"]):
            with contextlib.redirect_stdout(io.StringIO()):
                claude_status.main(argv)
            self.assertEqual(pathlib.Path("collected/claude-status.json").read_text(encoding="utf-8"), before, argv)

    def test_title_only_drafts_are_checked_against_the_collected_feed(self):
        day = now_kst().date().isoformat()
        _write(f"collected/feed/{day}.json", {"date": day, "items": [
            {"id": "aaaaaaaaaaaa", "source": "carbon-pulse", "kind": "link", "url": "https://example.org/569673/?site=cpp", "text": "FEATURE: A hard sell, experts say"},
            {"id": "bbbbbbbbbbbb", "source": "keco-cbam", "kind": "link", "url": "https://example.org/view.do?article_seq=1", "text": "월간 동향 37호"}]})
        _write("collected/feed/2020-01-01.json", {"date": "2020-01-01", "items": [{"id": "cccccccccccc", "source": "carbon-pulse", "kind": "link", "url": "https://example.org/old", "text": "오래된 기록"}]})
        _write("sources/registry.json", {"sources": [{"code": "carbon-pulse", "url": "https://example.org/category/cbam/"}, {"code": "keco-cbam", "url": "https://example.org/list.do"}]})

        def look(**fields):
            _write("db/items/x.json", {"id": "x", **fields})
            return _run(feed_title.main, ["--item-file", "db/items/x.json"])[1]

        found = look(candidateIds=["aaaaaaaaaaaa"], link="https://example.org/569673/?site=cpp")
        self.assertEqual((found["found"], found["linkMatches"]), (True, True))
        self.assertEqual((found["entries"][0]["text"], found["entries"][0]["feedDate"]), ("FEATURE: A hard sell, experts say", day))
        # 초안의 링크가 기록의 주소와 다르면 맞지 않는 것으로 본다. 다만 그 출처의 목록 화면 주소는 맞는 것으로 본다
        self.assertFalse(look(candidateIds=["aaaaaaaaaaaa"], link="https://example.org/569673/")["linkMatches"])
        self.assertTrue(look(candidateIds=["bbbbbbbbbbbb"], link="https://example.org/list.do")["linkMatches"])
        # 기록에 없는 후보, 너무 오래된 기록, 후보가 적히지 않은 초안은 찾지 못한 것이다
        self.assertFalse(look(candidateIds=["dddddddddddd"], link="https://example.org/a")["found"])
        self.assertFalse(look(candidateIds=["cccccccccccc"], link="https://example.org/old")["found"])
        self.assertFalse(look(link="https://example.org/569673/?site=cpp")["found"])

    def test_directly_opened_sources_come_with_their_search_words(self):
        from tools.run import prepare_collect
        day = now_kst().date().isoformat()
        _write("sources/registry.json", {"sources": [
            {"code": "council-cbam", "name": "Council", "url": "https://example.org/council/", "tier": "A", "collector": "claude", "find": "Council CBAM policy"},
            {"code": "op-europa", "name": "OP", "url": "https://example.org/op", "tier": "A", "collector": "off"},
            {"code": "keco-cbam", "name": "KECO", "url": "https://example.org/list.do", "tier": "B", "collector": "github"}]})
        _write(f"collected/feed/{day}.json", {"date": day, "items": [{"id": "bbbbbbbbbbbb", "source": "keco-cbam", "kind": "link", "url": "https://example.org/view.do?article_seq=1", "text": "월간 동향 37호"}]})
        with contextlib.redirect_stdout(io.StringIO()):
            prepare_collect.main(["--db-dir", "db", "--out", "candidates.json"])
        book = _read("candidates.json")
        self.assertEqual([(row["code"], row["url"], row["find"]) for row in book["claudeSources"]], [("council-cbam", "https://example.org/council/", "Council CBAM policy")])
        self.assertEqual([(row["id"], row["tier"], row["sourceUrl"]) for row in book["candidates"]], [("bbbbbbbbbbbb", "B", "https://example.org/list.do")])

    def test_one_line_items_keep_their_mark_when_published(self):
        self._draft("20261112-keco-cbam-brief1", brief=True, tier="B", summary="한국환경공단이 월간 동향 37호를 게시판에 올렸습니다.", events=[])
        self._draft("20261112-keco-cbam-full01", brief=False, tier="B", events=[])
        for item_id in ("20261112-keco-cbam-brief1", "20261112-keco-cbam-full01"):
            self._verdict(item_id, "pass")
        _, result = _run(add_items.main, ["--db-dir", "db"])
        self.assertEqual(sorted(result["added"]), ["20261112-keco-cbam-brief1", "20261112-keco-cbam-full01"])
        rows = {row["id"]: row for row in _read("data/items.json")["items"]}
        self.assertIs(rows["20261112-keco-cbam-brief1"].get("brief"), True)
        self.assertNotIn("brief", rows["20261112-keco-cbam-full01"])


class DaySummaryTest(unittest.TestCase):
    DAY = "2026-11-10"  # 화요일
    WEEKLY = {"kind": "weekly", "startedAt": "2026-11-09T09:10:00+09:00", "problems": []}  # 전날(월요일)의 주간 작업

    def test_normal_day(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {"written": 5, "rewritten": 1}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {"pass": 5, "hold": 1, "published": 5}, "pushed": True, "problems": [],
             "holds": [{"id": "a", "gate": "근거", "why": "제목이 원문과 다름"}]},
            {"kind": "collect", "startedAt": "2026-11-09T07:05:00+09:00", "counts": {"written": 9}, "problems": ["어제의 문제"]},
            self.WEEKLY,
        ]
        result = day_summary.summarize(runs, self.DAY)
        self.assertEqual((result["problems"], result["finalHolds"], result["retryHolds"]), ([], [], 1))
        self.assertEqual(result["counts"], {"written": 6, "pass": 5, "hold": 1, "published": 5})

    def test_missing_runs_and_final_holds(self):
        runs = [{"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": False, "problems": ["x: 게시 단계에서 막힘(사실 대조)"],
                 "holds": [{"id": "b", "gate": "확인 불가", "why": "원문을 열지 못함"}, {"id": "c-r2", "gate": "근거", "why": "다시 쓴 초안도 보류: 근거 없음"},
                           {"id": "d-c3", "gate": "확인 불가", "why": "원문을 열지 못함"}, {"id": "e", "gate": "출처", "why": "저장소의 글과 화면이 다름"},
                           {"id": "f-r2", "gate": "확인 불가", "why": "다시 쓴 초안도 보류: 원문을 열지 못함"}]}, self.WEEKLY]
        result = day_summary.summarize(runs, self.DAY)
        self.assertEqual(result["problems"], ["수집·작성 실행 기록이 없음", "x: 게시 단계에서 막힘(사실 대조)", "게시 데이터를 저장소에 올리지 못함"])
        # 원문을 열지 못한 보류는 세 번째(-c3)에야 사람이 볼 보류가 된다. 그 전에는 다시 낼 보류로 센다
        self.assertEqual([hold["id"] for hold in result["finalHolds"]], ["c-r2", "d-c3", "e"])
        self.assertEqual(result["retryHolds"], 2)

    def test_weekend_has_no_missing_run_problem(self):
        self.assertEqual(day_summary.summarize([], "2026-11-14")["problems"], [])

    def test_problems_of_an_adhoc_run_are_reported_too(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
            {"kind": "adhoc", "startedAt": "2026-11-10T01:00:00+09:00", "counts": {"revised": 3}, "problems": ["요약 보강: 웹 읽기가 되지 않음"]},
            {"kind": "report", "startedAt": "2026-11-10T10:05:00+09:00", "problems": ["보고 실행이 적은 글은 다시 모으지 않음"]},
            self.WEEKLY,
        ]
        result = day_summary.summarize(runs, self.DAY)
        self.assertEqual(result["problems"], ["요약 보강: 웹 읽기가 되지 않음"])
        self.assertEqual(result["runs"], {"collect": 1, "verify": 1, "adhoc": 1, "translate": 0, "review": 0})

    def test_problems_of_runs_after_the_last_report_are_reported(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
            {"kind": "report", "startedAt": "2026-11-09T10:05:30+09:00", "finishedAt": "2026-11-09T10:07:00+09:00", "problems": []},
            {"kind": "translate", "startedAt": "2026-11-09T16:15:00+09:00", "finishedAt": "2026-11-09T16:25:00+09:00", "problems": ["번역: 검사를 통과하지 못해 올리지 않음"]},
            {"kind": "translate", "startedAt": "2026-11-09T09:15:00+09:00", "finishedAt": "2026-11-09T09:25:00+09:00", "problems": ["어제 보고에 이미 실린 문제"]},
            # 지난 보고가 도는 동안 끝난 실행: 그 보고가 보지 못했으므로 이번에 싣는다
            {"kind": "translate", "startedAt": "2026-11-09T09:58:00+09:00", "finishedAt": "2026-11-09T10:06:10+09:00", "problems": ["보고와 엇갈려 끝난 실행의 문제"]},
            self.WEEKLY,
        ]
        result = day_summary.summarize(runs, self.DAY)
        self.assertEqual(sorted(result["problems"]), ["번역: 검사를 통과하지 못해 올리지 않음", "보고와 엇갈려 끝난 실행의 문제"])
        self.assertEqual(result["runs"]["translate"], 2)

    def test_problems_of_translation_review_runs_are_reported(self):
        # 번역 검수는 번역과 다른 예약 작업(다른 모델)이 한다. 그 실행이 적은 문제도 보고에 실린다
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
            {"kind": "report", "startedAt": "2026-11-09T10:05:30+09:00", "finishedAt": "2026-11-09T10:07:00+09:00", "problems": []},
            {"kind": "review", "startedAt": "2026-11-09T13:05:00+09:00", "finishedAt": "2026-11-09T13:12:00+09:00", "problems": ["검수: 일부러 바꾼 번역을 두 번 놓침"]},
            {"kind": "review", "startedAt": "2026-11-08T13:05:00+09:00", "finishedAt": "2026-11-08T13:12:00+09:00", "problems": ["지난 보고에 이미 실린 문제"]},
            self.WEEKLY,
        ]
        result = day_summary.summarize(runs, self.DAY)
        self.assertEqual(result["problems"], ["검수: 일부러 바꾼 번역을 두 번 놓침"])
        self.assertEqual(result["runs"]["review"], 1)

    def test_on_monday_the_weekend_runs_are_looked_at_too(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-16T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-16T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
            {"kind": "report", "startedAt": "2026-11-13T10:06:04+09:00", "finishedAt": "2026-11-13T10:06:54+09:00", "problems": ["금요일 보고가 실은 글"]},
            {"kind": "translate", "startedAt": "2026-11-13T05:51:00+09:00", "finishedAt": "2026-11-13T06:02:00+09:00", "problems": ["금요일 아침의 문제(금요일 보고가 이미 알림)"]},
            {"kind": "translate", "startedAt": "2026-11-13T12:15:00+09:00", "finishedAt": "2026-11-13T12:25:00+09:00", "problems": ["금요일 보고 뒤 번역의 문제"]},
            {"kind": "translate", "startedAt": "2026-11-14T12:15:00+09:00", "finishedAt": "2026-11-14T12:20:00+09:00", "problems": ["토요일 번역의 문제"]},
            {"kind": "adhoc", "startedAt": "2026-11-15T20:00:00+09:00", "finishedAt": "2026-11-15T20:30:00+09:00", "problems": ["일요일 임시 작업의 문제"]},
        ]
        result = day_summary.summarize(runs, "2026-11-16")   # 월요일
        self.assertEqual(sorted(result["problems"]), ["금요일 보고 뒤 번역의 문제", "일요일 임시 작업의 문제", "토요일 번역의 문제"])

    def test_without_a_last_report_in_the_records_everything_fetched_is_looked_at(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
            {"kind": "translate", "startedAt": "2026-11-08T16:15:00+09:00", "problems": ["그제의 문제"]},
            {"kind": "translate", "startedAt": "2026-11-11T00:10:00+09:00", "problems": ["내일의 실행(받아 온 기록에 섞여 있어도 보지 않는다)"]},
            self.WEEKLY,
        ]
        self.assertEqual(day_summary.summarize(runs, self.DAY)["problems"], ["그제의 문제"])

    def test_a_missing_weekly_run_is_reported_on_tuesday(self):
        runs = [
            {"kind": "collect", "startedAt": "2026-11-10T07:05:00+09:00", "counts": {}, "problems": []},
            {"kind": "verify", "startedAt": "2026-11-10T08:20:00+09:00", "counts": {}, "pushed": True, "problems": []},
        ]
        self.assertEqual(day_summary.summarize(runs, self.DAY)["problems"], ["어제(월요일)의 주간 작업 실행 기록이 없음"])
        self.assertEqual(day_summary.summarize(runs + [self.WEEKLY], self.DAY)["problems"], [])
        monday = [{**run, "startedAt": run["startedAt"].replace("2026-11-10", "2026-11-09")} for run in runs]
        self.assertEqual(day_summary.summarize(monday, "2026-11-09")["problems"], [])   # 월요일 보고는 아직 묻지 않는다


class SiteInfoTest(unittest.TestCase):
    def test_address_comes_from_the_site_settings_and_ends_with_a_slash(self):
        from tools.common import siteinfo
        self.assertEqual(siteinfo.site_url({"url": "https://example.org/watch"}), "https://example.org/watch/")
        self.assertEqual(siteinfo.site_url({}), siteinfo.DEFAULT_URL)
        self.assertTrue(siteinfo.site_url().startswith("https://") and siteinfo.site_url().endswith("/"))

    def test_deploying_elsewhere_needs_an_owner_and_a_name(self):
        from tools.common import siteinfo
        self.assertEqual(siteinfo.site_repo({"siteRepo": ""}), "")
        self.assertEqual(siteinfo.site_repo({"siteRepo": "someone/site"}), "someone/site")
        self.assertEqual(siteinfo.site_repo({"siteRepo": "https://github.com/someone/site"}), "")  # 주소가 아니라 이름을 적는다
        self.assertEqual(siteinfo.deploy_remote({"siteRepo": ""}), "origin")
        self.assertEqual(siteinfo.deploy_remote({"siteRepo": "someone/site"}), "https://github.com/someone/site")

    def test_the_deploy_setting_of_this_repository_is_readable(self):
        from tools.common import siteinfo
        self.assertIn(siteinfo.deploy_remote().split(":")[0], ("origin", "https"))  # 값은 운영 설정이므로 꼴만 본다


if __name__ == "__main__":
    unittest.main()

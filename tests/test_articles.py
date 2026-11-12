"""공공기관 게시글의 본문 받기: 본문 자리 찾기, 이용 조건 확인, 수집 기록에 경로 적기, 되풀이 한도, 상태 점검."""
import datetime
import json
import os
import pathlib
import tempfile
import unittest

from tools.collect import article_text, articles
from tools.common.jsonio import KST
from tools.run import articles_health

NOW = datetime.datetime(2026, 11, 12, 12, 30, tzinfo=KST)
TITLE = "시험용 게시글: 탄소국경조정제도 설명회 안내"
LICENSE = "시험부 보도자료저작물은 '공공누리 1유형(출처표시)' 조건에 따라 누구나 이용할 수 있습니다."
BODY = ["시험부는 2026년 11월 20일에 탄소국경조정제도 설명회를 연다고 밝혔다.",
        "설명회는 수출 기업의 담당자를 대상으로 하며 배출량 산정 방법과 검증 절차를 다룬다.",
        "참가 신청은 11월 18일까지 받으며 자세한 내용은 붙임 자료에서 볼 수 있다.",
        "이 글은 시험을 위해 지어낸 것으로 실제 기관의 발표가 아니다. " * 8]


def page(title=TITLE, license_text=LICENSE, body=BODY):
    """정부 게시판의 글 화면을 흉내 낸 HTML. 메뉴, 지나온 길, 머리, 본문, 만족도 조사, 바닥글 차례다."""
    paragraphs = "".join(f"<p>{line}</p>" for line in body)
    return f"""<html><head><title>{title} | 보도자료</title></head><body>
<ul><li><a href="/news">알림·소식</a></li><li><a href="/news/press">보도자료</a></li><li><a href="/policy">정책·정보</a></li></ul>
<div class="path"><span>메인</span><span>알림·소식</span><span>{title}</span></div>
<p>{license_text}</p>
<h3>{title}</h3>
<ul><li>담당부서 시험과</li><li>등록일 2026-11-11</li><li>조회수 12</li></ul>
<div class="view">{paragraphs}</div>
<p>만족도 조사</p><p>이 페이지에서 제공하는 정보에 만족하셨습니까?</p>
<div>이전글</div><div>다음글</div>
<footer><p>시험부 주소와 전화번호, 개인정보처리방침, 저작권정책</p>{"<p>바닥글을 채우는 줄</p>" * 20}</footer>
</body></html>""".encode("utf-8")


def answer(body, status=200, content_type="text/html; charset=utf-8"):
    return status, {"Content-Type": content_type}, body, ""


class ArticleTextTest(unittest.TestCase):
    def test_body_starts_at_the_heading_and_stops_before_the_survey(self):
        lines = ["알림·소식", "보도자료", TITLE, "다른 메뉴", TITLE, "담당부서 시험과", "등록일 2026-11-11"] + BODY + ["만족도 조사", "바닥글"]
        kept, found = article_text.body(lines, TITLE)
        self.assertTrue(found)
        self.assertEqual(kept[0], TITLE)
        self.assertEqual(kept[1], "담당부서 시험과")  # 메뉴에 적힌 같은 제목이 아니라 등록일이 따르는 머리 줄에서 시작한다
        self.assertEqual(kept[-1], BODY[-1])

    def test_contact_lines_under_the_heading_are_left_out(self):
        lines = [TITLE, "담당자홍길동", "담당부서시험과", "연락처044-000-0000", "등록일2026-11-11", "조회수457", "첨부파일"] + BODY + ["담당자가 설명회를 진행한다고 적은 본문 문장"] * 12
        kept, _ = article_text.body(lines + ["만족도 조사"], TITLE)
        self.assertEqual(kept[:4], [TITLE, "담당부서시험과", "등록일2026-11-11", "첨부파일"])
        self.assertEqual(kept[-1], "담당자가 설명회를 진행한다고 적은 본문 문장")  # 머리에서 멀리 떨어진 본문의 줄은 그대로 둔다

    def test_title_is_matched_whatever_the_spacing(self):
        kept, found = article_text.body(["메뉴", "시험용  게시글:탄소국경조정제도 설명회 안내", "등록일 2026-11-11", "본문"], TITLE)
        self.assertTrue(found)
        self.assertEqual(kept, ["시험용  게시글:탄소국경조정제도 설명회 안내", "등록일 2026-11-11", "본문"])

    def test_without_the_title_the_whole_page_is_kept_and_reported(self):
        kept, found = article_text.body(["메뉴", "본문 한 줄", "목록", "바닥글"], TITLE)
        self.assertFalse(found)
        self.assertEqual(kept, ["메뉴", "본문 한 줄"])

    def test_a_stop_word_inside_a_sentence_does_not_end_the_body(self):
        kept, _ = article_text.body([TITLE, "등록일 2026-11-11", "대상 품목의 목록은 붙임과 같다.", "다음 글에서 이어진다고 적은 문장", "목록", "바닥글"], TITLE)
        self.assertEqual(kept[-1], "다음 글에서 이어진다고 적은 문장")

    def test_source_specific_stop_and_length_limits(self):
        kept, _ = article_text.body([TITLE, "등록일 2026-11-11", "본문", LICENSE, "뒤따르는 글"], TITLE, ["공공누리 1유형"])
        self.assertEqual(kept[-1], "본문")
        many, _ = article_text.body([TITLE, "등록일 2026-11-11"] + ["가" * 100] * 500, TITLE)
        self.assertLessEqual(sum(len(line) for line in many), article_text.MAX_CHARS)
        self.assertLessEqual(len(many), article_text.MAX_LINES)

    def test_license_line_and_length(self):
        self.assertEqual(article_text.license_line(["메뉴", LICENSE], ["공공누리 제1유형", "공공누리 1유형"]), LICENSE)
        self.assertEqual(article_text.license_line(["공공누리  1 유형 조건"], ["공공누리 1유형"]), "공공누리  1 유형 조건")
        self.assertEqual(article_text.license_line(["공공누리 2유형(출처표시+상업적이용금지)"], ["공공누리 1유형", "공공누리 제1유형"]), "")
        self.assertEqual(article_text.license_line(["메뉴"], []), "")
        self.assertTrue(article_text.long_enough(BODY))
        self.assertFalse(article_text.long_enough(["첨부 파일을 참고"]))


class FillTest(unittest.TestCase):
    def setUp(self):
        self.here = pathlib.Path.cwd()
        self.folder = tempfile.TemporaryDirectory()
        os.chdir(self.folder.name)
        sources = [
            {"code": "ministry", "name": "시험부 보도자료", "url": "https://gov.example/board", "tier": "B", "collector": "github", "watch": ["links"],
             "articles": {"license": ["공공누리 1유형", "공공누리 제1유형"]}},
            {"code": "agency", "name": "시험공단", "url": "https://agency.example/board", "tier": "B", "collector": "github", "watch": ["links"]},
            {"code": "switched-off", "name": "꺼 둔 곳", "url": "https://off.example/", "tier": "B", "collector": "off", "watch": ["links"],
             "articles": {"license": ["공공누리 1유형"]}},
        ]
        self._write("sources/registry.json", {"sources": sources, "keywords": []})
        self.rows = [
            {"id": "aaa", "source": "ministry", "kind": "link", "url": "https://gov.example/board/1/view", "text": TITLE},
            {"id": "bbb", "source": "ministry", "kind": "link", "url": "https://elsewhere.example/post", "text": "다른 사이트로 가는 링크"},
            {"id": "ccc", "source": "ministry", "kind": "link", "url": "https://gov.example/attach/down/abc", "text": "붙임 파일"},
            {"id": "ddd", "source": "ministry", "kind": "line", "url": "https://gov.example/board", "text": "화면의 한 줄"},
            {"id": "eee", "source": "agency", "kind": "link", "url": "https://agency.example/board/9", "text": "본문을 받지 않는 출처의 글"},
            {"id": "fff", "source": "switched-off", "kind": "link", "url": "https://off.example/1", "text": "꺼 둔 출처의 글"},
        ]
        self._write("collected/feed/2026-11-12.json", {"date": "2026-11-12", "items": self.rows})
        self.opened = []

    def tearDown(self):
        os.chdir(self.here)
        self.folder.cleanup()

    def _write(self, path, value):
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def _feed(self, date="2026-11-12"):
        return {row["id"]: row for row in json.loads(pathlib.Path(f"collected/feed/{date}.json").read_text(encoding="utf-8"))["items"]}

    def _fetcher(self, body):
        """body가 {주소: 화면}이면 주소마다 다른 화면을 주고("*"는 그 밖의 주소), 아니면 모든 주소에 같은 화면을 준다."""
        def fetch(url):
            self.opened.append(url)
            found = body.get(url, body.get("*")) if isinstance(body, dict) else body
            return found if isinstance(found, tuple) else answer(found)
        return fetch

    def _fill(self, body, **more):
        return articles.fill(moment=more.pop("moment", NOW), fetcher=self._fetcher(body), pause=0, **more)

    def test_only_the_marked_source_and_its_own_pages_are_fetched(self):
        done = self._fill(page())
        self.assertEqual(self.opened, ["https://gov.example/board/1/view"])
        self.assertEqual((done["saved"], done["failed"], done["sources"]), (["aaa"], [], ["ministry"]))
        rows = self._feed()
        self.assertEqual(rows["aaa"]["textPath"], "collected/pages/items/aaa.txt")
        self.assertTrue(all("textPath" not in rows[key] for key in ("bbb", "ccc", "ddd", "eee", "fff")))

    def test_saved_text_names_its_source_and_terms_and_holds_only_the_article(self):
        self._fill(page())
        lines = pathlib.Path("collected/pages/items/aaa.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "[주소] https://gov.example/board/1/view")
        self.assertEqual(lines[1], "[출처] 시험부 보도자료")
        self.assertEqual(lines[2], f"[이용 조건] {LICENSE}")
        self.assertTrue(lines[3].startswith("[받은 때] 2026-11-12T12:30:00"))
        body = lines[5:]
        self.assertEqual(body[0], TITLE)
        self.assertIn("등록일 2026-11-11", body)
        self.assertEqual(body[-1], BODY[-1].strip())
        self.assertFalse(any("바닥글" in line or "만족도" in line or "정책·정보" in line for line in body))

    def test_a_page_without_the_terms_is_not_stored(self):
        done = self._fill(page(license_text="이 화면에는 이용 조건이 적혀 있지 않다."))
        self.assertEqual((done["saved"], done["failed"]), ([], ["aaa"]))
        self.assertFalse(pathlib.Path("collected/pages/items/aaa.txt").exists())
        self.assertNotIn("textPath", self._feed()["aaa"])
        state = json.loads(pathlib.Path(articles.STATE).read_text(encoding="utf-8"))
        self.assertEqual((state["items"]["aaa"]["result"], state["items"]["aaa"]["tries"]), (articles.NO_LICENSE, 1))

    def test_terms_written_once_on_the_board_page_count_for_its_articles(self):
        bare = page(license_text="이 글의 화면에는 이용 조건이 적혀 있지 않다.")
        second = dict(self.rows[0], id="aab", url="https://gov.example/board/2/view")
        self._write("collected/feed/2026-11-12.json", {"date": "2026-11-12", "items": self.rows + [second]})
        done = self._fill({"https://gov.example/board": page(title="보도자료 목록"), "*": bare})
        self.assertEqual(done["saved"], ["aaa", "aab"])
        self.assertEqual(self.opened.count("https://gov.example/board"), 1)  # 게시판 화면은 한 번만 받는다
        lines = pathlib.Path("collected/pages/items/aaa.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[2], f"[이용 조건] {LICENSE} (게시판 화면 https://gov.example/board 에 적힌 글)")
        self.assertEqual(lines[5], TITLE)

    def test_when_no_terms_are_found_the_record_keeps_how_the_page_words_them(self):
        other = "시험부 저작물은 공공누리 2유형(출처표시+상업적이용금지) 조건에 따라 이용할 수 있습니다."
        done = self._fill(page(license_text=other))
        self.assertEqual(done["failed"], ["aaa"])
        state = json.loads(pathlib.Path(articles.STATE).read_text(encoding="utf-8"))["items"]["aaa"]
        self.assertEqual(state["result"], articles.NO_LICENSE)
        self.assertIn(other, state["hints"])

    def test_short_pages_files_and_errors_are_not_stored(self):
        for body, expected in ((page(body=["붙임 파일을 참고"]), articles.TOO_SHORT), (answer(b"%PDF" * 400, content_type="application/pdf"), "HTML이 아님"),
                               ((404, {}, b"", "HTTP Error 404: Not Found"), "404"), ((0, {}, b"", "robots.txt가 이 주소의 자동 읽기를 막음"), "robots.txt")):
            with self.subTest(expected=expected):
                pathlib.Path(articles.STATE).unlink(missing_ok=True)
                done = self._fill(body)
                self.assertEqual(done["failed"], ["aaa"])
                state = json.loads(pathlib.Path(articles.STATE).read_text(encoding="utf-8"))
                self.assertIn(expected, state["items"]["aaa"]["result"])

    def test_a_stored_article_is_not_fetched_again_and_failures_stop_after_the_limit(self):
        self._fill(page())
        self._fill(page())
        self.assertEqual(len(self.opened), 1)
        pathlib.Path("collected/pages/items/aaa.txt").unlink()  # 파일이 사라졌으면 다시 받는다
        self._fill(page())
        self.assertEqual(len(self.opened), 2)

        self.opened.clear()
        self._write("collected/feed/2026-11-12.json", {"date": "2026-11-12", "items": self.rows})
        pathlib.Path(articles.STATE).unlink()
        pathlib.Path("collected/pages/items/aaa.txt").unlink()
        for _ in range(articles.MAX_TRIES + 2):
            self._fill((503, {}, b"", "HTTP Error 503"))
        self.assertEqual(len(self.opened), articles.MAX_TRIES)

    def test_older_days_are_filled_and_the_limit_holds(self):
        older = [{"id": f"old{n}", "source": "ministry", "kind": "link", "url": f"https://gov.example/board/old{n}/view", "text": TITLE} for n in range(3)]
        self._write("collected/feed/2026-11-10.json", {"date": "2026-11-10", "items": older})
        self._write("collected/feed/2026-11-01.json", {"date": "2026-11-01", "items": [dict(older[0], id="ancient")]})
        done = self._fill(page(), limit=2)
        self.assertEqual((done["saved"], done["left"]), (["old0", "old1"], 2))
        self.assertIn("textPath", self._feed("2026-11-10")["old0"])
        done = self._fill(page(), limit=8)
        self.assertEqual(done["saved"], ["old2", "aaa"])  # 이레보다 오래된 날의 기록은 보지 않는다
        self.assertFalse(pathlib.Path("collected/pages/items/ancient.txt").exists())

    def test_old_attempts_are_dropped_from_the_record(self):
        self._write(articles.STATE, {"items": {"gone": {"source": "ministry", "result": "열리지 않음", "tries": 3, "at": "2026-08-01T05:20:00+09:00"},
                                                 "kept": {"source": "ministry", "result": "열리지 않음", "tries": 3, "at": "2026-11-01T05:20:00+09:00"}}})
        self._fill(page())
        self.assertEqual(sorted(json.loads(pathlib.Path(articles.STATE).read_text(encoding="utf-8"))["items"]), ["aaa", "kept"])


class HealthTest(unittest.TestCase):
    def _problems(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "articles.json"
            path.write_text(json.dumps({"items": rows}, ensure_ascii=False), encoding="utf-8")
            return articles_health.problems(NOW, str(path))

    def test_repeated_misses_of_one_source_are_reported_once(self):
        row = {"source": "ministry", "result": articles.NO_LICENSE, "tries": 3, "at": "2026-11-12T05:21:00+09:00"}
        self.assertEqual(self._problems({"a": row, "b": row}), [])
        found = self._problems({"a": row, "b": row, "c": row, "d": dict(row, result=articles.SAVED)})
        self.assertEqual(len(found), 1)
        self.assertIn("ministry", found[0])
        self.assertIn("3건", found[0])
        self.assertIn(articles.NO_LICENSE, found[0])

    def test_old_misses_mixed_reasons_and_a_missing_record_are_quiet(self):
        old = {"source": "ministry", "result": articles.NO_LICENSE, "tries": 3, "at": "2026-10-20T05:21:00+09:00"}
        self.assertEqual(self._problems({"a": old, "b": old, "c": old}), [])
        mixed = [dict(old, at="2026-11-12T05:21:00+09:00", result=why) for why in (articles.NO_LICENSE, articles.TOO_SHORT, "열리지 않음(상태 503)")]
        self.assertEqual(self._problems(dict(zip("abc", mixed))), [])
        self.assertEqual(articles_health.problems(NOW, "/nonexistent/articles.json"), [])


if __name__ == "__main__":
    unittest.main()

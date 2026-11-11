"""실무 달력 자료(data/duties.json)의 검사, 일정으로 바꾸기, 겹치는 일정 가리기."""
import copy
import unittest

from tools.common.jsonio import read_json
from tools.publish import duties


class DutiesTest(unittest.TestCase):
    def setUp(self):
        self.body = read_json(duties.SOURCE, None)

    def test_the_stored_duties_match_the_legal_texts(self):
        self.assertEqual(duties.problems(self.body), [])
        self.assertEqual({duty["scheme"] for duty in self.body["duties"]}, {"eu", "uk"})

    def test_the_date_must_be_written_in_the_quoted_phrases(self):
        self.assertTrue(duties.date_in_phrases("2027-09-30", ["By 30 September of each year, and for the first time in 2027 for the year 2026"]))
        self.assertTrue(duties.date_in_phrases("2028-05-31", ["before the end of 31st May 2028"]))
        self.assertFalse(duties.date_in_phrases("2027-09-30", ["By 30 September of each year"]))        # 해가 없음
        self.assertFalse(duties.date_in_phrases("2027-10-01", ["on 31 October 2027", "11 October 2027"]))   # 다른 날
        self.assertFalse(duties.date_in_phrases("2027-10", ["October 2027"]))

    def test_a_moved_date_is_reported_as_drift(self):
        body = copy.deepcopy(self.body)
        duty = next(row for row in body["duties"] if row["id"] == "eu-cancellation-2026")
        duty["date"] = "2027-11-02"
        found = duties.problems(body)
        self.assertEqual([where for where, _ in found], ["의무 eu-cancellation-2026"])
        self.assertTrue(found[0][1].startswith("근거 어긋남"))
        self.assertEqual(duties.problems(body, kinds=("format",)), [])

    def test_shape_and_wording_are_checked(self):
        body = copy.deepcopy(self.body)
        body["duties"][0]["text"] = "이날까지 신청한다."
        body["duties"][1]["kind"] = "행사"
        found = [what for _, what in duties.problems(body, kinds=("format",))]
        self.assertTrue(any("표기 규칙" in what for what in found))
        self.assertTrue(any("종류" in what for what in found))

    def test_a_listed_event_about_the_same_thing_gives_way(self):
        same = {"date": "2027-02", "title": "CBAM 인증서를 공통 중앙 플랫폼에서 구매하기 시작", "kind": "시행"}
        other = {"date": "2027-02", "title": "다른 제도의 시행", "kind": "시행"}
        self.assertTrue(duties.superseded(same, self.body))
        self.assertFalse(duties.superseded(other, self.body))
        self.assertFalse(duties.superseded({**same, "kind": "기한"}, self.body))

    def test_events_and_the_public_shape(self):
        rows = duties.events(self.body)
        self.assertEqual(len(rows), len(self.body["duties"]))
        first = next(row for row in rows if row["duty"] == "eu-first-declaration")
        self.assertEqual((first["date"], first["kind"], first["scheme"]), ("2027-09-30", "기한", "EU CBAM"))
        public = duties.public(self.body)
        self.assertTrue(all("evidence" not in duty and "covers" not in duty for duty in public["duties"]))
        self.assertEqual([duty["date"] for duty in public["duties"]], sorted(duty["date"] for duty in public["duties"]))


if __name__ == "__main__":
    unittest.main()

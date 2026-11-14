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
        rows = duties.events(self.body, "2026-11-13")
        self.assertEqual(len(rows), len(duties.expanded(self.body, "2026-11-13")))
        first = next(row for row in rows if row["duty"] == "eu-first-declaration")
        self.assertEqual((first["date"], first["kind"], first["scheme"]), ("2027-09-30", "기한", "EU CBAM"))
        public = duties.public(self.body, "2026-11-13")
        self.assertTrue(all("evidence" not in duty and "covers" not in duty and "yearly" not in duty for duty in public["duties"]))
        self.assertEqual([duty["date"] for duty in public["duties"]], sorted(duty["date"] for duty in public["duties"]))
        self.assertEqual([role["key"] for role in public["roles"]], ["declarant", "operator", "verifier", "uk"])

    def test_yearly_duties_are_repeated_up_to_two_years_ahead(self):
        made = {duty["id"]: duty for duty in duties.expanded(self.body, "2026-11-13")}
        # 첫 일정은 그대로 두고, 이듬해부터 올해의 두 해 뒤까지 같은 날에 일정을 만든다
        self.assertEqual(sorted(key for key in made if key.startswith("eu-first-declaration")), ["eu-first-declaration", "eu-first-declaration-2028"])
        again = made["eu-first-declaration-2028"]
        self.assertEqual((again["date"], again["title"], again["repeat"]), ("2028-09-30", "2027년분 CBAM 신고서 제출과 인증서 제출", True))
        self.assertIn("2027년 수입분", again["text"])
        self.assertIn("2027년 수입분의 보고기간", again["supplier"])  # 그해에 맞춘 글: 보고기간은 기본으로 수입한 해다(산정 방법 이행규정 제7조)
        self.assertNotIn("covers", again)                           # 게시 데이터의 일정과 겹치는지는 첫 일정으로만 본다
        self.assertTrue(made["eu-first-declaration"]["repeat"])      # 원래 의무에도 해마다 돌아온다는 표시를 한다
        self.assertEqual(made["eu-verifier-plan-2027"]["text"], made["eu-verifier-plan"]["text"])   # 달리 적지 않은 글은 그대로 되풀이한다
        self.assertNotIn("repeat", made["eu-cancellation-2026"])
        # 해가 넘어가면 만드는 일정도 한 해 늘어난다
        self.assertIn("eu-verifier-plan-2029", {duty["id"] for duty in duties.expanded(self.body, "2027-01-02")})
        self.assertNotIn("eu-verifier-plan-2029", made)

    def test_a_yearly_duty_cannot_collide_or_fall_on_29_february(self):
        self.assertFalse(any("겹침" in what for _, what in duties.problems(self.body, kinds=("format",))))   # eu-cancellation-2026은 해마다 돌아오는 의무가 만드는 id가 아니다
        body = copy.deepcopy(self.body)
        clash = copy.deepcopy(next(row for row in body["duties"] if row["id"] == "eu-cancellation-2026"))
        clash["id"] = "eu-verifier-plan-2031"
        body["duties"].append(clash)
        self.assertIn(("의무 eu-verifier-plan-2031", "id가 해마다 돌아오는 의무 eu-verifier-plan가 만드는 일정의 id와 겹침"), duties.problems(body, kinds=("format",)))
        body = copy.deepcopy(self.body)
        next(row for row in body["duties"] if row["id"] == "eu-verifier-plan")["date"] = "2028-02-29"
        self.assertTrue(any("2월 29일" in what for where, what in duties.problems(body, kinds=("format",)) if where == "의무 eu-verifier-plan"))
        self.assertEqual([row["id"] for row in duties.expanded(body, "2026-11-13") if row["id"].startswith("eu-verifier-plan")], ["eu-verifier-plan"])   # 없는 날의 일정은 만들지 않는다

    def test_roles_and_yearly_texts_are_checked(self):
        body = copy.deepcopy(self.body)
        duty = next(row for row in body["duties"] if row["id"] == "eu-verifier-plan")
        duty["roles"] = ["verifier", "nobody"]
        duty["yearly"] = {"text": "해마다 통지한다.", "when": "x"}
        found = [what for where, what in duties.problems(body, kinds=("format",)) if "eu-verifier-plan" in where]
        self.assertTrue(any("모르는 역할" in what for what in found))
        self.assertTrue(any("yearly에는" in what for what in found))
        duty["yearly"] = {"text": "해마다 통지한다."}
        self.assertTrue(any("표기 규칙" in what for where, what in duties.problems(body, kinds=("format",)) if "yearly" in where))
        body["duties"][0].pop("roles")
        self.assertTrue(any("roles가 비었" in what for _, what in duties.problems(body, kinds=("format",))))


if __name__ == "__main__":
    unittest.main()

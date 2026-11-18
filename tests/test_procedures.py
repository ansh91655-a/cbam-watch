"""입법 절차의 자료(tools.publish.procedures): 실린 자료에 문제가 없는지, 근거와 꼴의 검사, 사이트에 실을 모양, 글 속 용어 풀이에 넘기는 용어."""
import copy
import unittest

from tools.common.jsonio import read_json
from tools.publish import gloss, procedures

STORED = "collected/archive/pages/eu-primary/tfeu-288.txt"


def body():
    return {
        "asOf": "2026-11-18", "lead": "표본입니다.",
        "sources": {"tfeu-288": {"text": "EU 기능조약 제288조", "url": "https://example.eu/288", "path": STORED, "read": "#law-x"},
                    "guide": {"text": "기관의 안내", "url": "https://example.eu/guide", "checkedOn": "2026-11-18"}},
        "institutions": [{"key": "commission", "name": "EU 집행위원회", "en": "European Commission", "role": "제안하는 기관입니다.",
                          "points": [{"text": "법안을 제안합니다.", "basis": [{"source": "guide"}]}]},
                         {"key": "council", "name": "EU 이사회", "en": "Council", "aka": "각료이사회", "role": "채택하는 기관입니다.",
                          "points": [{"text": "법을 채택합니다.", "basis": [{"source": "guide"}]}]}],
        "acts": [{"key": "regulation", "name": "규정", "en": "Regulation", "text": "모든 회원국에 적용됩니다.",
                  "basis": [{"source": "tfeu-288", "contains": ["A regulation shall have general application."]}]}],
        "codes": [{"code": "COM(2025) 1", "text": "제안 문서의 번호입니다.", "basis": [{"source": "guide"}]}],
        "kinds": [{"key": "cod", "name": "일반입법절차", "en": "Ordinary legislative procedure", "lanes": ["commission", "council"],
                   "lead": {"text": "두 기관이 함께 정합니다.", "basis": [{"source": "guide"}]},
                   "steps": [{"key": "proposal", "name": "제안", "part": "제안", "who": ["commission"], "text": "법안을 냅니다.", "basis": [{"source": "guide"}], "reach": 0},
                             {"key": "opinion", "name": "의견", "part": "제안", "who": [], "by": "자문기구", "optional": True, "track": "advisory", "text": "의견을 냅니다.", "basis": [{"source": "guide"}]},
                             {"key": "adoption", "name": "채택", "part": "채택", "who": ["council"], "text": "법을 채택합니다.", "basis": [{"source": "guide"}], "reach": 1}],
                   "notes": [{"title": "덧붙임", "text": "기한이 없습니다.", "basis": [{"source": "guide"}]}]}],
        "terms": [{"ko": "일반입법절차", "en": "ordinary legislative procedure", "also": ["통상입법절차"], "text": "두 기관이 함께 정하는 절차입니다.", "at": "cod"},
                  {"ko": "채택", "en": "adoption", "abbr": "ADP", "text": "법을 정하는 일입니다.", "at": "cod.adoption"}],
    }


class ProceduresTest(unittest.TestCase):
    def found(self, change):
        made = body()
        change(made)
        return [what for _, what in procedures.problems(made)]

    def test_the_published_data_is_clean(self):
        # 꼴과 표기만 본다. 근거로 적은 글이 받아 둔 글에 있는지는 사이트를 만들 때와 상태 점검이 본다(받아 둔 글은 날마다 다시 받으므로 여기에서 못박지 않는다)
        data = read_json(procedures.SOURCE)
        self.assertEqual(procedures.problems(data, kinds=("format",)), [])
        self.assertEqual(procedures.blocking(procedures.problems(data)), [])
        stored = [name for name, source in data["sources"].items() if "path" in source]
        self.assertGreater(len(stored), 30)                                            # 조약과 법령의 조문이 근거의 대부분이다
        self.assertEqual({kind["key"] for kind in data["kinds"]} & {"who", "acts", "board"}, set())

    def test_a_sound_body_passes(self):
        self.assertEqual(procedures.problems(body()), [])

    def test_every_text_needs_a_basis_that_names_a_listed_source(self):
        self.assertIn("근거(basis)가 없음", self.found(lambda made: made["acts"][0].pop("basis")))
        self.assertIn("없는 자료: nowhere", self.found(lambda made: made["kinds"][0]["steps"][0].update(basis=[{"source": "nowhere"}])))
        self.assertTrue(any("어느 글도 근거로 삼지 않는 자료" in what for what in self.found(lambda made: made["sources"].update(spare={"text": "남는 자료", "url": "https://example.eu/s", "checkedOn": "2026-11-18"}))))

    def test_stored_sources_are_matched_and_screen_sources_carry_a_date_instead(self):
        drift = self.found(lambda made: made["acts"][0]["basis"][0].update(contains=["이런 말은 조문에 없습니다"]))
        self.assertTrue(drift and drift[0].startswith(procedures.DRIFT))
        self.assertEqual(procedures.blocking([("법령의 종류 regulation", drift[0])]), [])          # 받아 둔 글이 달라진 것은 사이트 만들기를 멈추지 않는다
        self.assertIn("받아 둔 글(tfeu-288)에서 찾을 글(contains)이 없음", self.found(lambda made: made["acts"][0]["basis"][0].pop("contains")))
        self.assertIn("화면을 읽고 확인한 자료(guide)에는 찾을 글(contains)을 적지 않음", self.found(lambda made: made["codes"][0]["basis"][0].update(contains=["x"])))
        self.assertIn("받아 둔 글(path)과 확인한 날(checkedOn) 가운데 하나만 있어야 함", self.found(lambda made: made["sources"]["guide"].update(path=STORED)))
        self.assertIn("근거 파일이 모아 둔 자료가 아님", self.found(lambda made: made["sources"]["tfeu-288"].update(path="README.md")))
        # 근거만 볼 때에는 어긋난 것만 돌려준다
        made = body()
        made["acts"][0]["basis"][0]["contains"] = ["없는 말"]
        made["lead"] = ""
        self.assertEqual(len(procedures.problems(made, kinds=("evidence",))), 1)

    def test_steps_keep_their_shape(self):
        self.assertIn("하는 기관(who)이 기관의 이름이 아님", self.found(lambda made: made["kinds"][0]["steps"][0].update(who=["nobody"])))
        self.assertIn("줄(lanes)은 기관의 이름 둘 이상이어야 하고 겹치지 않아야 함", self.found(lambda made: made["kinds"][0].update(lanes=["commission"])))
        self.assertEqual(self.found(lambda made: made["kinds"][0].pop("lanes")), [])                 # 줄 그림이 없는 절차도 있다
        self.assertIn("이름(key)이 없거나 겹치거나 소문자·숫자·붙임표가 아님", self.found(lambda made: made["kinds"][0]["steps"][2].update(key="proposal")))
        self.assertIn("큰 단계의 번호(reach)가 수가 아니거나 앞 단계보다 작음", self.found(lambda made: made["kinds"][0]["steps"][2].update(reach=-1)))
        self.assertIn("같은 묶음(part)의 단계가 떨어져 있음", self.found(lambda made: made["kinds"][0]["steps"][1].update(part="딴 묶음") or made["kinds"][0]["steps"][2].update(part="제안")))
        self.assertTrue(any("who" in what for what in self.found(lambda made: made["kinds"][0].update(key="who"))))   # 화면의 자리 이름과 겹치는 절차 이름
        self.assertIn("표기 규칙(plain-ending: 다.)", self.found(lambda made: made["kinds"][0]["steps"][0].update(text="법안을 낸다.")))

    def test_terms_point_at_a_place_on_the_screen(self):
        self.assertEqual(procedures.anchors(body()), {"who", "acts", "who.commission", "who.council", "acts.regulation", "cod", "cod.proposal", "cod.opinion", "cod.adoption"})
        self.assertIn("없는 자리(at): cod.nothing", self.found(lambda made: made["terms"][1].update(at="cod.nothing")))
        self.assertIn("국문 표기(ko)나 영문 표기(en)가 없거나 겹침", self.found(lambda made: made["terms"][1].update(ko="일반입법절차")))

    def test_the_public_copy_drops_paths_and_keeps_only_cited_sources(self):
        made = body()
        made["sources"]["spare"] = {"text": "남는 자료", "url": "https://example.eu/s", "checkedOn": "2026-11-18"}
        out = procedures.public(made)
        self.assertEqual(out["sources"], {"guide": {"text": "기관의 안내", "url": "https://example.eu/guide", "checkedOn": "2026-11-18"},
                                          "tfeu-288": {"text": "EU 기능조약 제288조", "url": "https://example.eu/288", "read": "#law-x"}})
        self.assertNotIn("collected/archive", str(out))
        self.assertNotIn("shall have general application", str(out))
        self.assertEqual(out["acts"][0]["basis"], ["tfeu-288"])
        step = out["kinds"][0]["steps"][1]
        self.assertEqual((step["by"], step["optional"], step["track"], step["basis"]), ("자문기구", True, "advisory", ["guide"]))
        self.assertNotIn("reach", out["kinds"][0]["steps"][0])                                   # 큰 단계와의 맞춤은 검사에만 쓴다
        self.assertEqual(out["institutions"][1]["aka"], "각료이사회")
        self.assertNotIn("terms", out)                                                           # 용어는 글 속 용어 풀이의 자료로 간다

    def test_terms_reach_the_gloss_with_their_other_forms_and_a_link_to_this_screen(self):
        extra = procedures.gloss_terms(body())
        self.assertEqual(extra[0], {"ko": "일반입법절차", "en": "ordinary legislative procedure", "abbr": "", "also": ["통상입법절차"],
                                    "text": "두 기관이 함께 정하는 절차입니다.", "read": "#procedure-cod"})
        handbook = {"terms": [{"ko": "채택", "en": "adoption", "text": "해설서의 풀이입니다.", "chapter": "overview", "section": "what"}]}
        made, problems = gloss.build({"skipAbbr": [], "skipKo": []}, {"terms": []}, handbook, extra=extra)
        self.assertEqual(problems, [])
        by_ko = {term["ko"]: term for term in made["terms"]}
        self.assertEqual(by_ko["일반입법절차"]["forms"], ["일반입법절차", "통상입법절차"])
        self.assertEqual(by_ko["일반입법절차"]["read"], "#procedure-cod")
        self.assertEqual(by_ko["채택"]["read"], "#handbook-overview.what")                        # 해설서가 이미 풀이한 말은 해설서의 풀이를 둔다
        self.assertEqual(procedures.gloss_terms(None), [])


if __name__ == "__main__":
    unittest.main()

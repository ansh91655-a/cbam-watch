"""EU 집행위원회가 채택했으나 관보에 실리지 않은 하위 법령을 규제 자료에 '채택된 법령'의 모습으로 적는 일을 확인한다."""
import argparse
import unittest

from tools.publish import regulations, rule_adopt, rule_enact

LINK = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=PI_COM:C(2026)8367"


def body():
    draft = {"id": "draft", "group": "eu-upcoming", "name": "표본 판매·환매 위임규정(안)", "official": "의견수렴 14132 · Ares(2024)546926", "kind": "위임규정(안)",
             "path": ["준비", "초안 의견수렴", "채택·공포", "시행"], "at": 1, "stage": "채택 대기", "tone": "progress", "summary": "표본입니다.", "status": "채택을 기다리고 있습니다.",
             "timeline": [{"date": "2026-07-09", "text": "초안이 공개되었습니다.", "source": "EU 집행위원회", "link": "https://example.eu/consult", "basis": "web", "checkedOn": "2026-11-10"}],
             "links": [{"text": "EU 집행위원회 의견수렴 14132", "url": "https://example.eu/consult"}], "related": {"words": ["판매·환매"]}}
    return {"asOf": "2026-11-10", "groups": [{"code": "eu-upcoming", "name": "준비 중인 하위 법령", "about": "준비 중입니다."}, {"code": "eu-acts", "name": "시행 중인 하위 법령", "about": "시행 중입니다."}],
            "regulations": [draft]}


def ask(**given):
    return argparse.Namespace(**{"id": "draft", "reference": "C(2026) 8367 final", "link": LINK, "name": None, "kind": None, **given})


class Adopt(unittest.TestCase):
    def test_name_kind_official_and_link_show_the_adopted_act(self):
        data = body()
        rule_adopt.adopt(data, ask())
        made = data["regulations"][0]
        self.assertEqual((made["group"], made["name"], made["kind"]), ("eu-upcoming", "표본 판매·환매 위임규정", "위임규정(채택)"))
        self.assertEqual(made["official"], "C(2026) 8367 final · 의견수렴 14132 · Ares(2024)546926")
        self.assertEqual([link["url"] for link in made["links"]], [LINK, "https://example.eu/consult"])
        self.assertIn("관보 게재 전", made["links"][0]["text"])
        self.assertTrue(made["changedOn"])
        self.assertEqual([what for _, what in regulations.problems(data) if not what.startswith("근거")], [])

    def test_stage_and_timeline_are_left_for_other_commands(self):
        data = body()
        rule_adopt.adopt(data, ask())
        made = data["regulations"][0]
        self.assertEqual((made["at"], made["stage"], len(made["timeline"])), (1, "채택 대기", 1))

    def test_refuses_twice_and_bad_input(self):
        data = body()
        rule_adopt.adopt(data, ask())
        for bad in (ask(), ask(reference=" "), ask(link="http://example.eu/x"), ask(id="none")):
            with self.assertRaises(SystemExit):
                rule_adopt.adopt(data, bad)

    def test_enact_takes_the_adopted_mark_off(self):
        data = body()
        rule_adopt.adopt(data, ask())
        rule_enact.enact(data, argparse.Namespace(id="draft", celex="32027R0100", name=None, kind=None, after=None))
        made = data["regulations"][0]
        self.assertEqual((made["group"], made["kind"], made["official"]), ("eu-acts", "위임규정", "Delegated Regulation (EU) 2027/100"))
        self.assertEqual(made["links"][0]["url"], "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32027R0100")


if __name__ == "__main__":
    unittest.main()

"""같은 문장은 같은 번역으로(tools/laws/alike.py)."""
import unittest

from tools.laws import alike, store


def doc(act_id, group, *blocks):
    return ({"id": act_id, "group": group}, [{"id": "p1", "kind": "article", "label": "Article 1", "title": "", "blocks": list(blocks)}])


def memory(*pairs):
    return {store.key(source): korean for source, korean in pairs}


LAW = "(30) ‘installation’ means a stationary technical unit where a production process is carried out;"
GUIDE = "• ‘installation’ means a stationary technical unit where a production process is carried out."
NOTE_A = "Emission factors are taken from the data set[88] chosen by the operator for that purpose."
NOTE_B = "Emission factors are taken from the data set[19] chosen by the operator for that purpose."
NOTE_C = "Emission factors are taken from the data set chosen by the operator for that purpose."


class ShapeTest(unittest.TestCase):
    def test_a_text_is_cut_into_lead_body_and_tail(self):
        self.assertEqual(alike.shape("(30) ‘사업장’이란 고정된 기술 단위를 말한다."), ("(30) ", "‘사업장’이란 고정된 기술 단위를 말한다", "."))
        self.assertEqual(alike.shape("• (a) First;"), ("• (a) ", "First", ";"))
        self.assertEqual(alike.shape("No lead and no tail"), ("", "No lead and no tail", ""))
        self.assertEqual("".join(alike.shape("1. Whole text,")), "1. Whole text,")

    def test_the_same_sentence_has_one_key_whatever_its_number_marks_and_ending(self):
        self.assertEqual(alike.norm(LAW), alike.norm(GUIDE))
        self.assertEqual(alike.norm(NOTE_A), alike.norm(NOTE_B))
        self.assertEqual(alike.norm(NOTE_A), alike.norm(NOTE_C))
        self.assertNotEqual(alike.norm(LAW), alike.norm(LAW.replace("stationary", "mobile")))
        # 영문 병기만 다른 번역은 같은 번역으로 본다
        self.assertEqual(alike.kind("(a) 사업장(installation)의 배출량."), alike.kind("• 사업장의 배출량"))


class GroupsTest(unittest.TestCase):
    def test_the_translation_used_in_the_law_is_the_base(self):
        documents = [doc("guide-1", "guide", GUIDE), doc("guide-2", "guide", GUIDE.replace("• ", "- ")), doc("32023R0956", "act", LAW)]
        known = memory((GUIDE, "• ‘사업장’은 생산공정이 수행되는 고정된 기술 단위를 말한다."), (GUIDE.replace("• ", "- "), "- ‘사업장’은 생산공정이 수행되는 고정된 기술 단위를 말한다."),
                       (LAW, "(30) ‘사업장’이란 생산공정이 수행되는 고정된 기술 단위를 말한다;"))
        found = alike.groups(documents, known, {})
        self.assertEqual((len(found), found[0]["base"]["act"]), (1, "32023R0956"))   # 둘이 쓰는 번역보다 법령의 번역이 먼저다
        changes, stuck, count = alike.plan(documents, known, {})
        self.assertEqual((count, stuck), (1, []))
        # 앞의 글머리표와 끝의 문장부호는 그 문단의 것을 지킨다(원문의 끝이 다르다: 쌍반점과 마침표)
        self.assertEqual(changes, {store.key(GUIDE): "• ‘사업장’이란 생산공정이 수행되는 고정된 기술 단위를 말한다.",
                                   store.key(GUIDE.replace("• ", "- ")): "- ‘사업장’이란 생산공정이 수행되는 고정된 기술 단위를 말한다."})

    def test_without_a_law_the_most_used_translation_is_the_base(self):
        documents = [doc("guide-1", "guide", NOTE_A), doc("guide-2", "guide", NOTE_B), doc("guide-3", "guide", NOTE_B)]   # 둘째 번역은 두 자리에서 쓰인다
        known = memory((NOTE_A, "배출계수는 사업자가 그 목적으로 고른 데이터 세트[88]에서 가져온다."), (NOTE_B, "배출계수는 사업자가 그 목적을 위하여 선택한 데이터 세트[19]에서 취한다."))
        changes, stuck, count = alike.plan(documents, known, {})
        self.assertEqual((count, stuck), (1, []))
        self.assertEqual(changes, {store.key(NOTE_A): "배출계수는 사업자가 그 목적을 위하여 선택한 데이터 세트[88]에서 취한다."})   # 각주 번호는 그 문단의 것으로 바꾼다

    def test_translations_that_cannot_be_matched_safely_are_left_and_reported(self):
        documents = [doc("32023R0956", "act", NOTE_A), doc("guide-2", "guide", NOTE_C)]
        known = memory((NOTE_A, "배출계수는 사업자가 그 목적을 위하여 선택한 데이터 세트[88]에서 취한다."), (NOTE_C, "배출계수는 사업자가 고른 데이터 세트에서 가져온다."))
        changes, stuck, count = alike.plan(documents, known, {})
        self.assertEqual((changes, count), ({}, 1))
        self.assertEqual(stuck, [(store.key(NOTE_C), "각주 번호를 짝지을 수 없음")])   # 각주가 있는 문장과 없는 문장

    def test_short_texts_and_single_translations_are_not_grouped(self):
        documents = [doc("guide-1", "guide", "(a) Source", "Source;", LAW), doc("guide-2", "guide", LAW)]
        known = memory(("(a) Source", "(a) 출처"), ("Source;", "배출원;"), (LAW, "(30) 번역"))
        self.assertEqual(alike.groups(documents, known, {}), [])
        self.assertEqual(alike.summary(documents, known, {}), "")

    def test_the_summary_counts_groups_and_changes(self):
        documents = [doc("guide-1", "guide", NOTE_A), doc("guide-2", "guide", NOTE_B)]
        known = memory((NOTE_A, "배출계수는 사업자가 고른 데이터 세트[88]에서 가져온다."), (NOTE_B, "배출계수는 사업자가 선택한 데이터 세트[19]에서 취한다."))
        self.assertEqual(alike.summary(documents, known, {}), "같은 문장의 번역: 묶음 1개가 서로 다름(맞출 수 있는 문단 1개, 맞추지 못하는 문단 0개)")

    def test_a_base_picked_by_a_reviewer_comes_first_and_skipped_groups_are_left(self):
        documents = [doc("guide-1", "guide", NOTE_A), doc("guide-2", "guide", NOTE_B)]
        known = memory((NOTE_A, "배출계수는 사업자가 고른 데이터 세트[88]에서 가져온다."), (NOTE_B, "배출계수는 사업자가 선택한 데이터 세트[19]에서 취한다."))
        same = alike.norm(NOTE_A)
        changes, _, _ = alike.plan(documents, known, {"pick": {same: store.key(NOTE_B)}})
        self.assertEqual(changes, {store.key(NOTE_A): "배출계수는 사업자가 선택한 데이터 세트[88]에서 취한다."})   # 고르지 않았다면 먼저 나온 것이 바탕이다
        self.assertEqual(alike.plan(documents, known, {"skip": [same]}), ({}, [], 0))
        self.assertEqual(alike.plan(documents, known, {"pick": {same: "없는 열쇠"}})[0], {store.key(NOTE_B): "배출계수는 사업자가 고른 데이터 세트[19]에서 가져온다."})


if __name__ == "__main__":
    unittest.main()

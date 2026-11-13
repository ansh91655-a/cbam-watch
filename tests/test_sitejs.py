"""화면 모듈 가운데 화면 요소를 다루지 않아 브라우저 없이 볼 수 있는 것: 국내 공지·자료 가르기(js/news/notices.js),
문단 인용의 글(js/laws/cite.js), 낱말 단위로 달라진 곳 찾기(js/laws/worddiff.js), 의무를 역할로 고르기(js/calendar/roles.js),
규정 원문과 그것을 적은 글을 잇는 주소(js/laws/refs.js), 부문별 모아 보기의 글(js/sector/facts.js)."""
import json
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { forRole, roleIn, roleTarget, tally } from './site/js/calendar/roles.js';
import { address, citeBlock, citePart, partName, source } from './site/js/laws/cite.js';
import { dutyHref, lawHref, linkedTo, tally as linkedTally, termHref } from './site/js/laws/refs.js';
import { wordDiff } from './site/js/laws/worddiff.js';
import { isNotice, NOTICES, split } from './site/js/news/notices.js';
import { gasText, markupText, proposedText, scopeOf, scopeText, upcoming } from './site/js/sector/facts.js';

const act = { id: '32023R0956', group: 'act', name: 'CBAM 규정', official: 'Regulation (EU) 2023/956', consolidated: '2025-10-20' };
const article = { id: 'art-6', kind: 'article', label: 'Article 6', ko: '제6조', title: 'CBAM declaration', titleKo: 'CBAM 신고',
  blocks: [['1. By 30 September of each year …', '1. 매년 9월 30일까지 …'], ['2. Not yet translated', ''], ['(12)', '(12)']] };
const guide = { id: 'guide-3', group: 'guide', name: '가이던스 3: 제품의 내재배출량 산정 방법', official: 'Guidance document 3', received: '2026-11-10' };
const section = { id: 'sec-4-3-1', kind: 'section', label: '4.3.1', ko: '4.3.1', title: 'Definitive Period rules', titleKo: '확정기간 규칙', page: 37, pages: [37, 38],
  blocks: [['First.', '첫째.'], ['Second.', '둘째.']] };
const base = 'https://example.org/cbam-watch/#law-old';

const items = [
  { id: 'a', title: '설명회 안내', brief: true },
  { id: 'b', title: '요약이 있는 소식', summary: '요약입니다.' },
  { id: 'c', title: '내린 한 줄 소식', brief: true, withdrawn: true },
  { id: 'd', title: '자료실의 자료', brief: true },
];
const parts = split(items);

const roles = [{ key: 'declarant', name: '신고인·수입자' }, { key: 'verifier', name: '검증기관' }, { key: 'uk', name: '영국 수입자' }];
const duties = [{ id: 'one', roles: ['declarant'] }, { id: 'two', roles: ['declarant', 'verifier'] }, { id: 'three' }];

const linkedRefs = { laws: { '32023R0956': {
  'art-6': { items: [], duties: [{ id: 'eu-first-declaration', title: '첫 신고', date: '2027-09-30' }], terms: [{ en: 'CBAM declaration', ko: 'CBAM 신고서' }, { en: 'CBAM obligation', ko: 'CBAM 의무' }], more: 0 },
  'art-7': { items: [], duties: [], terms: [], more: 0 },
  '': { items: [{ id: 'a', title: '소식', date: '2026-11-12' }], more: 4 },
} } };

const long = (word) => Array.from({ length: 900 }, (_, index) => `${word}${index}`).join(' ');

console.log(JSON.stringify({
  diff: {
    date: wordDiff('1. By 31 May of each year, each declarant shall submit.', '1. By 30 September of each year, each declarant shall submit.'),
    grown: wordDiff('shall not apply to:', 'shall not apply to goods used in military activities.'),
    korean: wordDiff('매년 5월 31일까지 신고서를 제출하여야 한다.', '매년 9월 30일까지 신고서를 제출하여야 한다.'),
    same: wordDiff('No change  here.', 'No change  here.'),
    empty: wordDiff('', 'New text.'),
    heavy: wordDiff(long('a'), long('b')).skipped,
    joined: ['old', 'new'].map((side) => wordDiff('  Leading space and a tail ', 'Leading  space and another tail')[side].map(([text]) => text).join('')),
  },
  cite: {
    block: citeBlock(act, article, 0, base).split('\n'), waiting: citeBlock(act, article, 1, base).split('\n'), same: citeBlock(act, article, 2, base).split('\n'),
    paged: citeBlock(guide, section, 1, base).split('\n'), part: citePart(act, article, base).split('\n'), partPaged: citePart(guide, section, base).split('\n'),
    partCut: citePart(act, { ...article, id: 'annex-i', kind: 'annex', ko: '부속서 I', cut: 300 }, base).split('\n').slice(-1)[0],
    names: [partName(article), partName(section), partName({ kind: 'recitals', ko: '전문' }), partName(null)],
    sources: [source(act, article, 0), source({ ...act, consolidated: '' }, article, 0), source(guide, section, 0)],
    links: [address(base, act, article), address('https://example.org/x/', guide, section, 2)],
  },
  sector: {
    gases: [gasText(['co2', 'pfc']), gasText(['co2', 'xx']), gasText(null)],
    scope: [scopeText({ directOnly: 14, both: 1 }), scopeText({ directOnly: 3, both: 0 }), scopeText({ directOnly: 0, both: 5 }), scopeText({}), scopeOf({ directOnly: true }), scopeOf({})],
    markups: [markupText({ 2026: 10, 2027: 20, 2028: 30 }), markupText({ 2026: 1 }), markupText(null)],
    next: upcoming([{ id: 'late', date: '2027-09-30', scheme: 'eu' }, { id: 'past', date: '2026-03-31', scheme: 'eu' }, { id: 'uk', date: '2027-01-01', scheme: 'uk' },
      { id: 'soon', date: '2026-11-15', scheme: 'eu' }, { id: 'today', date: '2026-11-13', scheme: 'eu' }, { id: 'far', date: '2028-01-01', scheme: 'eu' }], '2026-11-13', 3, 'eu').map((duty) => duty.id),
    proposed: [proposedText('철강', { own: 22, combined: 107 }), proposedText('알루미늄', { own: 0, combined: 107 }), proposedText('시멘트', null), proposedText('시멘트', { own: 0, combined: 0 })],
  },
  refs: {
    hrefs: [lawHref({ act: '32023R0956', part: 'art-6' }), lawHref({ act: '32025R2621', part: '' }), dutyHref({ id: 'eu-first-declaration', date: '2027-09-30' }), termHref({ en: 'CBAM declaration', ko: 'CBAM 신고서' })],
    linked: linkedTo(linkedRefs, '32023R0956', 'art-6'), whole: linkedTo(linkedRefs, '32023R0956'), none: [linkedTo(linkedRefs, '32023R0956', 'art-7'), linkedTo(linkedRefs, 'nobody', 'art-1'), linkedTo(null, 'x')],
    tally: [linkedTally(linkedTo(linkedRefs, '32023R0956', 'art-6')), linkedTally(linkedTo(linkedRefs, '32023R0956')), linkedTally(null)],
  },
  roles: {
    read: [roleIn('role-verifier', roles), roleIn('role-nobody', roles), roleIn('duty-one', roles), roleIn('', roles), roleIn('role-verifier', null)],
    targets: [roleTarget('verifier'), roleTarget('')],
    picked: forRole(duties, 'verifier').map((duty) => duty.id), all: forRole(duties, '').map((duty) => duty.id), none: forRole(null, 'verifier'),
    tally: tally(duties, roles).map((role) => [role.key, role.name, role.size]),
  },
  notices: { name: NOTICES, ids: parts.notices.map((item) => item.id), news: parts.news.map((item) => item.id), empty: split(null), one: isNotice(null) },
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면 모듈은 시험하지 않는다")
class SiteModulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_title_only_notices_are_set_apart_from_the_news(self):
        notices = self.seen["notices"]
        self.assertEqual(notices["name"], "notices")
        self.assertEqual(notices["ids"], ["a", "d"])          # 차례는 그대로다
        self.assertEqual(notices["news"], ["b", "c"])         # 요약을 내린 것은 보통 소식으로 둔다(내렸다는 알림이 보여야 한다)
        self.assertEqual(notices["empty"], {"news": [], "notices": []})
        self.assertFalse(notices["one"])

    def test_sector_facts_are_worded_from_the_data(self):
        sector = self.seen["sector"]
        self.assertEqual(sector["gases"], ["이산화탄소, 과불화탄소", "이산화탄소, xx", ""])
        self.assertEqual(sector["scope"], ["직접배출만 14줄, 직접배출과 간접배출 1줄", "직접배출만(부속서 II)", "직접배출과 간접배출", "", "직접배출만", "직접배출과 간접배출"])
        self.assertEqual(sector["markups"], ["2026년 10%, 2027년 20%, 2028년부터 30%", "2026년부터 1%", ""])   # 마지막 값은 그 뒤의 해에도 쓴다
        self.assertEqual(sector["next"], ["today", "soon", "late"])                                          # 오늘부터, 그 제도의 것만, 날짜 차례로
        self.assertTrue(sector["proposed"][0].startswith("철강 품목 22줄과 복합 금속 제품 107줄을 더하려는 개정안이 심의 중입니다."))
        self.assertTrue(sector["proposed"][1].startswith("복합 금속 제품 107줄을 더하려는"))
        self.assertEqual(sector["proposed"][2:], ["", ""])

    def test_links_between_the_law_text_and_what_cites_it(self):
        refs = self.seen["refs"]
        self.assertEqual(refs["hrefs"], ["#law-32023R0956.art-6", "#law-32025R2621", "#calendar-2027.duty-eu-first-declaration", "#terms-CBAM%20declaration"])
        self.assertEqual((len(refs["linked"]["duties"]), len(refs["linked"]["terms"]), refs["linked"]["items"]), (1, 2, []))
        self.assertEqual((refs["whole"]["duties"], refs["whole"]["terms"], refs["whole"]["more"]), ([], [], 4))   # 빠진 갈래는 빈 목록으로 채운다
        self.assertEqual(refs["none"], [None, None, None])                                                          # 이어진 것이 없으면 그리지 않는다
        self.assertEqual(refs["tally"], ["의무 일정 1건, 용어 2건", "소식 5건", ""])                                 # 다 싣지 못한 소식도 센다

    def test_duties_are_picked_by_the_role_named_in_the_address(self):
        roles = self.seen["roles"]
        # 주소의 role-<역할>만 역할로 읽는다. 목록에 없는 역할이나 일정의 번호(duty-…)는 역할이 아니다
        self.assertEqual(roles["read"], ["verifier", "", "", "", ""])
        self.assertEqual(roles["targets"], ["role-verifier", ""])
        self.assertEqual(roles["picked"], ["two"])
        self.assertEqual(roles["all"], ["one", "two", "three"])   # 역할을 고르지 않으면 역할이 적히지 않은 의무도 보인다
        self.assertEqual(roles["none"], [])
        # 그해에 의무가 하나도 없는 역할(영국 수입자)은 고를 것으로 내놓지 않는다
        self.assertEqual(roles["tally"], [["declarant", "신고인·수입자", 2], ["verifier", "검증기관", 1]])

    def test_a_cited_paragraph_carries_the_text_the_source_and_the_address(self):
        cite = self.seen["cite"]
        self.assertEqual(cite["block"], [
            "[원문] 1. By 30 September of each year …",
            "[국문] 1. 매년 9월 30일까지 …",
            "[출처] CBAM 규정 제6조 CBAM 신고 (Regulation (EU) 2023/956, 2025-10-20 통합본)",
            "[주소] https://example.org/cbam-watch/#law-32023R0956.art-6.1",
            "※ 국문은 CBAM 규제동향이 옮긴 비공식 번역입니다.",
        ])
        # 아직 옮기지 않은 문단과, 옮길 글이 없어 원문 그대로인 줄(수와 기호)에는 국문 줄과 번역 알림이 없다
        self.assertEqual([line[:4] for line in cite["waiting"]], ["[원문]", "[출처]", "[주소]"])
        self.assertEqual([line[:4] for line in cite["same"]], ["[원문]", "[출처]", "[주소]"])
        self.assertTrue(cite["waiting"][-1].endswith("#law-32023R0956.art-6.2"))
        # 안내 문서는 그 문단이 있는 PDF의 쪽과 받은 판을 적는다
        self.assertEqual(cite["paged"][2], "[출처] 가이던스 3: 제품의 내재배출량 산정 방법 4.3.1 확정기간 규칙, PDF 38쪽 (Guidance document 3, EU 집행위원회, 2026-11-10에 받은 판)")
        self.assertEqual(cite["paged"][3], "[주소] https://example.org/cbam-watch/#law-guide-3.sec-4-3-1.2")

    def test_a_cited_part_lists_the_whole_text_then_the_translation(self):
        cite = self.seen["cite"]
        self.assertEqual(cite["part"][:2], ["제6조 CBAM 신고", "Article 6 CBAM declaration"])
        at = {label: cite["part"].index(label) for label in ("[원문]", "[국문]")}
        self.assertEqual(cite["part"][at["[원문]"] + 1:at["[원문]"] + 4], ["1. By 30 September of each year …", "2. Not yet translated", "(12)"])
        self.assertEqual(cite["part"][at["[국문]"] + 1:at["[국문]"] + 4], ["1. 매년 9월 30일까지 …", "2. Not yet translated", "(12)"])  # 옮기지 않은 문단은 원문을 그 자리에 둔다
        self.assertEqual(cite["part"][-2], "[주소] https://example.org/cbam-watch/#law-32023R0956.art-6")
        self.assertIn("PDF 37쪽", cite["partPaged"][-3])       # 조각을 통째로 인용하면 조각이 시작하는 쪽을 적는다
        self.assertIn("앞부분만 실려 있습니다", cite["partCut"])  # 뒷부분을 싣지 않은 부속서를 통째로 인용하면 전부가 아님을 밝힌다
        self.assertEqual(cite["names"], ["제6조 CBAM 신고", "4.3.1 확정기간 규칙", "전문", ""])
        self.assertEqual(cite["sources"][1], "CBAM 규정 제6조 CBAM 신고 (Regulation (EU) 2023/956)")
        self.assertEqual(cite["links"], ["https://example.org/cbam-watch/#law-32023R0956.art-6", "https://example.org/x/#law-guide-3.sec-4-3-1.2"])

    def test_changed_words_are_marked_on_both_sides(self):
        diff = self.seen["diff"]
        self.assertEqual(diff["date"]["old"], [["1. By ", False], ["31 May", True], [" of each year, each declarant shall submit.", False]])
        self.assertEqual(diff["date"]["new"], [["1. By ", False], ["30 September", True], [" of each year, each declarant shall submit.", False]])
        # 뒤에 말이 붙은 문단: 옛 글에서는 바뀐 낱말 하나만, 새 글에서는 붙은 말이 한 조각으로 표시된다
        self.assertEqual(diff["grown"]["old"], [["shall not apply ", False], ["to:", True]])
        self.assertEqual(diff["grown"]["new"], [["shall not apply ", False], ["to goods used in military activities.", True]])
        self.assertEqual(diff["korean"]["new"], [["매년 ", False], ["9월 30일까지", True], [" 신고서를 제출하여야 한다.", False]])
        self.assertEqual(diff["same"], {"old": [["No change  here.", False]], "new": [["No change  here.", False]], "skipped": False})

    def test_the_pieces_always_join_back_into_the_text(self):
        diff = self.seen["diff"]
        self.assertEqual(diff["joined"], ["  Leading space and a tail ", "Leading  space and another tail"])   # 띄어쓰기도 그대로 남는다
        self.assertEqual(diff["empty"], {"old": [], "new": [["New text.", False]], "skipped": False})          # 견줄 짝이 없으면 표시하지 않는다
        self.assertTrue(diff["heavy"])                                                                        # 너무 긴 글은 견주지 않고 그대로 보여 준다


if __name__ == "__main__":
    unittest.main()

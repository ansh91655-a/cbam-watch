"""화면 모듈 가운데 화면 요소를 다루지 않아 브라우저 없이 볼 수 있는 것: 국내 공지·자료 가르기(js/news/notices.js), 번역이 준비된 정도(js/laws/ready.js),
문단 인용의 글(js/laws/cite.js), 낱말 단위로 달라진 곳 찾기(js/laws/worddiff.js), 의무를 역할로 고르기(js/calendar/roles.js),
규정 원문과 그것을 적은 글을 잇는 주소(js/laws/refs.js), 부문별 모아 보기의 글(js/sector/facts.js), 최근 소식 가리기(js/news/recent.js),
해설서 그림의 글(식 한 줄을 칸과 기호로 나누기 js/views/handbook/figures/equation.js, 날짜 적기 js/views/handbook/figures/timeline.js),
품목 한 장 보기의 셈(js/cn/sheet.js), 글 속 용어 풀이의 찾기(js/gloss/match.js)."""
import json
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { readFileSync } from 'node:fs';
import { unpack } from './site/js/calc/compute.js';
import { forRole, roleIn, roleTarget, tally } from './site/js/calendar/roles.js';
import { benchmarks, flagsOf, goodsUnder, line, LIST_LIMIT, markedUp, nearest, sectorOf, sheetYear, shown, splitByPeriod, yearly } from './site/js/cn/sheet.js';
import { address, citeBlock, citePart, partName, source } from './site/js/laws/cite.js';
import { translation, waitLabel } from './site/js/laws/ready.js';
import { dutyHref, lawHref, linkedTo, tally as linkedTally, termHref } from './site/js/laws/refs.js';
import { wordDiff } from './site/js/laws/worddiff.js';
import { compile, find } from './site/js/gloss/match.js';
import { isNotice, NOTICES, split } from './site/js/news/notices.js';
import { PERIODS, RECENT, RECENT_DAYS, within } from './site/js/news/recent.js';
import { gasText, markupText, proposedText, scopeOf, scopeText, upcoming } from './site/js/sector/facts.js';
import { tokens } from './site/js/views/handbook/figures/equation.js';
import { whenText } from './site/js/views/handbook/figures/timeline.js';

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

// 품목 한 장 보기: 비용 추정의 자료를 짧은 꼴로 지어 셈을 본다(열연 코일 한 품목, 세부 품목이 둘인 클링커, 연도 구간에 따라 값이 다른 합금강)
const sheetBook = unpack({
  years: { from: 2026, to: 2034 }, periods: [{ key: 1, from: 2026, to: 2027 }, { key: 2, from: 2028, to: 2030 }],
  markups: [{ sectors: ['cement', 'steel'], values: { 2026: 10, 2027: 20, 2028: 30 } }], cscf: { 2026: 100, 2027: 100, 2028: 100, 2029: 100, 2030: 100 },
  routes: [{ key: 'A', name: '회색 클링커·시멘트' }, { key: 'B', name: '백색 클링커·시멘트' }, { key: 'C', name: '탄소강, 고로·전로' }, { key: 'D', name: '탄소강, 직접환원철·전기로' }, { key: 'F', name: '저합금강, 고로·전로' }, { key: 'J', name: '고합금강(전기로)' }],
  rows: [['7208', 'Flat-rolled, hot-rolled', 'kr', 2.118, null, 2.118], ['2523100010', 'White clinker', 'kr', 1.19, 0.04, 1.23], ['2523100090', 'Other clinker', 'kr', 0.88, 0.03, 0.92], ['7224', 'Other alloy steel', 'other', 2.0, null, 2.0]],
  goods: [
    ['25231000', 'Cement clinkers', 'cement', [[0.666, 'A', 0], [0.859, 'B', 0]], [[0.666, 'A', 0], [0.859, 'B', 0]], [[1, 'B', 0.859, 0.859], [2, 'A', 0.666, 0.666]]],
    ['72081000', 'Flat-rolled, in coils, with patterns', 'steel', [[0.044, '', 0]], [[1.37, 'C', 0], [0.481, 'D', 0]], [[0, 'C', 1.37, 1.37]]],
    ['72082500', 'Flat-rolled, in coils, pickled', 'steel', [[0.044, '', 0]], [[1.37, 'C', 0], [0.481, 'D', 0]], [[0, 'C', 1.37, 1.37]]],
    ['72241010', 'Ingots of tool steel', 'steel', [[0.2, '', 1], [0.1, '', 2]], [[1.807, 'F', 1], [1.18, 'J', 1], [1.64, 'F', 2], [1.148, 'J', 2]], [[3, 'F', 1.807, 1.64]]],
  ],
});
const sheetPath = { key: 'current', name: '현행 지침', values: { 2026: 97.5, 2027: 95, 2028: 90, 2029: 77.5, 2030: 51.5, 2031: 39, 2032: 26.5, 2033: 14, 2034: 0 } };
const coil = sheetBook.goods.find((good) => good.code === '72081000');
const clinker = sheetBook.goods.find((good) => good.code === '25231000');
const tool = sheetBook.goods.find((good) => good.code === '72241010');
const sheetRows = [{ about: '늘', when: '' }, { about: '직접', when: 'direct' }, { about: '둘 다', when: 'both' }, { about: '값 있음', when: 'priced' }, { about: '값 없음', when: 'unpriced' }];
const round = (value) => Math.round(value * 1000) / 1000;

// 글 속 용어 풀이: 찾은 자리를 [찾은 글, 용어의 국문 표기]로 적는다
const glossTerms = [{ forms: ['부문 간 보정계수', 'CSCF'], ko: '부문 간 보정계수' }, { forms: ['EU 배출권거래제', 'EU ETS'], ko: 'EU 배출권거래제' }, { forms: ['ETS'], ko: '배출권거래제' },
  { forms: ['탄소가격'], ko: '탄소가격' }, { forms: ['기본 탄소가격'], ko: '기본 탄소가격' }, { forms: ['SEE'], ko: '고유 내재배출량' }, { forms: ['EUA'], ko: 'EU 배출권' },
  { forms: ['CCS', 'CCU', 'CCUS'], ko: '탄소 포집·저장' }, { forms: ['RED II'], ko: '재생에너지 지침' }];
const glossBook = compile(glossTerms);
const marked = (text, seen, skip) => find(text, glossBook, seen, skip).map((hit) => [text.slice(hit.start, hit.end), glossTerms[hit.at].ko]);

// 해설서에 실린 식: 풀이가 달린 말은 식 한 줄에서 칸 하나로 나뉘어야 한다(그래야 그 말이 칸으로 그려진다)
const formulas = JSON.parse(readFileSync('./data/handbook.json', 'utf8')).chapters.flatMap((chapter) => chapter.sections).map((one) => one.formula).filter(Boolean);
const drawn = (formula) => tokens(formula.text).filter(([kind]) => kind === 'term').map(([, word]) => word);

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
  ready: { states: [{ blocks: 10, done: 10 }, { blocks: 10, done: 4 }, { blocks: 10, done: 0 }, { blocks: 0, done: 0 }, null, { blocks: 3, done: 5 }].map(translation),
    labels: [{ blocks: 10, done: 10 }, { blocks: 10, done: 4 }, { blocks: 10, done: 0 }].map(waitLabel) },
  notices: { name: NOTICES, ids: parts.notices.map((item) => item.id), news: parts.news.map((item) => item.id), empty: split(null), one: isNotice(null) },
  sheet: {
    under: [['7208', 2], ['720810', 1], ['7208100090', 1], ['72', 0], ['720', 0], ['', 0], ['7318', 0]].map(([query, size]) => goodsUnder(sheetBook.goods, query).length === size),
    near: [nearest(sheetBook.goods, '72081510'), nearest(sheetBook.goods, '72089900'), nearest(sheetBook.goods, '73181510'), nearest(sheetBook.goods, '7208')],
    years: [2026, 2019, 2040, 0].map((year) => sheetYear(sheetBook, year)), limit: LIST_LIMIT,
    coil: (({ code, value, markup, embedded, benchmark, factor, cscf, allocation, perTonne, costPerTonne, route, routeAlt, more, year }) =>
      ({ code, value, markup, embedded: round(embedded), benchmark, factor, cscf, allocation: round(allocation), perTonne: round(perTonne), cost: round(costPerTonne), route, routeAlt, more, year }))(line(sheetBook, sheetPath, coil, 2026, 80)),
    clinker: [0, 1].map((choice) => { const one = line(sheetBook, sheetPath, clinker, 2026, 80, choice); return [one.row.text, one.route, round(one.embedded), round(one.perTonne), one.more]; }),
    tool: (({ route, routeAlt, benchmark }) => ({ route, routeAlt, benchmark }))(line(sheetBook, sheetPath, tool, 2028, 80)),
    none: line(sheetBook, { values: {} }, coil, 2026, 80),
    yearly: yearly(sheetBook, sheetPath, coil, 80).map((row) => [row.year, round(row.perTonne), round(row.costPerTonne), row.assumed, row.updated]),
    marked: markedUp(sheetBook, 'steel', 2.118).map((cell) => [cell.year, cell.rate, round(cell.value), cell.onward]), unmarked: markedUp(sheetBook, 'hydrogen', 14.03),
    benchmarks: { coil: benchmarks(sheetBook, coil), clinker: benchmarks(sheetBook, clinker).map((row) => [row.route, row.name, row.a, row.b]), tool: benchmarks(sheetBook, tool).map((row) => [row.route, row.a, row.b]) },
    split: [coil, clinker, tool].map((good) => splitByPeriod(benchmarks(sheetBook, good))),
    flags: [flagsOf([{ directOnly: true }], true, true), flagsOf([{ directOnly: false }, { directOnly: true }], false, true), flagsOf([{ directOnly: true }], false, false), flagsOf([], false, false)],
    shown: [flagsOf([{ directOnly: true }], true, true), flagsOf([{ directOnly: false }], false, false)].map((flags) => shown(sheetRows, flags).map((row) => row.about)), empty: shown(null, {}),
    sector: [sectorOf([{ key: 'steel', cn: ['steel'] }, { key: 'hydrogen', cn: ['chemicals'] }], [{ sector: 'chemicals' }]).key, sectorOf([{ key: 'steel', cn: ['steel'] }], [{ sector: 'combined' }]), sectorOf(null, [])],
  },
  gloss: {
    spacing: marked('부문간 보정계수(CSCF)는 해마다 정합니다.'),
    longest: [marked('EU ETS의 배출권과 다른 나라의 ETS'), marked('기본 탄소가격은 탄소가격과 다릅니다.')],
    whole: [marked('markets and assets, see Article 5; SEEs'), marked('SEE는 제품 1톤당 값입니다. ETS2는 따로입니다.')],
    plural: marked('EUAs를 삽니다. CCUS와 CCS는 다릅니다. RED II와 RED III'),
    once: (() => { const seen = new Set(); return [marked('탄소가격을 냅니다.', seen), marked('탄소가격을 또 냅니다. CSCF도 있습니다.', seen)]; })(),
    skipped: marked('CSCF와 탄소가격', new Set(), (term) => term.ko === '탄소가격'),
    empty: [find('CSCF', compile([])), find('', glossBook), find('CSCF', null), compile(null).rows],
  },
  figures: {
    tokens: tokens('인증서 수 = (내재배출량 − 무상할당량) × 수입량'), plain: tokens('CO2e 1톤'), none: tokens(''),
    when: [{ date: '2027-02-01', edge: '부터' }, { date: '2027-11-01' }, { when: '2027년 각 분기 말' }, { when: '2026년', edge: '부터' }, {}].map(whenText),
    formulas: formulas.length, results: formulas.map((one) => tokens(one.text).findIndex(([kind, word]) => kind === 'op' && word === '=')),
    unnamed: formulas.flatMap((one) => one.parts.map(([word]) => word).filter((word) => !drawn(one).includes(word))),
  },
  recent: { name: RECENT, days: RECENT_DAYS, periods: PERIODS,
    seen: ['2026-11-13', '2026-10-14', '2026-10-13', '2026-11-20', '', 'soon', '2026-10-14T09:00:00+09:00'].map((date) => within(date, '2026-11-13')),
    wider: [within('2026-08-15', '2026-11-13', 90), within('2026-08-14', '2026-11-13', 90)], noToday: within('2026-11-13', '') },
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

    def test_translation_state_is_told_without_a_percentage(self):
        # 사이트에는 검수를 마친 번역만 실린다. 다 실린 문서에는 표시가 없고, 그렇지 않은 문서에만 '번역 준비 중'이라고 적는다
        ready = self.seen["ready"]
        self.assertEqual(ready["states"], ["ready", "partial", "none", "ready", "ready", "ready"])
        self.assertEqual(ready["labels"], ["", "일부 번역 준비 중", "번역 준비 중"])
        for path in ("site/js/views/laws.js", "site/js/views/law.js", "site/js/views/search/hits.js"):
            with open(path, encoding="utf-8") as file:
                self.assertNotRegex(file.read(), r"국문 번역 \$\{[^}]*\}%", path)   # 퍼센트를 화면에 적지 않는다

    def test_the_item_sheet_finds_the_goods_under_a_code(self):
        sheet = self.seen["sheet"]
        self.assertEqual(sheet["under"], [True] * 7)   # 앞자리로 찾는다. 8자리를 넘으면 앞 8자리로, 4자리가 안 되면 찾지 않는다
        # 그 코드의 품목이 없으면 앞 6자리, 앞 4자리 차례로 넓혀 처음 품목이 있는 곳을 알려 준다
        self.assertEqual(sheet["near"], [{"code": "7208", "count": 2}, {"code": "7208", "count": 2}, None, None])
        self.assertEqual((sheet["years"], sheet["limit"]), ([2026, 2026, 2034, 2026], 12))

    def test_the_item_sheet_uses_the_estimate_of_the_calculator(self):
        sheet = self.seen["sheet"]
        # 기본값 2.118에 마크업 10%를 더하고, 벤치마크 1.370 × CBAM 계수 97.5% × 보정계수 100%를 뺀다(해설서의 계산 예와 같은 값)
        self.assertEqual(sheet["coil"], {"code": "72081000", "value": 2.118, "markup": 10, "embedded": 2.33, "benchmark": 1.37, "factor": 97.5, "cscf": 100,
                                         "allocation": 1.336, "perTonne": 0.994, "cost": 79.524, "route": "C", "routeAlt": "", "more": 0, "year": 2026})
        # 세부 품목이 둘인 품목은 줄마다 값과 생산경로가 다르다
        self.assertEqual(sheet["clinker"], [["White clinker", "B", 1.353, 0.515, 1], ["Other clinker", "A", 1.012, 0.363, 1]])
        self.assertEqual(sheet["tool"], {"route": "F", "routeAlt": "J", "benchmark": 1.64})   # 2028년은 둘째 연도 구간의 값. 합금강은 고합금강의 경로와 견준다
        self.assertIsNone(sheet["none"])                                                      # CBAM 계수가 없으면 어림하지 않는다
        years = sheet["yearly"]
        self.assertEqual([row[0] for row in years], list(range(2026, 2035)))
        self.assertEqual((years[0][1:], years[-1][1:]), ([0.994, 79.524, False, False], [2.753, 220.272, True, True]))   # 2034년에는 무상할당 조정이 없다. 2031년부터는 가정이 든다
        self.assertEqual([row[4] for row in years[:2]], [False, True])                                                   # 2027년부터는 갱신될 벤치마크의 해
        self.assertEqual(sheet["marked"], [[2026, 10, 2.33, False], [2027, 20, 2.542, False], [2028, 30, 2.753, True]])
        self.assertEqual(sheet["unmarked"], [])

    def test_the_item_sheet_lists_benchmarks_by_route_and_period(self):
        tables = self.seen["sheet"]["benchmarks"]
        self.assertEqual(tables["coil"], [{"route": "C", "name": "탄소강, 고로·전로", "a": [0.044, 0.044], "b": [1.37, 1.37]},
                                          {"route": "D", "name": "탄소강, 직접환원철·전기로", "a": [0.044, 0.044], "b": [0.481, 0.481]}])
        self.assertEqual(tables["clinker"], [["A", "회색 클링커·시멘트", [0.666, 0.666], [0.666, 0.666]], ["B", "백색 클링커·시멘트", [0.859, 0.859], [0.859, 0.859]]])
        self.assertEqual(tables["tool"], [["F", [0.2, 0.1], [1.807, 1.64]], ["J", [0.2, 0.1], [1.18, 1.148]]])
        self.assertEqual(self.seen["sheet"]["split"], [False, False, True])   # 연도 구간에 따라 값이 다른 품목만 표에 구간을 나누어 적는다

    def test_the_item_sheet_shows_only_the_lines_that_fit_the_item(self):
        sheet = self.seen["sheet"]
        self.assertEqual(sheet["flags"], [{"direct": True, "both": False, "priced": True, "unpriced": False}, {"direct": True, "both": True, "priced": False, "unpriced": False},
                                          {"direct": True, "both": False, "priced": False, "unpriced": True}, {"direct": False, "both": False, "priced": False, "unpriced": True}])
        self.assertEqual(sheet["shown"], [["늘", "직접", "값 있음"], ["늘", "둘 다", "값 없음"]])
        self.assertEqual((sheet["empty"], sheet["sector"]), ([], ["hydrogen", None, None]))

    def test_terms_in_the_text_are_found_for_the_inline_glossary(self):
        gloss = self.seen["gloss"]
        # 국문 표기는 띄어쓰기가 달라도 찾는다. 한 용어의 두 표기(국문, 약어)가 한 글에 함께 나오면 처음 것만 표시한다
        self.assertEqual(gloss["spacing"], [["부문간 보정계수", "부문 간 보정계수"]])
        # 긴 표기부터 본다. 긴 표기에 걸린 자리에서는 그 안의 짧은 표기를 다시 찾지 않는다
        self.assertEqual(gloss["longest"], [[["EU ETS", "EU 배출권거래제"], ["ETS", "배출권거래제"]], [["기본 탄소가격", "기본 탄소가격"], ["탄소가격", "탄소가격"]]])
        # 영문 약어는 낱말 하나로 나온 곳만, 대소문자를 가려 찾는다(markets의 ets, see에 걸리지 않는다). 약어에 붙은 숫자는 다른 말이다(ETS2)
        self.assertEqual(gloss["whole"], [[["SEEs", "고유 내재배출량"]], [["SEE", "고유 내재배출량"]]])
        self.assertEqual(gloss["plural"], [["EUAs", "EU 배출권"], ["CCUS", "탄소 포집·저장"], ["RED II", "재생에너지 지침"]])   # 복수형의 s는 받아 준다. 같은 용어의 다른 표기(CCS)는 다시 표시하지 않는다
        self.assertEqual(gloss["once"], [[["탄소가격", "탄소가격"]], [["CSCF", "부문 간 보정계수"]]])                                # 글 한 편에서 용어마다 한 번만
        self.assertEqual(gloss["skipped"], [["CSCF", "부문 간 보정계수"]])
        self.assertEqual(gloss["empty"], [[], [], [], []])

    def test_a_formula_line_is_cut_into_boxes_and_signs(self):
        figures = self.seen["figures"]
        self.assertEqual(figures["tokens"], [["term", "인증서 수"], ["op", "="], ["op", "("], ["term", "내재배출량"], ["op", "−"], ["term", "무상할당량"], ["op", ")"], ["op", "×"], ["term", "수입량"]])
        self.assertEqual((figures["plain"], figures["none"]), ([["term", "CO2e 1톤"]], []))
        # 실린 식은 모두 '결과 = …' 꼴이고, 풀이가 달린 말은 빠짐없이 칸으로 그려진다
        self.assertGreaterEqual(figures["formulas"], 3)
        self.assertEqual(set(figures["results"]), {1})
        self.assertEqual(figures["unnamed"], [])

    def test_a_date_on_a_timeline_is_written_out_in_korean(self):
        self.assertEqual(self.seen["figures"]["when"], ["2027년 2월 1일부터", "2027년 11월 1일", "2027년 각 분기 말", "2026년부터", ""])

    def test_recent_news_is_counted_and_listed_by_one_rule(self):
        recent = self.seen["recent"]
        self.assertEqual((recent["name"], recent["days"]), ("recent", 30))
        self.assertIn(recent["days"], recent["periods"])      # 첫 화면이 센 날수를 소식 화면의 기간에서도 고를 수 있다
        # 오늘, 꼭 30일 전, 31일 전, 앞날의 날짜, 날짜 없음, 날짜가 아닌 글, 시각이 붙은 날짜
        self.assertEqual(recent["seen"], [True, True, False, True, False, False, True])
        self.assertEqual(recent["wider"], [True, False])
        self.assertFalse(recent["noToday"])

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

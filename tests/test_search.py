"""사이트 검색과 주 메뉴의 펼침 목록 가운데 브라우저 없이 볼 수 있는 것.

찾는 셈(js/search/find.js), 찾기 좋은 줄 만들기(rows.js), 화면으로 바로 가는 길(pages.js), 품목 코드 읽기(codes.js),
짧은 영문 약어를 찾는 기준(js/laws/engine.js), 메뉴에 싣는 값(tools/publish/derive.py의 menu, js/ui/navmenu.js의 menuLists),
그리고 머리글의 짜임(index.html)이 화면 모듈과 맞는지를 본다.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

from tools.publish import derive

SCRIPT = r"""
import { find, makeIndex, marks, parse, split } from './site/js/laws/engine.js';
import { codeIn, codeVerdict, codeWords } from './site/js/search/codes.js';
import { gather, keep, missing, needed, rank, reach, tally } from './site/js/search/find.js';
import { findPages } from './site/js/search/pages.js';
import * as rows from './site/js/search/rows.js';
import { menuLists } from './site/js/ui/navmenu.js';

const terms = [
  { en: 'default value', ko: '기본값', abbr: '', alt: '', note: '2차 데이터로 정한 대푯값' },
  { en: 'default carbon price', ko: '기본 탄소가격', abbr: '', alt: '', note: '배출량 기본값과 다른 개념' },
  { en: 'Emissions Trading System', ko: '배출권거래제', abbr: 'ETS', alt: '배출권 거래제', note: '' },
  { en: 'oxidation factor', ko: '산화계수', abbr: 'OF', alt: '', note: '' },
  { en: 'continuous emission measurement', ko: '연속측정방법', abbr: 'CEM', alt: '', note: '' },
  { en: 'European Union', ko: 'EU', abbr: 'EU', alt: '유럽연합', note: '' },
  { en: 'euro', ko: '유로', abbr: 'EUR', alt: '', note: '' },
  { en: 'specific embedded emissions', ko: '고유 내재배출량', abbr: 'SEE', alt: '', note: '' },
  { en: 'verifier', ko: '검증기관', abbr: '', alt: '', note: '' },
];
const index = makeIndex(terms);
const items = [
  { id: 'old', title: '영국, CBAM 기본값 안내 공개', summary: '영국 정부가 기본값을 확인하는 안내를 냈습니다.', impact: '', topics: ['영국'], published: '2025-06-01', listed: '2025-06-02', sourceName: '숨길 출처' },
  { id: 'new', title: '영국, CBAM 기본값 안내 공개', summary: '영국 정부가 기본값을 확인하는 안내를 냈습니다.', impact: '', topics: ['영국'], published: '2026-11-01', listed: '2026-11-02' },
  { id: 'price', title: '2026년 3분기 CBAM 인증서 가격', summary: '인증서 가격이 게시되었습니다.', impact: '', topics: ['인증서 가격'], published: '2026-10-05' },
  { id: 'gone', title: '내린 소식의 제목', summary: '기본값 이야기', withdrawn: true, published: '2026-01-01' },
  { title: '번호가 없는 소식' },
];
const rules = { groups: [{ code: 'uk', name: '영국 CBAM' }], regulations: [
  { id: 'uk-cbam', group: 'uk', name: '영국 CBAM', official: 'Finance Act 2026', summary: '영국이 따로 시행하는 제도입니다.', status: '', next: '',
    analysis: { sections: [{ title: '주요 내용', items: [{ text: '기본값은 영국 재무부가 고시로 정합니다.' }] }] }, timeline: [{ date: '2026-03-18', text: '근거 법률이 제정되었습니다.' }] }] };
const events = [{ date: '2027-02-01', title: 'CBAM 인증서 판매 시작', kind: '시행', note: '', basis: 'Sale of certificates starts.' },
  { date: '2027-09-30', title: '첫 CBAM 신고서 제출', kind: '기한', note: '기본값으로 신고한 값도 냅니다.', derived: true, duty: 'eu-first' }];
const duties = [{ id: 'eu-first', date: '2027-09-30', title: '첫 CBAM 신고서 제출', who: 'EU 수입자', text: '기본값으로 신고한 값도 냅니다.', basis: 'CBAM 규정 제6조' }];
const cn = { current: [{ sector: 'steel', codes: ['72'], shown: '72', text: 'Iron and steel', except: [{ codes: ['72022'], shown: '7202 2', text: 'Ferro-silicon' }] },
    { sector: 'cement', codes: ['25070080'], shown: 'ex 2507 00 80', ex: true, text: 'Other kaolinic clays' }],
  proposed: [{ sector: 'steel', codes: ['72'], shown: '72', text: 'Iron and steel' }, { sector: 'combined', codes: ['854449'], shown: '8544 49', text: 'Electric conductors' }],
  council: { added: [{ codes: ['870810'], shown: '8708 10', text: 'Bumpers' }], removed: [] } };
const acts = [{ id: 'guide-5d', group: 'guide', name: '가이던스 5d: 철강', short: '가이던스 5d', official: 'Guidance document 5d', url: 'https://x.example/download/abc-123_en?filename=g.pdf', remark: '' },
  { id: '32025R2621', group: 'act', name: '기본값 이행규정', short: '기본값 이행규정', official: 'Implementing Regulation (EU) 2025/2621', url: 'https://eur-lex.example/2621' }];
const documents = [{ id: 'abc-123', title: 'Guidance No. 5d - iron and steel', filename: 'g.pdf', format: 'PDF' }, { id: 'dv', title: 'Default values for the definitive period', filename: 'dv.pdf', format: 'PDF' }];
const book = { news: rows.newsRows(items), rules: rows.ruleRows(rules), terms: rows.termRows(terms), dates: rows.dateRows(events, duties), codes: rows.codeRows(cn),
  files: rows.fileRows(documents, acts), laws: rows.lawRows(acts) };

const ask = (query) => { const parsed = parse(query, index); return { parsed, found: gather(parsed, book, { today: '2026-11-12' }) }; };
const names = (hits) => hits.map((hit) => hit.row.p);
const one = ask('기본값');
const two = ask('영국 기본값');
const three = ask('영국 기본값 고시');
const odd = ask('기본값 zzzz');
const english = ask('default values');
const text = [
  { a: 'x', p: 'art-1', n: '', t: '', k: '', x: 'Markets and targets for cement offsets. Allow 150 tonnes because of code 72081000.', y: '' },
  { a: 'x', p: 'art-2', n: '', t: '', k: '', x: 'The EU ETS and ETS2; EUAs are allowances. A CEM system. Lower use: 50 tonnes under 7208 10 00.', y: '' },
];
const labels = (query) => parse(query, index).groups.map((group) => group.label);
const where = (query) => find(text, parse(query, index), { limit: 9 }).map((hit) => hit.row.p);
const code = { query: '7318 15 00', groups: [codeWords('73181500')] };
const codeText = [{ a: 'x', p: 'spaced', n: '', t: '', k: '', x: 'Screws under 7318 15 00.', y: '' }, { a: 'x', p: 'joined', n: '', t: '', k: '', x: 'Code 73181500 applies.', y: '' },
  { a: 'x', p: 'noise', n: '', t: '', k: '', x: 'In 2015 about 150 euro and 300 units, 7318 only.', y: '' }];

console.log(JSON.stringify({
  rows: {
    news: book.news.map((row) => [row.p, row.y]), sourceLeak: JSON.stringify(book.news.map((row) => [row.t, row.x, row.names])).includes('숨길 출처'),
    rule: book.rules[0].y, termNames: book.terms[2].names, dateForms: book.dates.map((row) => row.form), codeForms: book.codes.map((row) => [row.form, row.ref.shown]),
    fileActs: book.files.map((row) => [row.p, row.act, row.names.includes('가이던스 5d: 철강')]), lawNames: book.laws[0].names,
  },
  find: {
    needed: [needed(one.parsed), needed(two.parsed), needed(three.parsed), needed(parse('무엇인가요', index))],
    oneNews: names(keep(one.found, 1).news), oneTerms: names(keep(one.found, 1).terms), oneRules: names(keep(one.found, 1).rules), oneDates: names(keep(one.found, 1).dates), oneLaws: names(keep(one.found, 1).laws),
    twoNews: names(keep(two.found, needed(two.parsed)).news), twoTerms: names(keep(two.found, needed(two.parsed)).terms),
    threeRules: names(keep(three.found, needed(three.parsed)).rules),
    oddStrict: tally(keep(odd.found, needed(odd.parsed))).total, oddReach: reach(odd.found), oddMissing: missing(odd.parsed, odd.found), oddLoose: tally(keep(odd.found, reach(odd.found))).total > 0,
    englishFiles: names(keep(english.found, 1).files), englishTerms: names(keep(english.found, 1).terms),
    empty: tally(ask('무엇인가요').found).total,
    plain: names(rank(book.news, parse('인증서 가격', index))),
  },
  pages: Object.fromEntries(['가격', '인증서 가격 추이', '탄소가격 공제', 'three months', 'hs', '규제', '규정', '신고 기한', '기본값', '가'].map((query) => [query, findPages(query).map((page) => page.href)])),
  codes: {
    read: ['7208', '7318 15 00', 'CN 7208', 'HS코드 7208.10', '720', 'abc 7208', '2026년'].map(codeIn),
    verdicts: Object.fromEntries(['7208', '2026', 'cn 9999', '999999', '7202 21 00', '8544 49', '8708 10', '2507 00 80'].map((query) => { const found = codeVerdict(query, cn); return [query, found ? [found.state, found.later, found.council, found.rows.length] : null]; })),
  },
  engine: {
    ets: find(text, parse('ETS', index), { limit: 9 }).map((hit) => hit.row.p), cem: find(text, parse('CEM', index), { limit: 9 }).map((hit) => hit.row.p),
    lowerOf: parse('default values of steel', index).groups.map((group) => group.label), upperOf: parse('OF 산정', index).groups[0].en,
    lowerEts: parse('ets', index).groups.map((group) => group.label),
    inside: [labels('neutral'), labels('Europe'), labels('carbon neutrality'), labels('reporting verifiers'), labels('euros'), labels('see article 5'), labels('SEE 산정')[0], labels('EU의 제도')[0]],
    starts: [where('low'), where('use'), where('50'), where('7208'), where('UK')], abbrTyped: where('NCA'),
    codeWords: codeWords('73181500'), codeHits: find(codeText, code, { limit: 9 }).map((hit) => hit.row.p), shortCode: codeWords('7208').ko,
    pieces: split('Markets, the ETS, ETS2 and EUAs; default values', ['ets', 'eua', 'default value']), korean: split('기본값과 기본값', ['기본값']),
    marks: marks(parse('ETS', index)),
  },
  menu: (() => { const lists = menuLists({ menu: { rules: [{ code: 'uk', name: '영국 CBAM', icon: 'abroad' }], years: [2026, 2027], topics: ['law'] } }, [{ code: 'law', name: '제도·법령' }, { code: 'etc', name: '기타' }]);
    return { news: lists.news.items.map((item) => item.href), cols: lists.news.cols, rules: lists.rules.items.map((item) => [item.href, item.icon]), years: lists.calendar.items.map((item) => item.href),
      docs: lists.docs.items.map((item) => item.href), price: lists.price.items.map((item) => [item.href, Boolean(item.about)]),
      bare: menuLists({}, [{ code: 'law', name: '제도·법령' }, { code: 'etc', name: '기타' }]).news.items.length,
      notices: menuLists({ menu: { topics: ['law'], notices: 3 } }, [{ code: 'law', name: '제도·법령' }]).news.items.map((item) => [item.href, item.name]) }; })(),
}));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 찾기는 시험하지 않는다")
class SearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_rows_carry_what_can_be_searched_and_nothing_else(self):
        rows = self.seen["rows"]
        news = dict(rows["news"])
        self.assertEqual(set(news), {"old", "new", "price", "gone"})            # 번호가 없는 소식은 싣지 않는다
        self.assertEqual(news["gone"], "")                                     # 요약을 내린 소식은 제목으로만 찾는다
        self.assertIn("영국", news["new"].split("\n")[-1])                       # 붙인 주제어는 본문의 마지막 줄
        self.assertFalse(rows["sourceLeak"])                                   # 소식의 출처 이름은 찾는 글에 넣지 않는다
        self.assertIn("기본값은 영국 재무부가 고시로 정합니다.", rows["rule"])     # 규제는 분석의 글과
        self.assertIn("근거 법률이 제정되었습니다.", rows["rule"])               # 연혁으로도 찾는다
        self.assertEqual(rows["termNames"], ["배출권거래제", "Emissions Trading System", "ETS", "배출권 거래제"])
        self.assertEqual(rows["dateForms"], ["event", "duty"])                 # 의무에서 만든 달력의 일정은 두 번 싣지 않는다
        self.assertEqual(rows["codeForms"], [["current", "72"], ["current", "ex 2507 00 80"], ["proposed", "8544 49"]])  # 두 목록에 다 있는 줄은 한 번만
        self.assertEqual(rows["fileActs"], [["abc-123", "guide-5d", True], ["dv", "", False]])  # 번역해 실은 문서는 국문 이름으로도 찾는다
        self.assertEqual(rows["lawNames"], ["가이던스 5d: 철강", "Guidance document 5d", "가이던스 5d"])

    def test_words_must_come_together_and_exact_names_come_first(self):
        found = self.seen["find"]
        self.assertEqual(found["needed"], [1, 2, 2, 0])                          # 둘까지는 모두, 셋부터는 하나가 빠져도 된다
        self.assertEqual(found["oneTerms"][0], "0")                              # 이름이 찾는 말과 똑같은 용어가 맨 앞
        self.assertIn("1", found["oneTerms"])                                    # 설명에 나온 용어도 찾는다
        self.assertEqual(found["oneNews"], ["new", "old"])                       # 같은 글이면 새 소식이 앞. 내린 소식의 요약으로는 찾지 않는다
        self.assertEqual(found["oneRules"], ["uk-cbam"])
        self.assertEqual(found["oneDates"], ["duty-eu-first"])
        self.assertEqual(found["oneLaws"], ["32025R2621"])
        self.assertEqual(found["twoNews"], ["new", "old"])                       # 두 낱말이 함께 나온 소식만
        self.assertEqual(found["twoTerms"], [])                                  # 한 낱말만 나온 용어는 뺀다
        self.assertEqual(found["threeRules"], ["uk-cbam"])
        self.assertEqual(found["plain"], ["price"])

    def test_it_steps_back_only_when_nothing_has_every_word(self):
        found = self.seen["find"]
        self.assertEqual(found["oddStrict"], 0)
        self.assertEqual(found["oddReach"], 1)
        self.assertEqual(found["oddMissing"], ["zzzz"])
        self.assertTrue(found["oddLoose"])
        self.assertEqual(found["empty"], 0)                                      # 물음말만 있으면 찾을 낱말이 없다

    def test_a_korean_or_english_word_finds_the_other_language_through_the_glossary(self):
        found = self.seen["find"]
        self.assertEqual(found["englishFiles"], ["dv"])
        self.assertEqual(found["englishTerms"][0], "0")
        self.assertEqual(self.seen["find"]["oneNews"], ["new", "old"])

    def test_page_shortcuts_follow_names_and_whole_words(self):
        pages = self.seen["pages"]
        self.assertEqual(pages["가격"], ["#price"])
        self.assertEqual(pages["인증서 가격 추이"][0], "#price")
        self.assertEqual(pages["탄소가격 공제"], [])                               # 다른 낱말 속의 '가격'은 화면을 부르는 말이 아니다
        self.assertEqual(pages["three months"], [])                              # months의 hs
        self.assertEqual(pages["hs"], ["#cn"])
        self.assertEqual(pages["규제"], ["#rules"])
        self.assertEqual(pages["규정"], ["#laws"])
        self.assertEqual(pages["신고 기한"], ["#calendar"])
        self.assertEqual(pages["기본값"], [])
        self.assertEqual(pages["가"], [])

    def test_a_code_is_read_only_when_it_is_one(self):
        codes = self.seen["codes"]
        self.assertEqual(codes["read"], ["7208", "73181500", "7208", "720810", "", "", ""])
        verdicts = codes["verdicts"]
        self.assertEqual(verdicts["7208"], ["in", False, False, 1])
        self.assertIsNone(verdicts["2026"])                                      # 목록에 없는 네 자리 숫자는 연도일 수 있다
        self.assertEqual(verdicts["cn 9999"][0], "out")                          # 코드라고 밝혀 적었으면 판정을 준다
        self.assertEqual(verdicts["999999"][0], "out")
        self.assertEqual(verdicts["7202 21 00"][0], "excluded")
        self.assertEqual(verdicts["8544 49"], ["out", True, False, 0])           # 확대 개정안이 더한 품목
        self.assertEqual(verdicts["8708 10"], ["out", False, True, 0])           # 이사회 안이 더한 코드
        self.assertEqual(verdicts["2507 00 80"][0], "part")

    def test_short_abbreviations_match_whole_words_only(self):
        engine = self.seen["engine"]
        self.assertEqual(engine["ets"], ["art-2"])                               # markets, targets, offsets에는 걸리지 않는다
        self.assertEqual(engine["cem"], ["art-2"])                               # cement에는 걸리지 않는다
        self.assertEqual(engine["lowerOf"], ["기본값", "steel"])                  # 영문 질문의 of는 약어가 아니다
        self.assertEqual(engine["upperOf"], ["oxidation factor"])                # 대문자로 적어도 흔한 낱말과 같은 약어로는 찾지 않는다
        self.assertEqual(engine["lowerEts"], ["배출권거래제"])                    # 세 글자부터는 소문자로 적어도 약어로 읽는다
        self.assertEqual(engine["pieces"], [["Markets, the ", False], ["ETS", True], [", ", False], ["ETS", True], ["2 and ", False], ["EUAs", True], ["; ", False], ["default values", True]])
        self.assertEqual(engine["korean"], [["기본값", True], ["과 ", False], ["기본값", True]])
        self.assertIn("ets", engine["marks"])

    def test_glossary_words_are_not_read_out_of_the_middle_of_other_words(self):
        inside = self.seen["engine"]["inside"]
        self.assertEqual(inside[0], ["neutral"])                                 # neutral의 eu를 EU로 읽지 않는다
        self.assertEqual(inside[1], ["europe"])                                  # europe의 euro도
        self.assertEqual(inside[2], ["carbon", "neutrality"])
        self.assertEqual(inside[3], ["검증기관", "reporting"])                   # 복수형은 용어집의 낱말로 읽고, 남은 글자(s)는 버린다
        self.assertEqual(inside[4], ["유로"])
        self.assertEqual(inside[5], ["see", "article"])                          # 흔한 낱말과 같은 약어는 대문자로 적었을 때만
        self.assertEqual(inside[6], "고유 내재배출량")
        self.assertEqual(inside[7], "EU")                                        # 조사가 붙은 영문 표기는 읽는다

    def test_short_words_and_numbers_are_not_found_inside_other_words(self):
        engine = self.seen["engine"]
        self.assertEqual(engine["starts"], [["art-2"], ["art-2"], ["art-2"], ["art-2"], []])  # allow, because, 150, 72081000에는 걸리지 않는다
        self.assertEqual(engine["abbrTyped"], [])

    def test_a_code_is_searched_as_one_word(self):
        engine = self.seen["engine"]
        self.assertEqual(engine["codeWords"], {"label": "7318 15 00", "ko": ["73181500", "7318 15 00"], "en": ["73181500", "7318 15 00"], "refs": []})
        self.assertEqual(sorted(engine["codeHits"]), ["joined", "spaced"])        # 15나 00만 든 글은 찾지 않는다
        self.assertEqual(engine["shortCode"], ["7208"])

    def test_menu_lists_follow_the_published_data(self):
        menu = self.seen["menu"]
        self.assertEqual(menu["news"], ["#news", "#news-law"])                   # 소식이 없는 주제는 싣지 않는다
        self.assertEqual(menu["cols"], 2)
        self.assertEqual(menu["rules"], [["#rules", "law"], ["#rules-uk", "abroad"]])
        self.assertEqual(menu["years"], ["#calendar-2026", "#calendar-2027"])
        self.assertEqual(menu["docs"], ["#cn", "#laws", "#docs", "#terms", "#about"])
        self.assertEqual(menu["price"], [["#price", True], ["#calc", True]])     # 화면의 설명이 붙는다
        self.assertEqual(menu["bare"], 3)                                        # 메뉴 값이 없으면 주제를 모두 싣는다
        self.assertEqual(menu["notices"][-1], ["#news-notices", "국내 공지·자료"])   # 국내 공지·자료가 있으면 주제 뒤에 싣는다


class MenuDataTest(unittest.TestCase):
    def test_the_menu_lists_used_groups_years_and_topics(self):
        rules = {"groups": [{"code": "eu-law", "name": "EU CBAM 기본법", "icon": "law"}, {"code": "empty", "name": "빈 묶음"}, {"code": "uk", "name": "영국 CBAM"}],
                 "regulations": [{"id": "a", "group": "uk"}, {"id": "b", "group": "eu-law"}]}
        events = [{"date": "2027-02-01"}, {"date": "2026-01-01"}, {"date": "2027-09"}, {"date": ""}, {}]
        items = [{"topic": "price"}, {"topic": "law"}, {"topic": "price"}, {}]
        self.assertEqual(derive.menu(rules, events, items), {
            "rules": [{"code": "eu-law", "name": "EU CBAM 기본법", "icon": "law"}, {"code": "uk", "name": "영국 CBAM", "icon": ""}],
            "years": [2026, 2027], "topics": ["law", "price"], "notices": 0})
        self.assertEqual(derive.menu(None, None), {"rules": [], "years": [], "topics": [], "notices": 0})
        # 제목이 곧 내용인 국내 공지·자료는 주제를 셀 때 빼고 수만 따로 적는다(요약을 내린 것은 보통 소식으로 센다)
        briefs = [{"topic": "korea", "brief": True}, {"topic": "korea", "brief": True}, {"topic": "events", "brief": True, "withdrawn": True}]
        self.assertEqual(derive.menu(None, None, items + briefs), {"rules": [], "years": [], "topics": ["events", "law", "price"], "notices": 2})
        # 주제 목록을 넘기면, 목록에 없는 주제나 주제가 없는 소식은 화면처럼 '기타'로 센다
        topics = [{"code": "law"}, {"code": "price"}, {"code": "etc"}]
        self.assertEqual(derive.menu(None, None, items + [{"topic": "gone"}], topics)["topics"], ["etc", "law", "price"])


class ShellTest(unittest.TestCase):
    """머리글의 짜임(index.html)이 화면 모듈과 맞는지."""

    @classmethod
    def setUpClass(cls):
        cls.page = pathlib.Path("site/index.html").read_text(encoding="utf-8")
        cls.nav = cls.page.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]

    def test_the_search_box_is_in_the_header_and_its_view_is_known(self):
        head = self.page.split("<header", 1)[1].split("</header>", 1)[0]
        self.assertRegex(head, r'<form class="head-search" id="site-search" role="search" aria-label="[^"]+">')
        self.assertRegex(head, r'<label class="sr" for="site-q">[^<]+</label>\s*<input id="site-q" type="search"')
        self.assertRegex(head, r'<button type="submit" aria-label="[^"]+"')
        router = pathlib.Path("site/js/router.js").read_text(encoding="utf-8")
        app = pathlib.Path("site/js/app.js").read_text(encoding="utf-8")
        self.assertRegex(router, r'const VIEWS = \[[^\]]*"search"[^\]]*\];')
        self.assertRegex(app, r"const VIEWS = \{[^}]*\bsearch\b[^}]*\};")
        self.assertIn('search: "검색"', app)
        self.assertIn('id: "search-q"', pathlib.Path("site/js/views/search.js").read_text(encoding="utf-8"))  # 머리글의 단추가 찾아가는 큰 입력 칸

    def test_every_menu_button_sits_right_after_its_menu(self):
        pairs = re.findall(r'<a href="#(\w+)"[^>]*data-menu="(\w+)"[^>]*>([^<]+)</a>\s*<button class="nav-more" type="button" data-menu="(\w+)" aria-expanded="false" aria-label="([^"]+)"', self.nav)
        self.assertEqual([pair[1] for pair in pairs], ["news", "rules", "price", "calendar", "docs"])
        for view, menu, name, button, label in pairs:
            self.assertEqual((view, menu), (button, button))                     # 메뉴의 이름은 그 화면의 이름과 같다
            self.assertTrue(label.startswith(name), label)
        self.assertEqual(self.nav.count('class="nav-more"'), len(pairs))
        lists = pathlib.Path("site/js/ui/navmenu.js").read_text(encoding="utf-8")
        for _, menu, _, _, _ in pairs:
            self.assertRegex(lists, rf"\b{menu}: \{{")                            # 단추마다 목록이 있다

    def test_every_linked_stylesheet_exists(self):
        sheets = re.findall(r'<link rel="stylesheet" href="(css/[^"]+)">', self.page)
        self.assertIn("css/search.css", sheets)
        self.assertIn("css/navmenu.css", sheets)
        for sheet in sheets:
            self.assertTrue((pathlib.Path("site") / sheet).exists(), sheet)


if __name__ == "__main__":
    unittest.main()

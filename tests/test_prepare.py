"""역할별 준비 목록(data/prepare.json): 검사(tools/publish/prepare.py)와, 화면이 쓰는 셈(site/js/prepare/plan.js, done.js)."""
import copy
import json
import shutil
import subprocess
import unittest

from tools.common.jsonio import read_json
from tools.publish import duties, handbook, prepare

# 역할의 것이지만 그 역할이 하는 일이 아니어서 목록에 넣지 않은 일정
LEFT_OUT = {"eu-threshold-review"}   # 집행위원회가 하는 평가

SCRIPT = r"""
import { cleared, keeper, KEY, pruned, readDone, toggled, writeDone } from './site/js/prepare/done.js';
import { hrefOf, itemsOf, occurrence, placeOf, progress, resolve, upcoming } from './site/js/prepare/plan.js';

const roles = [{ key: 'declarant', groups: [{ items: [{ id: 'a' }, { id: 'b' }] }, { items: [{ id: 'c' }] }] }, { key: 'uk', groups: [] }];
const duties = [
  { id: 'plan', date: '2026-11-15', kind: '기한', title: '계획 통지', text: '해마다 보냅니다.', supplier: '사업자가 들어갑니다.', repeat: true },
  { id: 'plan-2027', date: '2027-11-15', kind: '기한', title: '계획 통지', text: '해마다 보냅니다.', supplier: '사업자가 들어갑니다.', repeat: true },
  { id: 'plan-2028', date: '2028-11-15', kind: '기한', title: '계획 통지', text: '해마다 보냅니다.', repeat: true },
  { id: 'planning', date: '2026-12-01', kind: '시행', title: '다른 일정', text: '이름이 비슷한 다른 일정입니다.' },
  { id: 'start', date: '2027-01-01', kind: '시행', title: '적용 시작', text: '이날부터 적용됩니다.' },
  { id: 'start-2028', date: '2028-01-01', kind: '시행', title: '이름만 비슷한 일정', text: '해마다 돌아오는 일정이 아닙니다.' },
  { id: 'old', date: '2026-03-31', kind: '기한', title: '지난 기준일', text: '지난 일정입니다.' },
];
const day = '2026-11-18';
const rows = [
  resolve({ id: 'a', title: '내 제목', text: '내 글', duty: 'start', sections: [{ href: '#handbook-x.y' }] }, duties, day),
  resolve({ id: 'b', duty: 'plan', note: 'supplier' }, duties, day),
  resolve({ id: 'c', duty: 'plan' }, duties, day),
  resolve({ id: 'd', title: '날짜 없는 일', text: '글' }, duties, day),
  resolve({ id: 'e', duty: 'old' }, duties, day),
  resolve({ id: 'f', duty: 'planning' }, duties, day),
];
const store = (start) => { const kept = new Map(start ? [[KEY, start]] : []); return { getItem: (k) => (kept.has(k) ? kept.get(k) : null), setItem: (k, v) => kept.set(k, v), removeItem: (k) => kept.delete(k), kept }; };
const filled = store();
const wrote = writeDone(filled, new Set(['b', 'a']));
const emptied = store('["a"]');
writeDone(emptied, new Set());
const broken = { getItem: () => { throw new Error('막힘'); }, setItem: () => { throw new Error('막힘'); }, removeItem: () => {} };
// 표시를 읽고 적는 창구: 저장소가 되면 저장소(다른 탭이 적은 것도 읽힌다), 없거나 적지 못하면 기억해 둔 묶음. 적지 못한 뒤로는 계속 기억을 쓴다
const shared = store();
const kept = keeper(shared);
const keptWrote = kept.write(new Set(['a']));
shared.setItem(KEY, '["a","b"]');
const keptRead = [...kept.read()];
const bare = keeper(null);
const bareWrote = bare.write(new Set(['c']));
const bareRead = [...keeper(null).read()];
const stuck = keeper(broken);
const stuckWrote = stuck.write(new Set(['d']));
const stuckRead = [...stuck.read()];
const afterFailure = [...keeper(shared).read()];
const own = { id: 'g', title: '내 제목', text: '첫 계획에 관한 내 글', duty: 'plan' };
console.log(JSON.stringify({
  places: [placeOf('', roles), placeOf('uk', roles), placeOf('uk.u-records', roles), placeOf('nobody.x', roles), placeOf('declarant.d-holding', roles), placeOf('x', [])],
  hrefs: [hrefOf(roles, 'declarant'), hrefOf(roles, 'uk'), hrefOf(roles, 'declarant', 'a'), hrefOf(roles, 'uk', 'u-records')],
  occurrences: [occurrence(duties, 'plan', day).id, occurrence(duties, 'plan', '2026-11-15').id, occurrence(duties, 'plan', '2029-01-01').id, occurrence(duties, 'start', day).id,
    occurrence(duties, 'planning', day).id, occurrence(duties, 'none', day), occurrence(duties, 'start', '2027-06-01').id],
  moved: [resolve(own, duties, '2026-11-15'), resolve(own, duties, day)].map((row) => [row.title, row.text, row.duty.id]),
  spare: [resolve({ id: 'h', duty: 'gone', note: 'supplier', fallback: { title: '예비 제목', text: '예비 글' } }, duties, day),
    resolve({ id: 'i', duty: 'gone', fallback: { title: '예비 제목', text: '예비 글' } }, duties, day)].map((row) => [row.title, row.text, row.noteKind, row.duty, row.date]),
  pruned: [...pruned(new Set(['a', 'zzz', 'b']), new Set(['a', 'b', 'c']))],
  keeper: { keptWrote, keptRead, bareWrote, bareRead, stuckWrote, stuckRead, afterFailure },
  rows: rows.map((row) => ({ id: row.id, title: row.title, text: row.text, noteKind: row.noteKind, date: row.date, past: row.past, duty: row.duty ? row.duty.id : null })),
  soon: upcoming(rows, day).map((row) => row.id), soonTwo: upcoming(rows, day, 2).map((row) => row.id),
  items: itemsOf(roles[0]).map((item) => item.id), noItems: itemsOf(null),
  progress: [progress(rows, new Set(['a', 'c', 'zzz'])), progress(rows, new Set())],
  wrote, saved: filled.kept.get(KEY), read: [...readDone(filled)], emptied: emptied.kept.has(KEY),
  bad: [[...readDone(store('{"a":1}'))], [...readDone(store('not json'))], [...readDone(store('["ok-1", 3, "BAD ID", "<b>"]'))], [...readDone(broken)], writeDone(broken, new Set(['a']))],
  toggled: [[...toggled(new Set(['a']), 'b', true)].sort(), [...toggled(new Set(['a', 'b']), 'a', false)]],
  cleared: [...cleared(new Set(['a', 'b', 'u-1']), ['a', 'b', 'c'])],
}));
"""


class StoredListTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body, cls.book, cls.duty_body = read_json(prepare.SOURCE, None), read_json(handbook.SOURCE, None), read_json(duties.SOURCE, None)

    def item(self, body, item_id):
        return next(item for role in body["roles"] for group in role["groups"] for item in group["items"] if item["id"] == item_id)

    def changed(self, change):
        body = copy.deepcopy(self.body)
        change(body)
        return body, self.book, self.duty_body

    def found(self, change):
        return [what for _, what in prepare.problems(*self.changed(change))]

    def test_it_has_no_problems_and_covers_every_role(self):
        self.assertEqual(prepare.problems(self.body, self.book, self.duty_body), [])
        self.assertEqual([role["key"] for role in self.body["roles"]], [role["key"] for role in self.duty_body["roles"]])

    def test_every_dated_duty_of_a_role_is_on_its_list(self):
        for role in self.body["roles"]:
            listed = {item.get("duty") for group in role["groups"] for item in group["items"]}
            mine = {duty["id"] for duty in self.duty_body["duties"] if role["key"] in duty["roles"]}
            self.assertEqual(mine - listed - LEFT_OUT, set(), role["key"])

    def test_dates_and_numbers_are_read_whole(self):
        self.assertEqual(prepare.facts("2027년 9월 30일까지, 해마다 11월 15일, 순중량 50톤, 50% 이상, 3배에서 5배, 5만 파운드, 1.33유로, 제26조(1)"),
                         ["2027년9월30일", "11월15일", "50톤", "50%", "3배", "5배", "5만", "1.33유", "26조", "1"])
        self.assertEqual(prepare.facts("날짜도 수도 없는 글"), [])

    def test_a_number_or_date_the_sources_do_not_have_is_caught(self):
        for item_id, old, new, missing in (("d-threshold", "50톤", "60톤", "60톤"), ("d-holding", "50%", "40%", "40%"), ("d-holding", "1개월", "2개월", "2개"),
                                           ("d-first-declaration", "2027년 9월 30일", "2027년 9월 29일", "2027년9월29일"), ("u-threshold", "5만 파운드", "6만 파운드", "6만"),
                                           ("d-repurchase", "10월 31일", "10월 30일", "10월30일")):
            def change(body, item_id=item_id, old=old, new=new):
                item = self.item(body, item_id)
                self.assertIn(old, item["text"])
                item["text"] = item["text"].replace(old, new)
            found = self.found(change)
            self.assertEqual(len(found), 1, item_id)
            self.assertIn("기대는 글에 없는 날짜나 수", found[0])
            self.assertIn(missing, found[0])

    def test_a_date_or_number_inside_a_longer_one_does_not_count(self):
        have = prepare.source_facts("해마다 11월 1일까지, 순중량 150톤, 2027년 9월 30일까지 처음으로, 통지일부터 30일 안에")
        self.assertEqual([what for _, what in prepare.fact_problems("글", "1월 1일까지 50톤", have)], ["기대는 글에 없는 날짜나 수: ['1월1일', '50톤']"])
        self.assertEqual(prepare.fact_problems("글", "2027년 9월 30일, 9월 30일, 2027년, 9월, 11월, 30일 안에", have), [])   # 날짜는 그 일부로도 쓸 수 있다
        self.assertEqual([what for _, what in prepare.fact_problems("글", "9월 3일까지, 31일 안에", have)], ["기대는 글에 없는 날짜나 수: ['31일', '9월3일']"])
        self.assertEqual(prepare.source_facts("2027년 9월 30일") & {"30일", "2027년", "9월", "9월30일"}, {"2027년", "9월", "9월30일"})   # 날만 따로는 풀지 않는다
        self.assertTrue(any("꼴로 적음" in what for _, what in prepare.fact_problems("글", "2027. 9. 30.까지", have)))
        # 실제 항목으로: 한 글자만 다른 날짜
        def change(body):
            item = self.item(body, "d-first-declaration")
            self.assertIn("2027년 9월 30일", item["text"])
            item["text"] = item["text"].replace("2027년 9월 30일", "2027년 9월 3일")
        self.assertEqual(self.found(change), ["기대는 글에 없는 날짜나 수: ['2027년9월3일']"])

    def test_numbers_written_in_words_are_read_too(self):
        self.assertEqual(prepare.facts("두 달 안에 신청하고 네 번째 해가 끝날 때까지 보관합니다. 제출한 해와 열흘, 첫 해"), ["두달", "네번째", "열흘", "첫해"])
        self.assertEqual(prepare.facts("신고서를 제출한 해의 다음 해"), [])   # '제출한 해'의 '한 해'는 수가 아니다
        found = self.found(lambda body: self.item(body, "v-ip-accreditation").update(
            text=self.item(body, "v-ip-accreditation")["text"].replace("두 달 안에", "세 달 안에")))
        self.assertEqual(found, ["기대는 글에 없는 날짜나 수: ['세달']"])

    def test_group_names_role_notes_and_the_lead_are_checked_for_facts(self):
        def rename(body):
            group = next(group for group in body["roles"][0]["groups"] if "2027년" in group["name"])
            group["name"] = group["name"].replace("2027년", "2029년")
        found = prepare.problems(*self.changed(rename))
        self.assertEqual([(where.split()[-1], what) for where, what in found], [("이름", "기대는 글에 없는 날짜나 수: ['2029년']")])
        found = prepare.problems(*self.changed(lambda body: body["roles"][0].update(about="승인된 CBAM 신고인이 2031년 12월 31일까지 챙길 일입니다.")))
        self.assertEqual([(where, what) for where, what in found], [("역할 declarant 설명", "기대는 글에 없는 날짜나 수: ['2031년12월31일']")])
        found = prepare.problems(*self.changed(lambda body: body.update(lead=body["lead"] + " 2027년 1월 1일부터 달라집니다.")))
        self.assertEqual([(where, what) for where, what in found], [("소개와 알림", "기대는 글에 없는 날짜나 수: ['2027년1월1일']")])

    def test_an_id_fits_what_the_screen_stores(self):
        self.assertEqual(self.found(lambda body: self.item(body, "u-goods").update(id="u-" + "a" * (prepare.ID_MAX - 2))), [])
        self.assertTrue(any("id(" in what for what in self.found(lambda body: self.item(body, "u-goods").update(id="u-" + "a" * (prepare.ID_MAX - 1)))))

    def test_links_into_the_list_are_checked_against_it(self):
        places = {"prepare": prepare.listed(self.body)}
        self.assertEqual(sorted(places["prepare"]), sorted(role["key"] for role in self.body["roles"]))
        self.assertIn("d-holding", places["prepare"]["declarant"])
        for href in ("#prepare", "#prepare-operator", "#prepare-declarant.d-holding"):
            self.assertEqual(handbook._href_problem(href, None, places), "", href)
        for href in ("#prepare-nobody", "#prepare-declarant.nothing", "#prepare-operator.d-holding"):
            self.assertIn("준비 목록에 없는 곳", handbook._href_problem(href, None, places), href)
        self.assertEqual(handbook._href_problem("#prepare-nobody", None, {}), "")   # 목록을 넘기지 않으면 보지 않는다
        # 해설서가 준비 목록의 없는 곳을 가리키면 해설서의 검사가 잡는다
        book = copy.deepcopy(self.book)
        section = next(section for chapter in book["chapters"] for section in chapter["sections"] if any(str(link.get("href", "")).startswith("#prepare") for link in section.get("see") or []))
        next(link for link in section["see"] if link["href"].startswith("#prepare"))["href"] = "#prepare-declarant.nothing"
        self.assertTrue(any("준비 목록에 없는 곳" in what for _, what in handbook.problems(book, kinds=("format",), prepared=places["prepare"])))
        self.assertFalse(any("준비 목록" in what for _, what in handbook.problems(self.book, kinds=("format",), prepared=places["prepare"])))

    def test_the_text_of_a_duty_counts_as_a_source(self):
        # 일정에 기대는 항목은 그 일정의 날짜와 글에 적힌 수를 쓸 수 있다
        def change(body):
            item = self.item(body, "u-records")
            item["title"], item["text"] = "영국 CBAM 기록 보관 시작", "2027년 1월 1일부터 기록을 남기고 6년간 보관해야 합니다."
        self.assertEqual(self.found(change), [])
        self.assertTrue(self.found(lambda body: self.item(body, "u-records").update(title="기록 보관", text="2027년 1월 2일부터 기록을 남겨야 합니다.")))

    def test_links_must_lead_somewhere(self):
        self.assertTrue(any("해설서에 없는 절" in what for what in self.found(lambda body: self.item(body, "d-scope").update({"from": ["scope.nowhere"]}))))
        self.assertTrue(any("없는 의무 일정" in what for what in self.found(lambda body: self.item(body, "u-goods").update(duty="uk-nothing"))))
        self.assertTrue(any("사이트에 없는 주소" in what for what in self.found(lambda body: self.item(body, "d-scope")["tool"].update(href="#nowhere"))))
        self.assertTrue(any("해설서에 없는 곳" in what for what in self.found(lambda body: self.item(body, "d-scope")["tool"].update(href="#handbook-scope.nowhere"))))
        # 근거 조문은 기대는 절의 근거에 있는 것만
        self.assertTrue(any("그 절의 근거에 없음" in what for what in self.found(lambda body: self.item(body, "d-scope")["refs"].append({"act": "32023R0956", "part": "art-22"}))))
        self.assertTrue(any("기대는 글이 없음" in what for what in self.found(lambda body: self.item(body, "d-threshold").update({"from": []}))))

    def test_shape_and_wording_are_checked(self):
        self.assertTrue(any("id가 겹침" in what for what in self.found(lambda body: self.item(body, "u-goods").update(id="d-scope"))))
        self.assertTrue(any("권유나 전망" in what for what in self.found(lambda body: self.item(body, "d-records").update(text="기록을 미리 정리해 두는 것이 좋습니다."))))
        self.assertTrue(any("표기 규칙" in what for what in self.found(lambda body: self.item(body, "d-records").update(text="기록을 보관한다."))))
        self.assertTrue(any("마침표로 끝남" in what for what in self.found(lambda body: self.item(body, "d-records").update(title="기록을 보관합니다."))))
        self.assertTrue(any("note는" in what for what in self.found(lambda body: self.item(body, "o-verifier-plan").update(note="verifier"))))   # 그 일정에 그런 글이 없다
        self.assertTrue(any("함께 적을 수 없음" in what for what in self.found(lambda body: self.item(body, "o-verifier-plan").update(title="계획", text="글입니다."))))
        self.assertTrue(any("의무 일정의 역할" in what for what in self.found(lambda body: body["roles"][0].update(key="nobody"))))
        self.assertTrue(any("설명" in where for where, _ in prepare.problems({**self.body, "roles": [{**self.body["roles"][0], "about": "챙길 일이다."}] + self.body["roles"][1:]}, self.book, self.duty_body)))

    def test_the_public_shape_names_sections_and_roles(self):
        made = prepare.public(self.body, self.book, self.duty_body)
        self.assertEqual([role["name"] for role in made["roles"]], [role["name"] for role in self.duty_body["roles"]])
        self.assertTrue(all(role["about"] for role in made["roles"]))
        rows = {item["id"]: item for role in made["roles"] for group in role["groups"] for item in group["items"]}
        self.assertEqual(rows["d-holding"]["sections"], [{"href": "#handbook-cycle.surrender", "chapter": "한 해의 일정", "title": "인증서 제출과 분기말 인증서 보유의무"}])
        self.assertEqual(rows["d-holding"]["duty"], "eu-quarterly-holding")
        self.assertEqual(rows["d-holding"]["refs"], [{"act": "32023R0956", "part": "art-22", "label": "32023R0956"}])   # 규정 원문의 목록을 넘기지 않으면 문서의 번호가 이름이다
        self.assertNotIn("from", rows["d-holding"])
        # 일정에만 기대는 항목에는 그 일정의 제목과 글이 함께 실린다(화면이 의무 일정을 읽지 못했을 때 쓴다). 제목과 글을 다 적은 항목에는 없다
        plan = next(duty for duty in self.duty_body["duties"] if duty["id"] == "eu-verifier-plan")
        self.assertEqual(rows["o-verifier-plan"], {"id": "o-verifier-plan", "duty": "eu-verifier-plan", "note": "supplier",
                                                   "sections": [{"href": "#handbook-verification.accreditation", "chapter": "검증", "title": "검증기관의 인정"}],
                                                   "fallback": {"title": plan["title"], "text": plan["supplier"]}})
        self.assertEqual(rows["v-plan"]["fallback"], {"title": plan["title"], "text": plan["text"]})
        self.assertNotIn("fallback", rows["d-status"])
        self.assertEqual(rows["d-holding"]["fallback"]["title"], "분기말 인증서 보유의무 적용 시작")   # 글만 적은 항목은 제목을 일정에서 받는다


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면의 셈은 시험하지 않는다")
class PlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode:
            raise AssertionError(done.stderr[-1500:])
        cls.seen = json.loads(done.stdout)

    def test_the_address_picks_a_role_and_an_item(self):
        self.assertEqual(self.seen["places"], [{"role": "declarant", "item": ""}, {"role": "uk", "item": ""}, {"role": "uk", "item": "u-records"},
                                               {"role": "declarant", "item": ""}, {"role": "declarant", "item": "d-holding"}, {"role": "", "item": ""}])
        self.assertEqual(self.seen["hrefs"], ["#prepare", "#prepare-uk", "#prepare-declarant.a", "#prepare-uk.u-records"])

    def test_a_yearly_duty_resolves_to_its_coming_occurrence(self):
        # 지난 것 다음의 일정, 오늘이 기한이면 그날, 모두 지났으면 마지막, 한 번뿐인 일정, 이름이 비슷한 다른 일정과 섞이지 않음, 없는 일정
        # 끝의 것: 한 번뿐인 일정은 날이 지나도 이름만 비슷한 다른 일정("start-2028")으로 넘어가지 않는다
        self.assertEqual(self.seen["occurrences"], ["plan-2027", "plan", "plan-2028", "start", "planning", None, "start"])

    def test_own_words_on_a_yearly_duty_are_for_its_first_date_only(self):
        # 첫 일정까지는 항목이 적은 제목과 글, 그 일정이 지나 다음 해로 넘어가면 일정의 제목과 글(글은 첫해를 말하는데 날짜는 다음 해인 어긋남이 없게)
        self.assertEqual(self.seen["moved"], [["내 제목", "첫 계획에 관한 내 글", "plan"], ["계획 통지", "해마다 보냅니다.", "plan-2027"]])

    def test_an_item_survives_missing_duties(self):
        self.assertEqual(self.seen["spare"], [["예비 제목", "예비 글", "supplier", None, ""], ["예비 제목", "예비 글", "", None, ""]])

    def test_an_item_takes_its_own_words_first_then_the_duty(self):
        rows = {row["id"]: row for row in self.seen["rows"]}
        self.assertEqual((rows["a"]["title"], rows["a"]["text"], rows["a"]["date"], rows["a"]["noteKind"]), ("내 제목", "내 글", "2027-01-01", ""))
        self.assertEqual((rows["b"]["title"], rows["b"]["text"], rows["b"]["noteKind"], rows["b"]["duty"]), ("계획 통지", "사업자가 들어갑니다.", "supplier", "plan-2027"))
        self.assertEqual((rows["c"]["text"], rows["c"]["noteKind"]), ("해마다 보냅니다.", ""))
        self.assertEqual((rows["d"]["date"], rows["d"]["past"], rows["d"]["duty"]), ("", False, None))
        self.assertEqual((rows["e"]["date"], rows["e"]["past"]), ("2026-03-31", True))

    def test_coming_dates_are_sorted_and_one_per_duty(self):
        self.assertEqual(self.seen["soon"], ["f", "a", "b"])       # 12월 1일, 1월 1일, 11월 15일(같은 일정에 기대는 c와 지난 e, 날짜 없는 d는 뺀다)
        self.assertEqual(self.seen["soonTwo"], ["f", "a"])
        self.assertEqual((self.seen["items"], self.seen["noItems"]), (["a", "b", "c"], []))
        self.assertEqual(self.seen["progress"], [{"done": 2, "all": 6}, {"done": 0, "all": 6}])

    def test_ticks_are_kept_in_the_browser_only_and_survive_bad_storage(self):
        self.assertTrue(self.seen["wrote"])
        self.assertEqual((self.seen["saved"], self.seen["read"]), ('["a","b"]', ["a", "b"]))
        self.assertFalse(self.seen["emptied"])                      # 하나도 없으면 적어 둔 것을 지운다
        self.assertEqual(self.seen["bad"], [[], [], ["ok-1"], [], False])
        self.assertEqual(self.seen["toggled"], [["a", "b"], ["b"]])
        self.assertEqual(self.seen["cleared"], ["u-1"])             # 다른 역할의 표시는 남긴다
        self.assertEqual(self.seen["pruned"], ["a", "b"])           # 지금 목록에 없는 항목의 표시는 거른다

    def test_ticks_are_remembered_without_storage_and_other_tabs_are_not_overwritten(self):
        seen = self.seen["keeper"]
        self.assertEqual((seen["keptWrote"], seen["keptRead"]), (True, ["a", "b"]))     # 적은 뒤 다른 탭이 더한 표시도 다음에 읽힌다
        self.assertEqual((seen["bareWrote"], seen["bareRead"]), (False, ["c"]))         # 저장소가 없으면 화면을 떠날 때까지 기억한다
        self.assertEqual((seen["stuckWrote"], seen["stuckRead"]), (False, ["d"]))       # 적지 못해도 표시는 남는다
        self.assertEqual(seen["afterFailure"], ["d"])                                   # 한 번 적지 못한 뒤로는 기억해 둔 것을 쓴다


if __name__ == "__main__":
    unittest.main()

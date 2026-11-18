"""PDF 나란히 보기의 문서 안 찾기 가운데 브라우저 없이 볼 수 있는 것(site/js/pdf/find.js): 쪽의 글자 조각을 잇고, 찾을 말을 다듬고, 찾은 곳을 조각의 자리로 돌려준다."""
import json
import shutil
import subprocess
import unittest

SCRIPT = r"""
import { flatten, hits, needle } from './site/js/pdf/find.js';

const piece = (str, hasEOL = false) => ({ str, hasEOL });
const out = {};

// 한 줄의 조각들: 빈칸은 하나로, 대문자는 소문자로
const line = flatten([piece('The  Reference'), piece(' Price'), piece('', true), piece('is  published.')]);
out.line = line.text;
out.lineAt = [line.at[0], line.at[4], line.at[line.at.length - 1]];

// 줄 끝의 붙임표로 나뉜 영문 낱말은 잇고, 숫자 사이의 붙임표와 한글은 그대로 둔다
out.hyphen = flatten([piece('the imple-', true), piece('menting act')]).text;
out.range = flatten([piece('pages 12-', true), piece('15 apply')]).text;
out.korean = flatten([piece('탄소국경조정', true), piece('제도의 인증서')]).text;
out.empty = flatten([]).text;

// 찾을 말 다듬기
out.needles = [needle('  Carbon   PRICE '), needle(''), needle(null), needle('배출권  가격')];

// 찾은 곳: 조각을 넘는 말, 여러 번 나오는 말, 없는 말
const flat = flatten([piece('Carbon price paid. The carbon'), piece(' price', true), piece('is deducted.')]);
out.found = hits(flat, needle('carbon price'));
out.none = hits(flat, needle('benchmark'));
out.blank = hits(flat, '');
out.overlap = hits(flatten([piece('aaaa')]), 'aa').length;   // 겹쳐 세지 않는다
const joined = flatten([piece('the imple-', true), piece('menting act')]);
out.acrossLines = hits(joined, needle('implementing'));

console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node가 없으면 화면 모듈은 시험하지 않는다")
class PdfFindTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", SCRIPT], capture_output=True, text=True)
        if done.returncode != 0:
            raise AssertionError(done.stderr[-2000:])
        cls.out = json.loads(done.stdout)

    def test_the_pieces_of_a_page_are_joined_into_one_line_of_text(self):
        self.assertEqual(self.out["line"], "the reference price is published.")
        self.assertEqual(self.out["lineAt"], [[0, 0], [0, 5], [3, 13]])   # 글자마다 [몇째 조각, 그 조각의 몇째 글자]
        self.assertEqual(self.out["empty"], "")

    def test_a_word_broken_at_the_end_of_a_line_is_joined(self):
        self.assertEqual(self.out["hyphen"], "the implementing act")
        self.assertEqual(self.out["range"], "pages 12- 15 apply")          # 숫자 사이의 붙임표는 낱말을 나눈 것이 아니다
        self.assertEqual(self.out["korean"], "탄소국경조정 제도의 인증서")

    def test_the_query_is_put_in_the_same_form(self):
        self.assertEqual(self.out["needles"], ["carbon price", "", "", "배출권 가격"])

    def test_places_found_are_given_by_piece_and_offset(self):
        self.assertEqual(self.out["found"], [{"from": [0, 0], "to": [0, 12]}, {"from": [0, 23], "to": [1, 6]}])   # 둘째 것은 조각 둘에 걸친다
        self.assertEqual((self.out["none"], self.out["blank"], self.out["overlap"]), ([], [], 2))
        self.assertEqual(self.out["acrossLines"], [{"from": [0, 4], "to": [1, 7]}])


if __name__ == "__main__":
    unittest.main()

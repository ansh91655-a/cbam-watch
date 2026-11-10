"""출처 접속 점검 도구: 목록 화면의 걸러 보기 양식 읽기."""
import unittest

from tools.probe import forms


class FormsTest(unittest.TestCase):
    """목록 화면의 걸러 보기 양식 읽기."""

    HTML = """
    <form id="searchForm" action="/kor/article/BOARD" method="get">
      <input type="hidden" name="pageIndex" value="1">
      <select name="category"><option value="">전체</option><option value="03" selected>통상·FTA</option></select>
      <select name="rowPageC"><option value="10">10개</option><option value="50">50개</option></select>
      <input type="text" name="searchKeyword" value="">
      <input type="submit" value="검색">
    </form>
    <form action="/empty"></form>
    """

    def test_it_lists_the_fields_and_the_choices(self):
        found = forms.describe(self.HTML)
        self.assertEqual(len(found), 1)  # 칸이 없는 양식은 뺀다
        form = found[0]
        self.assertEqual((form["action"], form["method"], form["id"]), ("/kor/article/BOARD", "get", "searchForm"))
        names = [field["name"] for field in form["fields"]]
        self.assertEqual(names, ["pageIndex", "category", "rowPageC", "searchKeyword"])  # 누르는 단추는 적지 않는다
        category = form["fields"][1]
        self.assertEqual([(option["value"], option["text"], option["selected"]) for option in category["options"]], [("", "전체", False), ("03", "통상·FTA", True)])

    def test_a_page_without_forms_gives_nothing(self):
        self.assertEqual(forms.describe("<p>글</p>"), [])
        self.assertEqual(forms.describe(""), [])


class RowsTest(unittest.TestCase):
    """목록의 줄 읽기: 걸러 본 목록이 맞는지 눈으로 보는 데 쓴다."""

    def test_cells_are_joined_and_empty_rows_are_skipped(self):
        html = "<table><tr><th>번호</th><th>분류</th><th>제목</th></tr><tr><td>7</td><td>통상·FTA</td><td><a href='/x'>  안내서\n 발간 </a></td></tr><tr><td></td></tr></table>"
        self.assertEqual(forms.rows(html), ["번호 | 분류 | 제목", "7 | 통상·FTA | 안내서 발간"])

    def test_it_stops_at_the_limit(self):
        html = "".join(f"<tr><td>{n}</td></tr>" for n in range(30))
        self.assertEqual(len(forms.rows(html, limit=5)), 5)


if __name__ == "__main__":
    unittest.main()

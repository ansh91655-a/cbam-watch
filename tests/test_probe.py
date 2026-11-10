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


if __name__ == "__main__":
    unittest.main()

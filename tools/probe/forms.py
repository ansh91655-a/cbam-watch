"""목록 화면의 걸러 보기 양식을 읽는다. 게시판을 출처로 더할 때, 분류나 한 쪽에 보이는 건수를 정하는 주소를 알아내는 데 쓴다.

양식마다 보내는 곳(action)과 방식(method), 칸의 이름과 값(고르는 칸은 보기의 값과 글)을 돌려준다.
"""
from html.parser import HTMLParser

MAX_FIELDS = 40    # 양식 하나에서 적는 칸의 수
MAX_OPTIONS = 15   # 고르는 칸 하나에서 적는 보기의 수


class _Forms(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self._form = None
        self._select = None
        self._option = None

    def _field(self, row):
        if self._form is not None and len(self._form["fields"]) < MAX_FIELDS:
            self._form["fields"].append(row)
            return row
        return None

    def handle_starttag(self, tag, attrs):
        got = dict(attrs)
        if tag == "form":
            self._form = {"action": got.get("action") or "", "method": (got.get("method") or "get").lower(), "id": got.get("id") or got.get("name") or "", "fields": []}
            self.forms.append(self._form)
        elif tag == "select":
            self._select = self._field({"tag": "select", "name": got.get("name") or got.get("id") or "", "options": []})
        elif tag == "option" and self._select is not None:
            self._option = {"value": got.get("value") or "", "text": "", "selected": "selected" in got}
        elif tag == "input":
            kind = (got.get("type") or "text").lower()
            if kind not in ("submit", "button", "image", "reset"):
                self._field({"tag": "input", "type": kind, "name": got.get("name") or got.get("id") or "", "value": (got.get("value") or "")[:60]})

    def handle_data(self, data):
        if self._option is not None:
            self._option["text"] += data

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            self._option["text"] = " ".join(self._option["text"].split())[:40]
            if self._select is not None and len(self._select["options"]) < MAX_OPTIONS:
                self._select["options"].append(self._option)
            self._option = None
        elif tag == "select":
            self._select = None
        elif tag == "form":
            self._form = None


def describe(html):
    """화면에 든 양식들의 요약. 칸이 하나도 없는 양식은 뺀다."""
    reader = _Forms()
    reader.feed(html or "")
    return [form for form in reader.forms if form["fields"]]

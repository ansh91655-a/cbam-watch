"""소식의 주제 목록(data/topics.json). 사이트의 주제별 보기와 게시 관문이 같은 목록을 쓴다."""
from tools.common.jsonio import read_json

PATH = "data/topics.json"
OTHER = "etc"


def load():
    return read_json(PATH, {"topics": []}).get("topics", [])


def codes():
    return {topic["code"] for topic in load()}


def name_of(code):
    for topic in load():
        if topic["code"] == code:
            return topic["name"]
    return ""

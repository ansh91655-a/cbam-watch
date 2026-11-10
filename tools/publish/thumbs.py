"""소식에 미리보기 그림의 주소를 붙인다.

그림 파일은 site/assets/thumbs/<원문 주소의 해시>.webp다(tools/thumbs가 만든다). 같은 원문을 가리키는 소식은 같은 그림을 쓴다.
파일이 없는 소식에는 아무것도 붙이지 않는다(사이트가 주제 아이콘으로 그린 그림을 대신 보여 준다).
"""
import hashlib
import pathlib

FOLDER = pathlib.Path("site/assets/thumbs")
PUBLIC = "assets/thumbs"


def name_of(link):
    """원문 주소에서 그림 파일의 이름(확장자 없이)을 만든다."""
    return hashlib.sha1(str(link).strip().encode("utf-8")).hexdigest()[:16]


def path_of(name):
    return FOLDER / f"{name}.webp"


def attach(items):
    """그림이 있는 소식에 thumb 값을 붙인 새 목록을 돌려준다. 내린 소식에는 붙이지 않는다."""
    rows = []
    for item in items:
        link = item.get("link", "")
        name = name_of(link) if link else ""
        rows.append({**item, "thumb": f"{PUBLIC}/{name}.webp"} if name and not item.get("withdrawn") and path_of(name).exists() else item)
    return rows

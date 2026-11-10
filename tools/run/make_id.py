"""기록에 쓰는 이름을 만든다. 영문 소문자, 숫자, 하이픈만 쓴다.

쓰는 법: python -m tools.run.make_id item <출처 코드> "<제목이나 주소>"   -> 20261110-ec-news-3fa2c1
        python -m tools.run.make_id candidate <출처 코드> "<글>"           -> 12자리 16진수
"""
import hashlib
import sys

from tools.common.jsonio import now_kst


def candidate_id(source_code, text):
    return hashlib.sha1(f"{source_code}|{text}".encode("utf-8")).hexdigest()[:12]


def item_id(source_code, text, moment=None):
    day = (moment or now_kst()).strftime("%Y%m%d")
    return f"{day}-{source_code}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:6]}"


if __name__ == "__main__":
    kind, code, text = sys.argv[1], sys.argv[2], sys.argv[3]
    print(item_id(code, text) if kind == "item" else candidate_id(code, text))

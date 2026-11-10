"""정리 실행이 직접 여는 출처에서 '이미 본 것'을 가려낸다.

데이터베이스의 claudeseen 컬렉션(파일로 받아 둔 것)과 이번에 읽은 항목 목록을 견줘 새 항목만 알려 준다.
쓰는 법: python -m tools.run.seen --db-dir /tmp/run/db --code council-cbam --entries-file /tmp/run/council-cbam.txt --out-dir /tmp/run/out
- 항목 파일은 한 줄에 하나, "제목 | 날짜 | 주소" 꼴이다(날짜와 주소는 비워도 된다).
- 그 출처를 처음 보는 것이면 기준선만 만들고 새 항목은 없다고 답한다.
- 새로 본 항목은 <out-dir>/claudeseen/<id>.json 으로 써 둔다. 실행이 이 파일들을 데이터베이스에 올린다.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

from tools.common.jsonio import stamp, write_json
from tools.run import dbdump


def _key(code, title):
    plain = re.sub(r"[^0-9a-z가-힣]+", "", title.lower())
    return f"{code}-{hashlib.sha1(plain.encode('utf-8')).hexdigest()[:12]}"


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--entries-file", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    known = dbdump.ids(args.db_dir, "claudeseen")
    first_time = not any(doc_id.startswith(args.code + "-") for doc_id in known)
    fresh = []
    for line in pathlib.Path(args.entries_file).read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split("|")]
        if not parts or len(parts[0]) < 6:
            continue
        title, date, url = parts[0], (parts[1] if len(parts) > 1 else ""), (parts[2] if len(parts) > 2 else "")
        doc_id = _key(args.code, title)
        if doc_id in known:
            continue
        known.add(doc_id)
        write_json(pathlib.Path(args.out_dir) / "claudeseen" / f"{doc_id}.json", {"id": doc_id, "code": args.code, "title": title[:300], "date": date, "url": url, "at": stamp(), "baseline": first_time})
        if not first_time:
            fresh.append({"id": doc_id, "source": args.code, "kind": "claude", "text": title[:300], "date": date, "url": url})
    print(json.dumps({"code": args.code, "baseline": first_time, "new": fresh}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

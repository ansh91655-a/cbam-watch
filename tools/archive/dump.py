"""소급 수집의 준비 단계. 목록 화면을 받아 글, 표, 링크와 화면의 원래 내용을 그대로 적어 둔다.

화면의 짜임(목록의 꼴, 쪽 넘김 주소)을 보고 뽑는 규칙을 정하려는 것이다. 결과는 _dump/ 아래에 쓰고,
워크플로가 archive-probe 가지에 올린다(main에는 올리지 않는다).
쓰는 법: python -m tools.archive.dump [대상 파일]   대상 파일의 기본값은 tools/archive/probe_targets.json
"""
import json
import pathlib
import sys
import time

from tools.common.htmltext import decode, parse
from tools.common.net import fetch, header

OUT = pathlib.Path("_dump")
RAW_LIMIT = 1_500_000


def expand(target):
    """대상 하나가 가리키는 주소들을 (이름, 주소)로 편다."""
    if target.get("template"):
        return [(f"p{n}", target["template"].format(n=n)) for n in target.get("pages", [0])]
    return [(f"u{index}", url) for index, url in enumerate(target.get("urls", []))]


def grab(code, name, url, extra):
    status, headers, body, error = fetch(url, headers=extra or {})
    content_type = header(headers, "Content-Type")
    row = {"code": code, "name": name, "url": url, "status": status, "contentType": content_type, "bytes": len(body), "error": error[:200]}
    folder = OUT / code
    folder.mkdir(parents=True, exist_ok=True)
    if body:
        is_json = "json" in content_type.lower()
        (folder / f"{name}.{'json' if is_json else 'html'}").write_bytes(body[:RAW_LIMIT])
        if not is_json:
            links, lines, rows = parse(decode(body, content_type), url)
            row.update({"links": len(links), "lines": len(lines), "rows": len(rows)})
            (folder / f"{name}.parsed.json").write_text(
                json.dumps({"url": url, "lines": lines, "rows": rows, "links": links}, ensure_ascii=False, indent=1), encoding="utf-8")
    return row


def main(argv):
    targets = json.loads(pathlib.Path(argv[0] if argv else "tools/archive/probe_targets.json").read_text(encoding="utf-8"))["targets"]
    rows = []
    for target in targets:
        for name, url in expand(target):
            rows.append(grab(target["code"], name, url, target.get("headers")))
            print(rows[-1]["code"], name, rows[-1]["status"], rows[-1]["bytes"], rows[-1]["error"])
            time.sleep(1.5)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

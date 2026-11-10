"""공개 사이트 폴더(_site)를 만든다: 화면 파일, 게시 데이터, 수집 결과에서 만든 데이터.

저장소 맨 위에서 `python -m tools.publish.build_site [출력 폴더]`로 돌린다. 데이터 파일이 깨져 있으면 0이 아닌 값으로 끝난다.
"""
import json
import pathlib
import shutil
import sys

from tools.common.jsonio import read_json, write_json
from tools.publish import derive

DATA_FILES = ["items", "events", "digests", "terms", "topics", "prices"]
LIST_KEY = {"items": "items", "events": "events", "digests": "digests", "terms": "terms", "topics": "topics", "prices": "prices"}


def main(argv):
    out = pathlib.Path(argv[0] if argv else "_site")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree("site", out, ignore=shutil.ignore_patterns("site.config.json"))
    data_out = out / "data"
    data_out.mkdir(parents=True, exist_ok=True)

    counts, problems, bodies = {}, [], {}
    for name in DATA_FILES:
        source = pathlib.Path(f"data/{name}.json")
        body = read_json(source, None) if source.exists() else {LIST_KEY[name]: []}
        if body is None or not isinstance(body.get(LIST_KEY[name]), list):
            problems.append(f"data/{name}.json 을 읽지 못함")
            body = {LIST_KEY[name]: []}
        counts[name] = len(body[LIST_KEY[name]])
        bodies[name] = body
    # 일정에는 가격표에 적힌 게시일을 더한다(가격표가 바뀌면 일정도 따라 바뀐다)
    bodies["events"] = {**bodies["events"], "events": derive.events(bodies["events"]["events"], bodies["prices"])}
    counts["events"] = len(bodies["events"]["events"])
    for name, body in bodies.items():
        write_json(data_out / f"{name}.json", body)

    documents, diffs = derive.documents()
    counts.update({"documents": len(documents["documents"])})
    write_json(data_out / "documents.json", documents)
    for diff_path in diffs:
        source = pathlib.Path(diff_path)
        if source.exists():
            target = data_out / "diffs" / diff_path.split("originals/diffs/", 1)[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    write_json(data_out / "site.json", derive.site(counts))
    (out / ".nojekyll").write_text("", encoding="utf-8")

    for path in data_out.rglob("*.json"):  # 만든 파일이 모두 JSON으로 풀리는지 확인
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            problems.append(f"{path}: {error}")
    print("사이트 폴더:", out, counts)
    for problem in problems:
        print("문제:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""공개 사이트 폴더(_site)를 만든다: 화면 파일, 게시 데이터, 수집 결과에서 만든 데이터.

저장소 맨 위에서 `python -m tools.publish.build_site [출력 폴더]`로 돌린다. 데이터 파일이 깨져 있으면 0이 아닌 값으로 끝난다.
"""
import json
import pathlib
import shutil
import sys

from tools.check import term_check
from tools.common.jsonio import read_json, today, write_json
from tools.laws import build as laws
from tools.pdfko import site as pdf_site
from tools.publish import calc, crossrefs, derive, duties, factor, feed, gloss, handbook, item_sheet, merge, preload, regulations, sectors, thumbs

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
    # 규제별 진행 상황: 연혁의 근거를 다시 맞춰 보고, 안에서만 쓰는 값을 뺀 뒤 관련 소식을 붙여 싣는다
    rules = read_json("data/regulations.json", None)
    if rules is None:
        problems.append("data/regulations.json 을 읽지 못함")
        rules = {"groups": [], "regulations": []}
    problems += [f"규제 자료: {where}: {what}" for where, what in regulations.problems(rules, kinds=("format",))]
    for where, what in regulations.problems(rules, kinds=("evidence",)):  # 근거가 달라진 것은 알리기만 한다
        print(f"규제 자료 점검: {where}: {what}")
    write_json(data_out / "regulations.json", regulations.public(rules, bodies["items"]["items"]))
    counts["regulations"] = len(rules.get("regulations", []))

    # 일정에는 가격표에 적힌 게시일과 규제의 다음 일정을 더한다(가격표나 규제 자료가 바뀌면 일정도 따라 바뀐다)
    bodies["events"] = {**bodies["events"], "events": derive.events(bodies["events"]["events"], bodies["prices"], rules)}
    # 실무 달력(법령에 날짜가 적힌 의무)을 일정에 더한다. 같은 일을 가리키는 게시 데이터의 일정은 의무 쪽을 남긴다.
    # 꼴이 깨졌으면 멈추고, 법령 글과 달라진 것은 알리기만 한다
    duty_book = read_json(duties.SOURCE, None)
    duty_found = duties.problems(duty_book)
    duty_broken = [row for row in duty_found if not row[1].startswith("근거 어긋남")]
    problems += [f"실무 달력: {where}: {what}" for where, what in duty_broken]
    for where, what in duty_found:
        if what.startswith("근거 어긋남"):
            print(f"알림: 실무 달력: {where}: {what}")
    if not duty_broken:
        kept = [event for event in bodies["events"]["events"] if not duties.superseded(event, duty_book)]
        bodies["events"] = {**bodies["events"], "events": sorted(kept + duties.events(duty_book), key=lambda row: (str(row.get("date", "")), str(row.get("title", ""))))}
        write_json(data_out / "duties.json", duties.public(duty_book))
    counts["events"] = len(bodies["events"]["events"])
    # 미리보기 그림이 있는 소식에는 그림의 주소를 붙인다
    bodies["items"] = {**bodies["items"], "items": thumbs.attach(bodies["items"]["items"])}
    for name, body in bodies.items():  # 소식은 안에서만 쓰는 값(출처의 안쪽 이름 등)을 빼고 싣는다. 뒤의 단계들은 빼지 않은 자료를 쓴다
        write_json(data_out / f"{name}.json", derive.public_items(body) if name == "items" else body)
    # 하나로 묶은 소식의 옛 번호가 어디로 갔는지(옛 주소로 온 사람을 남긴 소식으로 넘긴다)
    records = read_json(merge.MERGED, {"merged": []}).get("merged", [])
    write_json(data_out / "moved.json", {"moved": merge.moved(records, {item["id"] for item in bodies["items"]["items"]})})

    # CBAM 계수(그림과 비용 추정이 쓴다). 꼴이 깨졌으면 멈추고, 법령 글과 달라진 것은 알리기만 한다
    book = read_json(factor.SOURCE, None)
    drift = [row for row in factor.problems(book) if row[1].startswith("근거 어긋남")]
    broken = [row for row in factor.problems(book) if not row[1].startswith("근거 어긋남")]
    problems += [f"CBAM 계수: {where}: {what}" for where, what in broken]
    for where, what in drift:
        print(f"알림: CBAM 계수: {where}: {what}")
    if not broken:
        write_json(data_out / "factor.json", factor.public(book))

    # 인증서 비용 추정의 자료(법령의 표에서 만든 품목별 벤치마크와 기본값). 꼴이 깨졌으면 멈추고, 받아 둔 글과 달라진 것은 알리기만 한다
    terms, goods = read_json(calc.SOURCE, None), read_json(calc.GOODS, None)
    calc_found = calc.problems(terms, goods)
    problems += [f"비용 추정: {where}: {what}" for where, what in calc.blocking(calc_found)]
    for where, what in calc_found:
        if what.startswith(calc.DRIFT):
            print(f"알림: 비용 추정: {where}: {what}")
    if not calc.blocking(calc_found):
        (data_out / "calc.json").write_text(calc.dump(calc.public(terms, goods)), encoding="utf-8")
        counts["calc"] = len(goods["goods"])

    codes = read_json("data/cn.json", None)  # 품목 코드 조회의 목록(법령 원문에서 뽑은 것)
    if codes is None or not codes.get("current"):
        problems.append("data/cn.json 을 읽지 못함")
    else:
        write_json(data_out / "cn.json", codes)
        counts["cn"] = len(codes["current"])

    # 규정 원문과 국문 번역, 전체 규정 검색에 쓰는 글(받아 둔 법령의 글에서 만든다)
    counts["laws"] = laws.write(data_out)
    counts["pdfs"] = pdf_site.write(out)  # 원문과 같은 자리에 번역을 앉힌 국문 PDF(도구가 없는 환경에서는 싣지 않는다)
    # CBAM 해설서: 꼴이 깨졌으면 멈추고, 근거로 적은 대목이 규정 원문이나 받아 둔 글과 달라진 것은 알리기만 한다
    guide = read_json(handbook.SOURCE, None)
    guide_found = handbook.problems(guide, term_check.load(), data_out / "laws", rules={rule.get("id") for rule in rules.get("regulations", [])}) if guide else [("해설서", "data/handbook.json 을 읽지 못함")]
    problems += [f"해설서: {where}: {what}" for where, what in handbook.blocking(guide_found)]
    for where, what in guide_found:
        if what.startswith(handbook.DRIFT):
            print(f"알림: 해설서: {where}: {what}")
    if guide and not handbook.blocking(guide_found):
        write_json(data_out / "handbook.json", handbook.public(guide, handbook.known_laws(read_json(data_out / "laws" / "index.json", None))))
        counts["handbook"] = sum(len(chapter.get("sections", [])) for chapter in guide.get("chapters", []))
    # 소식, 의무 일정, 용어집에 적힌 법령과 조문을 규정 원문으로 잇는다(글에 또렷이 적힌 곳만). 근거 칸에 적힌 조각이 글에 없으면 알리기만 한다
    linked, unlinked = crossrefs.write(data_out, bodies["items"]["items"], read_json(data_out / "duties.json", {}).get("duties", []),
                                       bodies["terms"].get("terms", []), today())
    # 부문별 모아 보기: 부문마다 대상 품목, 안내 문서, 기본값·벤치마크, 소식을 모은다(무엇을 모을지는 sources/sectors.json)
    counts["sectors"], sector_problems = sectors.write(data_out, bodies["items"]["items"])
    problems += [f"부문별 모아 보기: {where}: {what}" for where, what in sector_problems]
    # 글 속 용어 풀이: 소식, 규제, 해설서의 글에서 표시할 용어와 풀이(해설서가 풀이한 용어와 용어집의 약어. 무엇을 빼는지는 sources/gloss.json)
    counts["gloss"], gloss_problems = gloss.write(data_out, bodies["terms"], read_json(data_out / "handbook.json", {}))
    problems += [f"글 속 용어 풀이: {where}: {what}" for where, what in gloss_problems]
    # 품목 한 장 보기가 품목마다 잇는 근거 조문과 해설서의 절(무엇을 이을지는 sources/item-sheet.json)
    counts["sheet"], sheet_problems = item_sheet.write(data_out)
    problems += [f"품목 한 장 보기: {where}: {what}" for where, what in sheet_problems]
    print("규정 원문으로 이은 것:", linked)
    for where, what in unlinked:
        print(f"알림: 조문 잇기: {where}: {what}")

    documents, diffs = derive.documents()
    counts.update({"documents": len(documents["documents"])})
    write_json(data_out / "documents.json", documents)
    for diff_path in diffs:
        source = pathlib.Path(diff_path)
        if source.exists():
            target = data_out / "diffs" / diff_path.split("originals/diffs/", 1)[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for source, target in derive.stored_files():  # 문서 사본(원문 대장이 화면에서 보여 주고 내려받게 하는 파일)
        if pathlib.Path(source).exists():
            (out / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, out / target)
    config = derive.site(counts, rules, bodies["events"]["events"], bodies["items"]["items"], bodies["topics"].get("topics", []),
                         guide if counts.get("handbook") else None)
    write_json(data_out / "site.json", config)
    if feed.wanted(config):  # 구독 피드(새 소식 받아 보기를 열어 둔 동안에만 만든다)
        (out / "feed.xml").write_text(feed.news(bodies["items"]["items"], bodies["topics"].get("topics", []), config["url"], config["builtAt"]), encoding="utf-8")
        (out / "rules.xml").write_text(feed.rules(rules, config["url"], config["builtAt"]), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    # 화면 모듈을 한꺼번에 받게 하는 줄을 index.html에 넣는다(처음 여는 사람의 첫 화면이 빨리 뜬다). 넣지 못해도 사이트는 그대로 돌아가므로 알리기만 한다
    preloaded, why = preload.inject(out)
    print(f"알림: 화면 모듈 미리 받기: {why}" if why else f"한꺼번에 받게 한 화면 모듈: {preloaded}")

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

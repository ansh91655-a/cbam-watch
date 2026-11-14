"""부문별 모아 보기(#sector-<부문>)의 자료를 만든다: 부문마다 대상 품목, 안내 문서, 기본값·벤치마크, 소식을 한곳에 모은다.

- 무엇을 모을지는 sources/sectors.json이 정한다. 수와 글은 모두 사이트의 자료에서 만든다(손으로 적은 사실이 없다):
  대상 품목과 온실가스, 산정 범위는 품목 코드 조회의 목록(cn.json: CBAM 규정 부속서 I·II에서 만든 것),
  기본값·벤치마크가 정해진 품목 수와 마크업은 인증서 비용 추정의 자료(calc.json), 문서의 이름과 차례는 규정 원문의 목록(laws/index.json),
  소식은 게시한 소식 가운데 제목·요약·다룬 내용에 그 부문의 낱말이 나온 것이다(그 낱말이 든 다른 말은 except에 적어 세지 않는다: 수소의 '탄화수소').
- 만드는 것: data/sectors.json
  {"sectors": [{"key", "name", "cn": [품목 목록의 부문 이름], "goods": {"rows", "gases", "directOnly", "both"}, "proposed": {"own", "combined", "name"} 또는 없음,
                "docs": [{"id", "name", "group", "pages", "pdf", "sections"}], "calc": {"goods", "first", "markups"} 또는 없음,
                "items": [{"id", "title", "date"}], "itemCount"}],
   "common": [{"id", "name", "group"}], "law": 품목 목록의 근거, "asOf": 품목 목록을 만든 날}

쓰는 법: python -m tools.publish.sectors <사이트 폴더의 data>   (사이트 만들기가 부른다. 따로 돌리면 부문마다의 수와 문제를 찍는다)
"""
import pathlib
import sys

from tools.common.jsonio import read_json, write_json

SOURCE = "sources/sectors.json"
ITEMS = 6          # 부문마다 싣는 소식의 수(새 것부터)
SECTIONS = 8       # 문서마다 싣는 큰 절의 수
ITEM_FIELDS = ("title", "summary")


def problems(book, data_out):
    """[(자리, 문제)]. 자료가 가리키는 부문과 문서가 사이트의 자료에 있는지 본다."""
    if not isinstance(book, dict) or not isinstance(book.get("sectors"), list) or not book["sectors"]:
        return [("부문별 모아 보기", f"자료({SOURCE})를 읽지 못함")]
    data_out = pathlib.Path(data_out)
    acts = {act["id"] for act in read_json(data_out / "laws" / "index.json", {}).get("acts", [])}
    cn = read_json(data_out / "cn.json", {})
    cn_sectors = {row.get("sector") for row in cn.get("current", [])}
    proposed_sectors = {row.get("sector") for row in cn.get("proposed", [])}
    calc_sectors = {good[2] for good in read_json(data_out / "calc.json", {}).get("goods", [])}
    found = []
    keys = [sector.get("key") for sector in book["sectors"]]
    if len(set(keys)) != len(keys):
        found.append(("부문별 모아 보기", "부문의 key가 겹침"))
    for sector in book["sectors"]:
        where = f"부문 {sector.get('key', '?')}"
        if not str(sector.get("name", "")).strip() or not sector.get("words"):
            found.append((where, "name이나 words가 비어 있음"))
        missing = [name for name in sector.get("cn", []) if name not in cn_sectors]
        if missing or not sector.get("cn"):
            found.append((where, f"품목 목록에 없는 부문: {missing or '(없음)'}"))
        if sector.get("calc") and sector["calc"] not in calc_sectors:
            found.append((where, f"인증서 비용 추정의 자료에 없는 부문: {sector['calc']}"))
        found += [(where, f"규정 원문에 없는 문서: {doc}") for doc in sector.get("docs", []) if doc not in acts]
        found += [(where, f"개정안의 품목 목록에 없는 부문: {name}") for name in sector.get("proposed", []) if name not in proposed_sectors]
    found += [("부문별 모아 보기", f"규정 원문에 없는 문서(common): {doc}") for doc in book.get("common", []) if doc not in acts]
    return found


def _goods(sector, cn, calc_codes):
    rows = [row for row in cn.get("current", []) if row.get("sector") in sector["cn"]]
    gases = [gas for gas in ("co2", "n2o", "pfc") if any(gas in row.get("gases", []) for row in rows)]

    def priced(row):
        """이 줄의 코드로 시작하는 품목 가운데 기본값·벤치마크가 정해진 첫 품목의 코드(비용 추정으로 잇는다)."""
        return next((code for code in calc_codes if any(code.startswith(prefix) for prefix in row.get("codes", []))), "")

    return {"rows": [{"shown": row["shown"], "text": row["text"], "ex": bool(row.get("ex")), "gases": row.get("gases", []), "directOnly": bool(row.get("directOnly")),
                      "codes": row.get("codes", []), "calc": priced(row)} for row in rows],
            "gases": gases, "directOnly": sum(1 for row in rows if row.get("directOnly")), "both": sum(1 for row in rows if not row.get("directOnly"))}


def _proposed(sector, cn):
    rows = cn.get("proposed", [])
    own = sum(1 for row in rows if row.get("sector") in sector.get("proposed", []) and row.get("sector") != "combined")
    combined = sum(1 for row in rows if row.get("sector") == "combined") if "combined" in sector.get("proposed", []) else 0
    if not own + combined or cn.get("proposalEnacted"):
        return None
    return {"own": own, "combined": combined, "name": (cn.get("proposal") or {}).get("name", "")}


def _doc(act, pdfs):
    sections = [{"id": part["id"], "ko": part.get("ko", ""), "titleKo": part.get("titleKo", ""), "title": part.get("title", "")}
                for part in act.get("toc", []) if part.get("kind") == "section" and part.get("level", 0) <= 1 and (part.get("titleKo") or part.get("title"))]
    return {"id": act["id"], "name": act.get("name", act["id"]), "group": act.get("group", "act"), "official": act.get("official", ""), "pages": act.get("pages", 0),
            "received": act.get("received", ""), "remark": act.get("remark", ""), "pdf": act["id"] in pdfs, "sections": sections[:SECTIONS], "more": max(0, len(sections) - SECTIONS)}


def _calc(sector, calc):
    if not sector.get("calc"):
        return None
    codes = [good[0] for good in calc.get("goods", []) if good[2] == sector["calc"]]
    group = next((one for one in calc.get("markups", []) if sector["calc"] in one.get("sectors", [])), None)
    return {"goods": len(codes), "first": codes[0] if codes else "", "markups": (group or {}).get("values", {})} if codes else None


def _items(sector, items):
    words = [str(word) for word in sector.get("words", [])]
    others = [str(word) for word in sector.get("except", [])]   # 그 낱말이 든 다른 말(수소의 '탄화수소'). 글에서 지우고 찾는다
    hits = []
    for item in items or []:
        if item.get("withdrawn"):
            continue
        text = " ".join([str(item.get(field, "")) for field in ITEM_FIELDS] + [str(topic) for topic in item.get("topics", [])])
        for other in others:
            text = text.replace(other, " ")
        if any(word in text for word in words):
            hits.append(item)
    hits.sort(key=lambda item: str(item.get("published", "")), reverse=True)
    rows = []
    for item in hits[:ITEMS]:
        row = {"id": item["id"], "title": item.get("title", ""), "date": item.get("published", "")}
        if item.get("brief"):   # 제목만 실은 소식은 요약 화면이 없다. 원문으로 바로 간다
            row["link"] = item.get("link", "")
        rows.append(row)
    return rows, len(hits)


def build(book, data_out, items):
    """sectors.json의 내용. book은 sources/sectors.json의 내용이다."""
    data_out = pathlib.Path(data_out)
    acts = {act["id"]: act for act in read_json(data_out / "laws" / "index.json", {}).get("acts", [])}
    pdfs = read_json(data_out / "laws" / "pdf.json", {}).get("docs", {})
    cn = read_json(data_out / "cn.json", {})
    calc = read_json(data_out / "calc.json", {})
    calc_codes = [good[0] for good in calc.get("goods", [])]
    sectors = []
    for sector in book["sectors"]:
        found, total = _items(sector, items)
        sectors.append({"key": sector["key"], "name": sector["name"], "cn": sector["cn"], "words": sector.get("words", []), "goods": _goods(sector, cn, calc_codes), "proposed": _proposed(sector, cn),
                        "docs": [_doc(acts[doc], pdfs) for doc in sector.get("docs", []) if doc in acts], "calc": _calc(sector, calc),
                        "items": found, "itemCount": total})
    common = [{"id": doc, "name": acts[doc].get("name", doc), "group": acts[doc].get("group", "act")} for doc in book.get("common", []) if doc in acts]
    return {"asOf": cn.get("asOf", ""), "law": cn.get("law") or {}, "common": common, "sectors": sectors}


def write(data_out, items):
    """data/sectors.json을 쓰고 (부문 수, 문제)를 돌려준다. 문제가 있으면 쓰지 않는다. 품목 목록과 규정 원문의 목록이 먼저 만들어져 있어야 한다."""
    book = read_json(SOURCE, None)
    found = problems(book, data_out)
    if found:
        return 0, found
    body = build(book, data_out, items)
    write_json(pathlib.Path(data_out) / "sectors.json", body)
    return len(body["sectors"]), []


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    data_out = pathlib.Path(argv[0])
    count, found = write(data_out, read_json(data_out / "items.json", {}).get("items", []))
    for sector in read_json(data_out / "sectors.json", {}).get("sectors", []) if count else []:
        priced = (sector["calc"] or {}).get("goods", 0)
        print(f"{sector['name']}: 품목 {len(sector['goods']['rows'])}줄, 문서 {len(sector['docs'])}건, 기본값·벤치마크 {priced}품목, 소식 {sector['itemCount']}건")
    print(f"부문별 모아 보기: 부문 {count}개, 문제 {len(found)}건")
    for where, problem in found:
        print(f"- {where}: {problem}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

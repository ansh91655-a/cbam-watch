"""본문 받기를 글 하나에 시험해 본다. 저장하지 않고 본 것만 찍는다.

출처를 본문 받기에 넣기 전에(또는 받지 못한 까닭을 알아볼 때) 자동 실행 환경에서 그 화면이 어떻게 읽히는지 보려는 것이다:
이용 조건이 어디에서 찾아지는지, 화면이 저작권을 어떻게 적었는지, 본문이 어디서 시작해 어디서 끝나는지.

쓰는 법:
  python -m tools.collect.articles_try <출처 코드>=<글 주소> [...] [--license "<글귀>"] [--terms-url <주소>] [--stop "<끝 표시>"] [--dump body|page]
- 출처 코드는 출처 대장에 있는 것이어야 한다(수집을 꺼 둔 출처도 된다).
- 글 주소 자리에 first:<건수>@<주소에 든 글자>를 적으면 그 출처의 목록 화면에서 그런 주소의 링크를 앞에서부터 골라 시험한다
  (예: moj=first:2@artclView.do). 목록에 어떤 글이 있는지 모를 때 쓴다.
- --license, --terms-url, --stop을 주면 대장의 articles 대신 그 값으로 시험한다(대장에 아직 적지 않은 출처를 알아볼 때 쓴다).
- --dump body는 본문으로 고른 줄을 모두 찍는다(끝 표시를 정할 때 쓴다). --dump page는 화면의 줄과 링크를 모두 찍는다
  (저작권 안내 화면처럼 글이 아닌 화면을 읽거나, 목록 화면에서 글 주소의 꼴을 알아볼 때 쓴다). 줄은 110자까지만 찍는다.
글의 제목은 그 출처의 목록 화면에서 그 주소로 가는 링크의 글자로 삼는다(수집 프로그램이 제목으로 적는 글자다).
워크플로 '본문 받기 시험'이 이 프로그램을 돌린다.
"""
import argparse
import json
import re
import sys
from urllib.parse import urlsplit

from tools.collect import article_terms, article_text, articles, registry
from tools.common.net import fetch

CUT = 80
DUMP_CUT = 110
PICK = re.compile(r"^first:(\d+)@(.+)$")
NOT_PICKED = "목록 화면에서 그런 주소의 링크를 찾지 못함"
# 이용 조건을 적어 둔 화면으로 가는 링크를 알아보는 낱말(띄어쓰기를 빼고 소문자로 견준다)
TERMS_LINK_WORDS = ("저작권", "이용안내", "copyright", "licence", "license", "impressum", "legalnotice", "disclaimer", "termsandconditions",
                    "termsofuse", "re-use", "reuse")


def _same_page(left, right):
    """두 주소가 같은 화면인가. 끝의 빗금과 물음표 뒤는 견주지 않는다."""
    a, b = urlsplit(left), urlsplit(right)
    return (a.netloc, a.path.rstrip("/")) == (b.netloc, b.path.rstrip("/"))


def board_links(source, fetcher=fetch):
    """그 출처의 목록 화면에 있는 (주소, 글자) 쌍들. 받지 못하면 빈 목록이다."""
    board, _ = articles.read_page(source["url"], fetcher)
    return (board or {}).get("links", [])


def title_of(links, url):
    """목록 화면에서 이 글로 가는 링크의 글자. 없으면 빈 글."""
    for address, text in links:
        if address == url or _same_page(address, url):
            return text
    return ""


def picked(source, links, count, part):
    """목록 화면의 링크 가운데 주소에 part가 든 글의 주소를 앞에서부터 count건 고른다(같은 사이트의 화면만, 첨부 파일은 빼고)."""
    found = []
    for address, _ in links:
        if part in address and articles.same_site(address, source) and not articles.is_file(address) and address not in found:
            found.append(address)
    return found[:count]


def terms_links(links, limit=6):
    """이용 조건을 적어 둔 화면으로 보이는 링크의 (글자, 주소)들."""
    found = []
    for address, text in links:
        squeezed = article_text.flat(text).lower()
        if any(word in squeezed for word in TERMS_LINK_WORDS) and [text[:30], address] not in found:
            found.append([text[:30], address])
    return found[:limit]


def look(source, url, title, fetcher=fetch, dump=""):
    """글 하나를 받아 본 것을 값으로 돌려준다. dump가 "body"면 본문의 줄을, "page"면 화면의 줄과 링크를 모두 싣는다."""
    seen = {"code": source["code"], "url": url, "rules": articles.rules_of(source)}
    page, why = articles.read_page(url, fetcher)
    if page is None:
        return dict(seen, opened=False, why=why)
    shown, why = articles.terms(source, page, fetcher, {})
    rules = articles.rules_of(source)
    kept, found, cut = article_text.body(page["lines"], title, list(rules.get("stop", [])) + list(rules.get("license", [])))
    result = dict(
        seen, opened=True, pageLines=len(page["lines"]), title=title, titleFound=found, terms=shown, why=why,
        fieldValues=article_terms.field_values(page["lines"], (rules.get("field") or {}).get("label", "")) if rules.get("field") else [],
        hints=article_terms.hints(page["lines"] + page["alts"], limit=8), termsLinks=terms_links(page["links"]),
        bodyLines=len(kept), bodyChars=sum(len(line) for line in kept), cut=cut, longEnough=article_text.long_enough(kept),
        head=[line[:CUT] for line in kept[:10]], tail=[line[:CUT] for line in kept[-4:]],
        pageTail=[line[:CUT] for line in page["lines"][-12:]],
    )
    if dump == "body":
        result["body"] = [line[:DUMP_CUT] for line in kept]
    if dump == "page":
        result["page"] = [line[:DUMP_CUT] for line in page["lines"]]
        result["links"] = [[text[:40], address] for address, text in page["links"]]
    return result


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+", help="<출처 코드>=<글 주소> 또는 <출처 코드>=first:<건수>@<주소에 든 글자>")
    parser.add_argument("--license", action="append", default=[])
    parser.add_argument("--terms-url", default="")
    parser.add_argument("--stop", action="append", default=[])
    parser.add_argument("--dump", choices=["", "body", "page"], default="")
    args = parser.parse_args(argv)
    by_code = {source["code"]: source for source in registry.load()[0]}
    boards = {}
    for target in args.targets:
        code, _, url = target.partition("=")
        source = by_code.get(code)
        if not source or not url:
            print(json.dumps({"code": code, "url": url, "why": "출처 대장에 없는 코드이거나 주소가 비어 있음"}, ensure_ascii=False))
            continue
        if args.license or args.terms_url or args.stop:
            rules = dict(articles.rules_of(source))
            if args.license:
                rules["license"] = args.license
            if args.terms_url:
                rules["termsUrl"] = args.terms_url
            if args.stop:
                rules["stop"] = args.stop
            source = dict(source, articles=rules)
        if code not in boards:
            boards[code] = board_links(source)
        pick = PICK.match(url)
        urls = picked(source, boards[code], int(pick.group(1)), pick.group(2)) if pick else [url]
        if not urls:
            print(json.dumps({"code": code, "url": url, "why": NOT_PICKED, "boardLinks": len(boards[code])}, ensure_ascii=False))
        for address in urls:
            print(json.dumps(look(source, address, title_of(boards[code], address), dump=args.dump), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

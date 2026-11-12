"""본문 받기를 글 하나에 시험해 본다. 저장하지 않고 본 것만 찍는다.

출처를 본문 받기에 넣기 전에(또는 받지 못한 까닭을 알아볼 때) 자동 실행 환경에서 그 화면이 어떻게 읽히는지 보려는 것이다:
이용 조건이 어디에서 찾아지는지, 화면이 저작권을 어떻게 적었는지, 본문이 어디서 시작해 어디서 끝나는지.

쓰는 법:
  python -m tools.collect.articles_try <출처 코드>=<글 주소> [...] [--license "<글귀>"] [--terms-url <주소>] [--stop "<끝 표시>"]
출처 코드는 출처 대장에 있는 것이어야 한다. --license, --terms-url, --stop을 주면 대장의 articles 대신 그 값으로 시험한다
(대장에 아직 적지 않은 출처를 알아볼 때 쓴다). 글의 제목은 그 출처의 목록 화면에서 그 주소로 가는 링크의 글자로 삼는다.
워크플로 '출처 접속 점검'을 손으로 돌릴 때 articles 칸에 "<출처 코드>=<글 주소>"를 띄어 적으면 이 프로그램이 돈다.
"""
import argparse
import json
import sys
from urllib.parse import urlsplit

from tools.collect import article_terms, article_text, articles, registry
from tools.common.net import fetch

CUT = 80


def _same_page(left, right):
    """두 주소가 같은 화면인가. 끝의 빗금과 물음표 뒤는 견주지 않는다."""
    a, b = urlsplit(left), urlsplit(right)
    return (a.netloc, a.path.rstrip("/")) == (b.netloc, b.path.rstrip("/"))


def title_from_board(source, url, fetcher=fetch):
    """그 출처의 목록 화면에서 이 글로 가는 링크의 글자(수집 프로그램이 제목으로 적는 글자). 없으면 빈 글."""
    board, _ = articles.read_page(source["url"], fetcher)
    for address, text in (board or {}).get("links", []):
        if address == url or _same_page(address, url):
            return text
    return ""


def look(source, url, fetcher=fetch):
    """글 하나를 받아 본 것을 값으로 돌려준다."""
    seen = {"code": source["code"], "url": url, "rules": articles.rules_of(source)}
    page, why = articles.read_page(url, fetcher)
    if page is None:
        return dict(seen, opened=False, why=why)
    title = title_from_board(source, url, fetcher)
    shown, why = articles.terms(source, page, fetcher, {})
    rules = articles.rules_of(source)
    kept, found = article_text.body(page["lines"], title, list(rules.get("stop", [])) + list(rules.get("license", [])))
    return dict(
        seen, opened=True, pageLines=len(page["lines"]), title=title, titleFound=found, terms=shown, why=why,
        fieldValues=article_terms.field_values(page["lines"], (rules.get("field") or {}).get("label", "")) if rules.get("field") else [],
        hints=article_terms.hints(page["lines"] + page["alts"], limit=8),
        bodyLines=len(kept), bodyChars=sum(len(line) for line in kept), longEnough=article_text.long_enough(kept),
        head=[line[:CUT] for line in kept[:10]], tail=[line[:CUT] for line in kept[-4:]],
        pageTail=[line[:CUT] for line in page["lines"][-12:]],
    )


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+", help="<출처 코드>=<글 주소>")
    parser.add_argument("--license", action="append", default=[])
    parser.add_argument("--terms-url", default="")
    parser.add_argument("--stop", action="append", default=[])
    args = parser.parse_args(argv)
    by_code = {source["code"]: source for source in registry.load()[0]}
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
        print(json.dumps(look(source, url), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

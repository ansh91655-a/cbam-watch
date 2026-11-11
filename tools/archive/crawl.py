"""지난 소식을 한꺼번에 모은다(소급 수집). 저장소 맨 위에서 `python -m tools.archive.crawl [--budget-minutes 30] [출처 이름 ...]`으로 돌린다.

출처마다 모듈 하나가 목록(collected/archive/<출처>.json)과, 재이용이 허용된 자료의 원문 글(collected/archive/pages/)을 쓴다.
한 출처가 실패해도 나머지는 계속하고, 출처마다 결과를 collected/archive/report/<출처>.json에 적는다.
시간 한도(--budget-minutes)를 주면 오래 걸리는 출처가 한도에서 멈춘다.
평소의 자동 실행은 이 프로그램을 쓰지 않는다. 지난 소식을 채울 때만 워크플로 '소급 수집'으로 돌린다.
"""
import argparse
import sys
import time

from tools.archive import acts, boards, cellar, council, docs, ecnews, efta, eurlex, fedreg, fulltext, govuk, hys, newsletter, oeil, presscorner, tables, tofeed, ukleg
from tools.archive.store import ROOT, SINCE
from tools.common.jsonio import stamp, write_json

STEPS = [("ec-news", ecnews.crawl), ("ec-newsletter", newsletter.crawl), ("eur-lex", eurlex.crawl), ("eur-lex-related", cellar.crawl),
         ("eur-lex-docs", docs.crawl), ("ep-oeil", oeil.crawl), ("ec-hys", hys.crawl), ("ec-press", presscorner.crawl), ("ec-press-recent", presscorner.recent),
         ("eu-council", council.crawl), ("eu-fulltext", fulltext.crawl), ("eu-acts", acts.crawl), ("eu-tables", tables.crawl), ("efta-eea-lex", efta.crawl),
         ("uk-govuk", govuk.crawl), ("uk-govuk-recent", govuk.recent), ("uk-legislation", ukleg.crawl), ("us-fedreg", fedreg.crawl), ("kr-boards", boards.crawl),
         ("to-feed", tofeed.run)]


TIMED = {"ec-news", "eur-lex-docs", "ec-press", "ec-press-recent"}  # 시간 한도를 넘기면 거기서 멈추는 출처


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget-minutes", type=float, default=0)
    parser.add_argument("steps", nargs="*")
    args = parser.parse_args(argv)
    wanted = set(args.steps)
    if not wanted:  # 이름을 주지 않으면 전체를 다시 모으는 것만 돌린다(최근 것만 보는 단계는 이름을 줘야 돈다)
        wanted = {name for name, _ in STEPS} - {"ec-press-recent", "uk-govuk-recent", "to-feed", "eu-fulltext", "eu-acts", "eu-tables"}
    deadline = time.monotonic() + args.budget_minutes * 60 if args.budget_minutes else None
    for name, step in STEPS:
        if wanted and name not in wanted:
            continue
        try:
            result = step(deadline) if name in TIMED else step()
        except Exception as error:
            result = {"error": f"{type(error).__name__}: {error}"[:300]}
        print(name, result, flush=True)
        # 출처마다 파일을 따로 써서, 출처가 다른 실행이 함께 돌아도 서로의 결과를 덮지 않는다.
        write_json(ROOT / "report" / f"{name}.json", {"ranAt": stamp(), "since": SINCE, "result": result})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

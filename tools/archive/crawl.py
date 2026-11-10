"""지난 소식을 한꺼번에 모은다(소급 수집). 저장소 맨 위에서 `python -m tools.archive.crawl [--budget-minutes 30] [출처 이름 ...]`으로 돌린다.

출처마다 모듈 하나가 목록(collected/archive/<출처>.json)과, 재이용이 허용된 자료의 원문 글(collected/archive/pages/)을 쓴다.
한 출처가 실패해도 나머지는 계속하고, 출처마다 결과를 collected/archive/report/<출처>.json에 적는다.
시간 한도(--budget-minutes)를 주면 오래 걸리는 출처(인터넷 아카이브)가 한도에서 멈추고, 다음에 돌릴 때 이어서 읽는다.
평소의 자동 실행은 이 프로그램을 쓰지 않는다. 지난 소식을 채울 때만 워크플로 '소급 수집'으로 돌린다.
"""
import argparse
import sys
import time

from tools.archive import boards, ecnews, govuk, hys, oeil, wayback
from tools.archive.store import ROOT, SINCE
from tools.common.jsonio import stamp, write_json

STEPS = [("ec-news", ecnews.crawl), ("ep-oeil", oeil.crawl), ("ec-hys", hys.crawl), ("uk-govuk", govuk.crawl), ("kr-boards", boards.crawl), ("ec-latest", wayback.crawl)]


TIMED = {"ec-latest", "ec-news"}  # 시간 한도를 넘기면 거기서 멈추는 출처


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget-minutes", type=float, default=0)
    parser.add_argument("steps", nargs="*")
    args = parser.parse_args(argv)
    wanted = set(args.steps)
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

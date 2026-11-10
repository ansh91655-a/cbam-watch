"""지난 소식을 한꺼번에 모은다(소급 수집). 저장소 맨 위에서 `python -m tools.archive.crawl [출처 이름 ...]`으로 돌린다.

출처마다 모듈 하나가 목록(collected/archive/<출처>.json)과, 재이용이 허용된 자료의 원문 글(collected/archive/pages/)을 쓴다.
한 출처가 실패해도 나머지는 계속하고, 결과를 collected/archive/crawl-report.json에 모아 적는다.
평소의 자동 실행은 이 프로그램을 쓰지 않는다. 지난 소식을 채울 때만 워크플로 '소급 수집'으로 돌린다.
"""
import sys

from tools.archive import boards, ecnews, govuk, hys, oeil, wayback
from tools.archive.store import ROOT, SINCE
from tools.common.jsonio import stamp, write_json

STEPS = [("ec-news", ecnews.crawl), ("ep-oeil", oeil.crawl), ("ec-hys", hys.crawl), ("uk-govuk", govuk.crawl), ("kr-boards", boards.crawl), ("ec-latest", wayback.crawl)]


def main(argv):
    wanted = set(argv)
    report = {"ranAt": stamp(), "since": SINCE, "steps": {}}
    for name, step in STEPS:
        if wanted and name not in wanted:
            continue
        try:
            report["steps"][name] = step()
        except Exception as error:
            report["steps"][name] = {"error": f"{type(error).__name__}: {error}"[:300]}
        print(name, report["steps"][name])
    write_json(ROOT / "crawl-report.json", report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

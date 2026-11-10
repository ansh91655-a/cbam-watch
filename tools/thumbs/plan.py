"""미리보기 그림을 만들 원문을 고른다.

쓰는 법: python -m tools.thumbs.plan <할 일 파일> [--limit 150]
고르는 것: 재이용이 허용된 공식 출처의 원문이고, 아직 그림이 없고, 세 번 넘게 실패하지 않은 것. 같은 원문은 한 번만 넣는다.
그 사이트의 robots.txt가 자동 읽기를 막은 주소는 넣지 않는다(tools.common.robots).
법령 데이터베이스(EUR-Lex)의 문서는 PDF 첫 장으로(kind "pdf"), 그 밖은 원문 화면으로(kind "page") 만든다.
"""
import argparse
import sys
import urllib.parse

from tools.common import robots
from tools.common.jsonio import read_json, write_json
from tools.publish import thumbs

STATE = "collected/thumbs/state.json"
MAX_TRIES = 3
# 재이용을 허용한 곳: EU 기관(europa.eu), 영국 정부(gov.uk, Open Government Licence)
ALLOWED_ENDS = (".europa.eu", ".gov.uk")
ALLOWED_HOSTS = set()
BLOCKED_HOSTS = {"www.consilium.europa.eu"}  # 자동 실행에서 열리지 않는 곳

def allowed(link):
    host = urllib.parse.urlparse(str(link)).netloc.lower()
    return str(link).startswith("https://") and host not in BLOCKED_HOSTS and (host.endswith(ALLOWED_ENDS) or host in ALLOWED_HOSTS)


def job_of(link):
    job = {"name": thumbs.name_of(link), "url": link, "kind": thumbs.kind_of(link)}
    if job["kind"] == "pdf":
        job["celex"] = thumbs.celex_of(link)
    return job


def todo(items, state, exists, limit, permitted=None):
    """items에서 만들 것을 고른다. exists(name)는 그림이 이미 있는지, permitted(link)는 robots.txt가 그 주소를 허용하는지 알려 주는 함수다."""
    permitted = permitted or (lambda link: robots.check(link)[0])
    seen, jobs = set(), []
    for item in items:
        if len(jobs) >= limit:
            break
        link = item.get("link", "")
        if item.get("withdrawn") or not allowed(link):
            continue
        name = thumbs.name_of(link)
        if name in seen or exists(name) or state.get(name, {}).get("tries", 0) >= MAX_TRIES:
            continue
        seen.add(name)
        if not permitted(link):  # 사이트가 자동 읽기를 막은 주소는 그림 없이 둔다
            continue
        jobs.append(job_of(link))
    return jobs


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--limit", type=int, default=150)
    args = parser.parse_args(argv)
    items = read_json("data/items.json", {}).get("items", [])
    jobs = todo(items, read_json(STATE, {}).get("failed", {}), lambda name: thumbs.path_of(name).exists(), args.limit)
    write_json(args.out, jobs)
    print(f"만들 그림 {len(jobs)}건(화면 {sum(1 for job in jobs if job['kind'] == 'page')}, PDF {sum(1 for job in jobs if job['kind'] == 'pdf')})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

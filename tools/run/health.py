"""저장소 쪽의 상태를 모아 한 줄 JSON으로 출력한다. 실행 확인과 보고에 쓴다.

쓰는 법: python -m tools.run.health
"""
import json
import subprocess
import sys

from tools.common.jsonio import read_json, today


def _git(*args):
    try:
        done = subprocess.run(["git", *args], capture_output=True, timeout=60)
        return done.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def main():
    status = read_json("collected/status.json", {"sources": {}})
    originals = read_json("originals/state.json", {})
    items = read_json("data/items.json", {"items": []})["items"]
    failing = [{"code": code, "failCount": row.get("failCount", 0), "note": row.get("note", "")[:80]}
               for code, row in status.get("sources", {}).items() if row.get("failCount", 0) >= 3]
    bulk = [row["code"] for row in status.get("sources", {}).values() if "구조가 바뀐" in row.get("note", "")]
    _git("fetch", "--depth", "1", "origin", "gh-pages")
    deployed = _git("log", "-1", "--format=%cI", "FETCH_HEAD")
    report = {
        "today": today(),
        "collectCheckedAt": status.get("checkedAt", ""),
        "collectToday": str(status.get("checkedAt", "")).startswith(today()),
        "sourcesChecked": len(status.get("sources", {})),
        "failingSources": failing,
        "restructuredSources": bulk,
        "originalsCheckedAt": originals.get("checkedAt", ""),
        "originalsNotes": originals.get("notes", [])[:5],
        "siteDeployedAt": deployed,
        "publishedItems": len(items),
        "newestListed": max((item.get("listed", "") for item in items), default=""),
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

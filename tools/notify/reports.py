"""저장소의 보고 파일(reports/)을 읽어, 알려야 하는 것을 고른다."""
import datetime
import pathlib

from tools.common.jsonio import read_json

ROOT = pathlib.Path("reports")
KINDS = ("daily", "weekly", "test")


def load(root=ROOT):
    """보고 파일을 모두 읽어 날짜가 이른 것부터 돌려준다. 읽지 못하는 파일은 건너뛴다."""
    found = []
    for kind in KINDS:
        for path in sorted((pathlib.Path(root) / kind).glob("*.json")):
            report = read_json(path, None)
            if isinstance(report, dict) and report.get("kind") == kind:
                report["_key"] = path.stem
                found.append(report)
    return sorted(found, key=lambda report: (str(report.get("date", "")), report["kind"]))


def recent(reports, day, days=3):
    """기준일에서 며칠 안에 쓴 보고만 남긴다. 워크플로가 하루 이틀 쉬어도 놓치지 않으려고 며칠을 본다."""
    first = (datetime.date.fromisoformat(day) - datetime.timedelta(days=days)).isoformat()
    return [report for report in reports if first <= str(report.get("date", "")) <= day]


def needs_notice(report):
    """알릴 보고인가. 일일 보고는 문제가 있을 때만, 주간 보고와 시험은 늘 알린다."""
    if report["kind"] == "daily":
        return report.get("status") == "문제"
    return True


def has_daily(reports, day):
    return any(report["kind"] == "daily" and report.get("date") == day for report in reports)

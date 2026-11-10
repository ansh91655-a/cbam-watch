"""JSON 파일을 읽고 쓰는 공통 함수."""
import datetime
import json
import pathlib

KST = datetime.timezone(datetime.timedelta(hours=9))


def read_json(path, default=None):
    path = pathlib.Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


def now_kst():
    return datetime.datetime.now(KST)


def stamp(moment=None):
    return (moment or now_kst()).isoformat(timespec="seconds")


def today(moment=None):
    return (moment or now_kst()).date().isoformat()

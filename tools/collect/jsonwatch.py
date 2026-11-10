"""화면 대신 JSON으로 목록을 주는 출처를 본다(예: EU 집행위원회의 의견수렴 목록).

출처 설정의 json 항목
- url: JSON을 주는 주소
- list: 목록이 든 자리(점으로 이은 경로)
- id: 항목을 가리는 값의 경로
- state: 이 값들이 바뀌면 같은 항목이라도 새 소식으로 본다(단계, 의견수렴 상태 등)
- fields: 후보 글에 담을 값. {"이름": "경로"} 꼴
- labels: 코드 값을 풀어 쓴 말. {"코드": "풀이"} 꼴. 원문 글 파일에 "코드 (풀이)"로 함께 적는다
"""
import hashlib
import json

from tools.common.htmltext import squeeze


def dig(value, path):
    """점으로 이은 경로를 따라 값을 꺼낸다. 숫자는 목록의 차례다. 없으면 None."""
    for part in str(path).split("."):
        if isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def plain(value):
    """값을 글로 바꾼다. 16932.0 같은 수는 16932로 적는다."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return squeeze(str(value))


def entries(source, body, keywords):
    """(항목 목록, 건수)를 돌려준다. 항목은 {key, kind, text, url, detail}이고 detail은 원문 글 파일에 쓸 줄들이다."""
    config = source["json"]
    rows = dig(json.loads(body.decode("utf-8", "replace")), config["list"]) or []
    labels = config.get("labels", {})
    found = {}
    for row in rows:
        row_id = plain(dig(row, config["id"]))
        if not row_id:
            continue
        values = {name: plain(dig(row, path)) for name, path in config.get("fields", {}).items()}
        text = " | ".join(value for value in values.values() if value)
        if source.get("filter") and not any(keyword.lower() in text.lower() for keyword in keywords):
            continue
        state = "|".join(plain(dig(row, path)) for path in config.get("state", []))
        key = "j:" + hashlib.sha1(f"{row_id}|{state}".encode("utf-8")).hexdigest()[:16]
        detail = [f"{name}: {value}" + (f" ({labels[value]})" if value in labels else "") for name, value in values.items() if value]
        found[key] = {"key": key, "kind": "record", "text": text[:600], "url": source["url"], "detail": [f"[주소] {source['url']}", f"번호: {row_id}"] + detail}
    return list(found.values()), {"links": 0, "lines": 0, "rows": len(rows)}

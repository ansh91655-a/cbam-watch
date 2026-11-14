"""화면에 적는 출처의 이름.

출처 대장(sources/registry.json)의 name은 운영에 쓰는 이름이라 영문 화면 이름이 섞여 있다("EC CBAM Communication and News").
화면에는 sources/labels.json에 적어 둔 국문 이름을 쓴다. 거기에 없는 출처는 name이 이미 국문이거나 그대로 적는 고유한 이름이다.
대장에 함께 적지 않는 까닭은 대장이 바뀌면 출처 수집이 다시 돌기 때문이다(이름은 수집과 상관이 없다).
저장소의 자료(data/items.json, data/events.json)에 적힌 sourceName은 쓸 때의 이름이므로 고치지 않고, 사이트 자료를 만들 때 바꿔 싣는다
(tools/publish/build_site.py가 자료를 읽자마자 바꾼다. 그 뒤의 모든 것이 바꾼 이름을 쓴다).
일정처럼 출처의 코드 없이 이름만 옮겨 적은 자료는 옛 이름으로 찾아 바꾼다.
"""
from tools.common.jsonio import read_json

REGISTRY = "sources/registry.json"
LABELS = "sources/labels.json"


def labels(path=LABELS):
    """{출처 코드: 화면에 적는 이름}. 적어 둔 출처만."""
    return dict((read_json(path, {}) or {}).get("labels", {}))


def by_name(table, items=(), path=REGISTRY):
    """{운영에 쓰는 이름: 화면에 적는 이름}. 대장의 name과, 소식 자료에 그 출처의 이름으로 적혀 있는 이름(쓸 때의 이름이 대장과 다를 수 있다).

    한 이름이 화면의 이름 둘로 갈리면(다른 출처가 같은 이름으로 적힌 것) 그 이름은 바꾸지 않는다.
    """
    found, clash = {}, set()
    pairs = [(source.get("name", ""), source["code"]) for source in (read_json(path, {}) or {}).get("sources", [])]
    pairs += [(item.get("sourceName", ""), item.get("sourceCode", "")) for item in items]
    for name, code in pairs:
        label = table.get(code)
        if not name or not label:
            continue
        if found.setdefault(name, label) != label:
            clash.add(name)
    return {name: label for name, label in found.items() if name not in clash}


def rename_items(items, table):
    """소식마다 출처의 이름을 화면에 적는 이름으로 바꾼 새 목록. 출처의 코드로 찾는다."""
    return [{**item, "sourceName": table[item["sourceCode"]]} if item.get("sourceCode") in table else item for item in items]


def rename_rows(rows, names):
    """일정처럼 출처의 이름만 적힌 줄들의 이름을 바꾼 새 목록."""
    return [{**row, "sourceName": names[row["sourceName"]]} if row.get("sourceName") in names else row for row in rows]


def rename_source(source, table):
    """가격표의 출처({code, name, url})의 이름을 바꾼다."""
    return {**source, "name": table[source["code"]]} if isinstance(source, dict) and source.get("code") in table else source

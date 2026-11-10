"""지도 그림이 함께 쓰는 것: 나라 경계 자료(world-atlas의 TopoJSON)를 읽고, 한 점이 어느 나라 위인지 본다.

나라 경계는 Natural Earth(공개 자료)를 TopoJSON으로 묶은 world-atlas의 countries-110m.json이다.
"""
import json
import pathlib

# EU 회원국 27개국의 ISO 3166-1 숫자 코드(110m 자료에는 몰타가 없다)
EU = {"040", "056", "100", "191", "196", "203", "208", "233", "246", "250", "276", "300", "348", "372", "380",
      "428", "440", "442", "470", "528", "616", "620", "642", "703", "705", "724", "752"}
KOREA = "410"


def countries(path):
    """나라마다 (코드, [다각형])을 돌려준다. 다각형은 [바깥 고리, 구멍, ...]이고 고리는 (경도, 위도)의 목록이다."""
    topo = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x += dx
            y += dy
            points.append((x * sx + tx, y * sy + ty))
        arcs.append(points)

    def ring(indices):
        points = []
        for index in indices:
            part = arcs[index] if index >= 0 else arcs[~index][::-1]
            points.extend(part if not points else part[1:])
        return points

    found = []
    for geometry in topo["objects"]["countries"]["geometries"]:
        if geometry["type"] == "Polygon":
            polygons = [[ring(r) for r in geometry["arcs"]]]
        elif geometry["type"] == "MultiPolygon":
            polygons = [[ring(r) for r in polygon] for polygon in geometry["arcs"]]
        else:
            continue
        found.append((str(geometry.get("id", "")).zfill(3), polygons))
    return found


def inside(ring, lon, lat):
    """고리 안의 점인가(짝수-홀수 규칙)."""
    hit = False
    count = len(ring)
    for index in range(count):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % count]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def box(ring):
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def shapes(world):
    """점이 어느 나라 위인지 빨리 보려고, 다각형마다 (코드, 다각형, 둘레 상자)를 미리 만들어 둔다."""
    return [(code, polygon, box(polygon[0])) for code, polygons in world for polygon in polygons]


def country_at(found, lon, lat):
    """(경도, 위도)가 놓인 나라의 코드. 바다면 None."""
    for code, polygon, (x1, y1, x2, y2) in found:
        if not (x1 <= lon <= x2 and y1 <= lat <= y2):
            continue
        if inside(polygon[0], lon, lat) and not any(inside(hole, lon, lat) for hole in polygon[1:]):
            return code
    return None

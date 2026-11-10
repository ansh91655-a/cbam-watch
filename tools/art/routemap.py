"""첫 화면의 지도를 만든다. 유라시아의 나라들을 면으로 그리고 EU 회원국과 한국을 다른 색으로 칠하고, 한국에서 EU로 가는 길을 선 하나로 그린다.

지도의 나라 경계는 Natural Earth(공개 자료)를 TopoJSON으로 묶은 world-atlas의 countries-110m.json에서 읽는다.
쓰는 법: python -m tools.art.routemap <countries-110m.json의 경로> [출력 파일]
출력은 화면 모듈(site/js/ui/heromap.js)이다. 지도를 고칠 때만 손으로 돌리고, 평소의 자동 실행은 이 프로그램을 쓰지 않는다.
"""
import json
import math
import pathlib
import sys

# EU 회원국 27개국의 ISO 3166-1 숫자 코드(110m 자료에는 몰타가 없다)
EU = {"040", "056", "100", "191", "196", "203", "208", "233", "246", "250", "276", "300", "348", "372", "380",
      "428", "440", "442", "470", "528", "616", "620", "642", "703", "705", "724", "752"}
KOREA = "410"
# 그리는 범위. 남쪽을 인도와 동남아시아의 바닷가까지 넣어야 뭍의 생김새로 어디인지 알아볼 수 있다.
WEST, EAST, SOUTH, NORTH = -14.0, 150.0, 6.0, 71.5
SCALE = 350.0   # 1라디안이 몇 px인가
EDGE = 3.0      # 그리는 범위를 이만큼(도) 벗어난 나라까지 그린다(가장자리에서 잘려 보이게)
HOME = (128.9, 35.3)  # 길이 떠나는 곳(한국 남동부)
GATE = (4.3, 51.9)    # 길이 닿는 곳(북해 연안)
LIFT = 0.17           # 길이 북쪽으로 휘는 정도(두 곳을 잇는 가장 짧은 길은 북쪽으로 휜다)
MERIDIANS = [0, 30, 60, 90, 120]
PARALLELS = [15, 30, 45, 60]
# 지도 위에 얹는 글(경도, 위도, 글, 종류). 글자 크기가 지도와 함께 줄지 않게 그림 밖의 HTML로 얹는다.
TAGS = [(12.0, 67.5, "EU 27개 회원국", "eu"), (128.5, 43.5, "한국", "kr")]


def mercator(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


TOP = mercator(NORTH)
WIDTH = math.radians(EAST - WEST) * SCALE
HEIGHT = (TOP - mercator(SOUTH)) * SCALE


def project(lon, lat):
    return math.radians(lon - WEST) * SCALE, (TOP - mercator(lat)) * SCALE


def countries(path):
    """나라마다 (코드, [다각형]) 을 돌려준다. 다각형은 [바깥 고리, 구멍, ...]이고 고리는 (경도, 위도)의 목록이다."""
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


def box(ring):
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def unwrap(ring):
    """날짜 변경선을 넘는 고리(러시아의 동쪽 끝)는 서쪽으로 넘어간 점을 동쪽으로 이어 붙인다. 그러지 않으면 지도를 가로지르는 선이 생긴다."""
    west, _, east, _ = box(ring)
    if east - west <= 180:
        return ring
    return [(lon + 360 if lon < 0 else lon, lat) for lon, lat in ring]


def visible(ring):
    west, south, east, north = box(ring)
    return east >= WEST - EDGE and west <= EAST + EDGE and north >= SOUTH - EDGE and south <= NORTH + EDGE


def ring_path(ring):
    """고리 하나를 그림의 길로 바꾼다. 자리는 정수로 줄인다(그림이 화면에서 절반쯤으로 줄어들기 때문에 충분하다)."""
    points = []
    for lon, lat in ring:
        x, y = project(lon, max(-60.0, min(84.0, lat)))
        point = (round(x), round(y))
        if not points or point != points[-1]:
            points.append(point)
    if len(points) < 3:
        return ""
    return "M" + "L".join(f"{x} {y}" for x, y in points) + "Z"


def shapes(world):
    """나라의 면을 (EU 회원국, 한국, 그 밖의 땅)의 길로 돌려준다. 그리는 범위에 걸치지 않는 나라는 뺀다."""
    eu, korea, land = [], [], []
    for code, polygons in world:
        for polygon in polygons:
            rings = [unwrap(ring) for ring in polygon]
            if not visible(rings[0]):
                continue
            (eu if code in EU else korea if code == KOREA else land).append("".join(ring_path(ring) for ring in rings))
    return "".join(eu), "".join(korea), "".join(land)


def route():
    """한국에서 EU로 가는 길 하나. (길, 화살촉, 떠나는 곳의 표시)를 돌려준다."""
    hx, hy = project(*HOME)
    gx, gy = project(*GATE)
    distance = math.hypot(gx - hx, gy - hy)
    cx, cy = (hx + gx) / 2, (hy + gy) / 2 - distance * LIFT
    path = f'<path class="map-route" pathLength="100" d="M{hx:.1f} {hy:.1f}Q{cx:.1f} {cy:.1f} {gx:.1f} {gy:.1f}"/>'
    # 화살촉: 길의 끝에서의 방향(조절점에서 끝점으로 가는 방향)으로 놓는다.
    angle = math.atan2(gy - cy, gx - cx)
    tip = [(gx + 13 * math.cos(angle), gy + 13 * math.sin(angle))]
    for turn in (2.45, -2.45):
        tip.append((gx + 13 * math.cos(angle + turn), gy + 13 * math.sin(angle + turn)))
    head = '<path class="map-head" d="M' + "L".join(f"{x:.1f} {y:.1f}" for x, y in tip) + 'Z"/>'
    home = (f'<circle class="map-home-ring" cx="{hx:.1f}" cy="{hy:.1f}" r="13"/>'
            f'<circle class="map-home" cx="{hx:.1f}" cy="{hy:.1f}" r="5.5"/>')
    return path, head, home


def graticule():
    """옅은 경선과 위선."""
    lines = []
    for lon in MERIDIANS:
        x, _ = project(lon, NORTH)
        lines.append(f"M{x:.1f} 0V{HEIGHT:.1f}")
    for lat in PARALLELS:
        _, y = project(WEST, lat)
        lines.append(f"M0 {y:.1f}H{WIDTH:.1f}")
    return f'<path class="map-grid" d="{"".join(lines)}"/>'


def tags():
    """지도 위에 얹는 글의 자리(그림의 너비와 높이에 대한 백분율)."""
    found = []
    for lon, lat, text, kind in TAGS:
        x, y = project(lon, lat)
        found.append({"left": round(100 * x / WIDTH, 1), "top": round(100 * y / HEIGHT, 1), "text": text, "kind": kind})
    return found


def svg(world):
    eu, korea, land = shapes(world)
    path, head, home = route()
    body = (
        f'<svg class="map" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" '
        'aria-label="유라시아 지도. 파랗게 칠한 곳은 EU 회원국, 노랗게 칠한 곳은 한국이고, 한국에서 EU로 선 하나가 이어진다.">'
        f'{graticule()}'  # 경위선은 땅 아래에 깔려 바다에서만 보인다
        f'<path class="map-land" fill-rule="evenodd" d="{land}"/>'
        f'<path class="map-eu" fill-rule="evenodd" d="{eu}"/>'
        f'<path class="map-kr" fill-rule="evenodd" d="{korea}"/>'
        f'<g class="map-arcs">{path}{head}</g>{home}'
        '</svg>'
    )
    return body, {"eu": len(eu), "korea": len(korea), "land": len(land)}


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.routemap <countries-110m.json> [출력 파일]")
        return 1
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/js/ui/heromap.js")
    body, counts = svg(countries(argv[0]))
    module = (
        "// 첫 화면의 지도. tools/art/routemap.py가 만든 파일이므로 손으로 고치지 않는다.\n"
        "// 나라 경계: Natural Earth(공개 자료), world-atlas(ISC)의 countries-110m.\n"
        f"const SVG = {json.dumps(body, ensure_ascii=False)};\n"
        f"const TAGS = {json.dumps(tags(), ensure_ascii=False)};\n\n"
        "// 지도 위의 글은 그림 밖의 글자로 얹는다. 그림이 줄어도 글자 크기가 그대로이게 하려는 것이다.\n"
        "export function heroMap({ tags = true } = {}) {\n"
        "  const holder = document.createElement(\"div\");\n"
        "  holder.className = \"hero-map\";\n"
        "  holder.innerHTML = SVG; // 이 파일에 든 고정된 그림이다. 데이터가 아니다.\n"
        "  if (!tags) return holder;\n"
        "  for (const tag of TAGS) {\n"
        "    const label = document.createElement(\"span\");\n"
        "    label.className = `map-tag map-tag-${tag.kind}`;\n"
        "    label.style.left = `${tag.left}%`;\n"
        "    label.style.top = `${tag.top}%`;\n"
        "    label.textContent = tag.text;\n"
        "    label.setAttribute(\"aria-hidden\", \"true\"); // 그림의 설명글에 이미 들어 있다\n"
        "    holder.append(label);\n"
        "  }\n"
        "  return holder;\n"
        "}\n"
    )
    out.write_text(module, encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": len(module), **counts, "size": [round(WIDTH), round(HEIGHT)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""첫 화면의 점 지도를 만든다. 유라시아를 점으로 찍고 EU 회원국과 한국을 따로 표시하고, 한국에서 EU의 항구로 가는 흐름선을 그린다.

지도의 나라 경계는 Natural Earth(공개 자료)를 TopoJSON으로 묶은 world-atlas의 countries-110m.json에서 읽는다.
쓰는 법: python -m tools.art.dotmap <countries-110m.json의 경로> [출력 파일]
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
WEST, EAST, SOUTH, NORTH = -13.0, 147.0, 27.0, 69.5
SCALE = 400.0   # 1라디안이 몇 px인가
STEP = 12.0     # 점 사이의 거리(px)
HOME = (128.6, 35.6)  # 흐름선이 떠나는 곳(한국 남동부)
PORTS = [("로테르담", 4.1, 51.9, 0.30), ("함부르크", 9.9, 53.5, 0.36), ("그단스크", 18.7, 54.4, 0.42),
         ("코페르", 13.7, 45.5, 0.24), ("피레우스", 23.6, 37.9, 0.18), ("발렌시아", -0.3, 39.4, 0.22)]


def mercator(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


TOP = mercator(NORTH)
WIDTH = math.radians(EAST - WEST) * SCALE
HEIGHT = (TOP - mercator(SOUTH)) * SCALE


def project(lon, lat):
    return math.radians(lon - WEST) * SCALE, (TOP - mercator(lat)) * SCALE


def unproject(x, y):
    lat = math.degrees(2 * math.atan(math.exp(TOP - y / SCALE)) - math.pi / 2)
    return WEST + math.degrees(x / SCALE), lat


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


def inside(ring, lon, lat):
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


def classify(world):
    """점마다 어느 나라 위인지 본다. (EU의 점, 한국의 점, 그 밖의 땅의 점)을 돌려준다."""
    shapes = []
    for code, polygons in world:
        for polygon in polygons:
            shapes.append((code, polygon, box(polygon[0])))
    eu, korea, land = [], [], []
    row = 0
    y = STEP / 2
    while y < HEIGHT:
        x = STEP / 2 + (STEP / 2 if row % 2 else 0)
        while x < WIDTH:
            lon, lat = unproject(x, y)
            for code, polygon, (x1, y1, x2, y2) in shapes:
                if not (x1 <= lon <= x2 and y1 <= lat <= y2):
                    continue
                if inside(polygon[0], lon, lat) and not any(inside(hole, lon, lat) for hole in polygon[1:]):
                    (eu if code in EU else korea if code == KOREA else land).append((round(x, 1), round(y, 1)))
                    break
            x += STEP
        y += STEP * 0.866
        row += 1
    return eu, korea, land


def dots(points):
    return "".join(f"M{x:g} {y:g}h0" for x, y in points)


def arcs():
    hx, hy = project(*HOME)
    paths, ports = [], []
    for name, lon, lat, lift in PORTS:
        px, py = project(lon, lat)
        distance = math.hypot(px - hx, py - hy)
        cx, cy = (hx + px) / 2, (hy + py) / 2 - distance * lift
        paths.append(f'<path class="map-arc" pathLength="100" d="M{hx:.1f} {hy:.1f}Q{cx:.1f} {cy:.1f} {px:.1f} {py:.1f}"/>')
        ports.append(f'<circle class="map-port" cx="{px:.1f}" cy="{py:.1f}" r="4"><title>{name}</title></circle>')
    home = (f'<circle class="map-home-ring" cx="{hx:.1f}" cy="{hy:.1f}" r="13"/>'
            f'<circle class="map-home" cx="{hx:.1f}" cy="{hy:.1f}" r="6"/>')
    return "".join(paths), "".join(ports), home, (hx, hy)


def svg(world):
    eu, korea, land = classify(world)
    paths, ports, home, (hx, hy) = arcs()
    ex, ey = project(12, 49)  # EU 한가운데쯤. 뒤에 은은한 빛을 둔다.
    body = (
        f'<svg class="map" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" preserveAspectRatio="xMinYMid slice" role="img" '
        'aria-label="유라시아를 점으로 그린 지도. 밝은 점은 EU 회원국, 노란 점은 한국이고, 한국에서 EU의 항구로 선이 이어진다.">'
        '<defs>'
        f'<radialGradient id="map-glow" cx="{ex:.0f}" cy="{ey:.0f}" r="260" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-glow-in"/><stop offset="1" class="map-glow-out"/></radialGradient>'
        f'<linearGradient id="map-arc" x1="{hx:.0f}" y1="0" x2="{ex:.0f}" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-arc-from"/><stop offset="1" class="map-arc-to"/></linearGradient>'
        '</defs>'
        f'<rect class="map-glow" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" fill="url(#map-glow)"/>'
        f'<path class="map-land" d="{dots(land)}"/>'
        f'<path class="map-eu" d="{dots(eu)}"/>'
        f'<path class="map-kr" d="{dots(korea)}"/>'
        f'<g class="map-arcs" stroke="url(#map-arc)">{paths}</g>{ports}{home}'
        '</svg>'
    )
    return body, {"eu": len(eu), "korea": len(korea), "land": len(land)}


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.dotmap <countries-110m.json> [출력 파일]")
        return 1
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/js/ui/heromap.js")
    body, counts = svg(countries(argv[0]))
    module = (
        "// 첫 화면의 점 지도. tools/art/dotmap.py가 만든 파일이므로 손으로 고치지 않는다.\n"
        "// 나라 경계: Natural Earth(공개 자료), world-atlas(ISC)의 countries-110m.\n"
        f"const SVG = {json.dumps(body, ensure_ascii=False)};\n\n"
        "export function heroMap() {\n"
        "  const holder = document.createElement(\"div\");\n"
        "  holder.className = \"hero-map\";\n"
        "  holder.innerHTML = SVG; // 이 파일에 든 고정된 그림이다. 데이터가 아니다.\n"
        "  return holder;\n"
        "}\n"
    )
    out.write_text(module, encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": len(module), **counts, "size": [round(WIDTH), round(HEIGHT)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

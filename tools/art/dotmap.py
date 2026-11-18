"""첫 화면의 점 지도를 만든다. 유럽에서 동아시아까지를 점으로 찍고 EU 회원국과 한국을 따로 표시하고,
부산에서 말라카 해협과 수에즈 운하를 지나 EU의 항구로 가는 뱃길을 그린다.

쓰는 법: python -m tools.art.dotmap <countries-50m.json의 경로> [출력 파일]
출력은 화면 모듈(site/js/ui/heromap.js)이다. 지도를 고칠 때만 손으로 돌리고, 평소의 자동 실행은 이 프로그램을 쓰지 않는다.

그림은 두 장으로 나눈다. 아래 장은 움직이지 않는 점 지도이고, 위 장은 뱃길과 그 위를 지나가는 빛이다.
움직이는 것을 따로 두어야 화면이 점 수천 개를 되풀이해 그리지 않는다.
점은 줄마다 이어진 것끼리 한 선으로 적는다(선을 점선으로 그리면 점이 된다: 꾸밈의 stroke-dasharray). 점마다 적는 것보다 파일이 훨씬 작다.
점 사이의 거리보다 좁은 물길(수에즈, 바브엘만데브, 지브롤터, 말라카, 도버, 오트란토)에서는 뱃길에 닿는 점을 덜어 내 길을 트고, 그 밖에서 뱃길이 땅의 점을 밟으면 만들기를 멈춘다.
"""
import json
import math
import pathlib
import sys

from tools.art import sealane, world

# 그리는 범위. 서쪽은 뱃길이 이베리아반도를 돌아가는 바다를 넉넉히 넣고, 동쪽은 일본까지, 남쪽은 뱃길이 지나는 싱가포르 아래까지, 북쪽은 스칸디나비아의 가운데까지.
# 가장자리는 화면에서 흐리게 지우므로(layout.css) 뱃길과 EU, 한국이 가장자리에 걸리지 않게 여유를 둔다.
WEST, EAST, SOUTH, NORTH = -22.0, 146.5, -7.0, 64.0
WIDTH = 1120.0
SCALE = WIDTH / math.radians(EAST - WEST)   # 1라디안이 몇 px인가
STEP = 8.6      # 점 사이의 거리(px). 꾸밈(site/css/map.css의 --map-step)과 같아야 한다
ROW = STEP * 0.866
GLOW = (10.0, 49.5)   # EU 한가운데쯤. 뒤에 은은한 빛을 둔다.
CLEAR = 0.52          # 뱃길이 땅의 점에서 떨어져 있어야 하는 거리(점 사이 거리의 배수)
# 뱃길이 지나는 좁은 물길(서쪽 경도, 동쪽 경도, 남쪽 위도, 북쪽 위도). 점 사이의 거리보다 좁아 점에 묻히는 곳이다.
# 이 안에서는 뱃길에 닿는 땅의 점을 덜어 내 물길을 튼다. 이 밖에서 뱃길이 땅의 점을 밟으면 만들기를 멈춘다(항구 언저리는 빼고 본다).
NARROWS = [
    (31.6, 34.8, 26.8, 31.8),    # 수에즈만과 수에즈 운하
    (42.4, 44.0, 12.0, 14.0),    # 바브엘만데브 해협
    (-6.3, -4.6, 35.5, 36.4),    # 지브롤터 해협
    (97.5, 104.8, 0.6, 6.6),     # 말라카 해협과 싱가포르 해협
    (0.8, 2.3, 50.6, 51.5),      # 도버 해협
    (18.2, 19.7, 39.6, 41.0),    # 오트란토 해협
]
NEAR_PORT = 1.6       # 항구에서 이 도(°) 안은 보지 않는다


def mercator(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


TOP = mercator(NORTH)
HEIGHT = (TOP - mercator(SOUTH)) * SCALE


def project(lon, lat):
    return math.radians(lon - WEST) * SCALE, (TOP - mercator(lat)) * SCALE


def unproject(x, y):
    lat = math.degrees(2 * math.atan(math.exp(TOP - y / SCALE)) - math.pi / 2)
    return WEST + math.degrees(x / SCALE), lat


def classify(countries):
    """줄마다 점이 어느 나라 위인지 본다: [(y, [(x, 갈래)])]. 갈래는 "eu", "kr", "land"이고 바다의 점은 싣지 않는다."""
    found = world.shapes(countries)
    rows, row, y = [], 0, ROW / 2
    while y < HEIGHT:
        x = STEP / 2 + (STEP / 2 if row % 2 else 0)
        dots = []
        while x < WIDTH:
            code = world.country_at(found, *unproject(x, y))
            if code:
                dots.append((round(x, 2), "eu" if code in world.EU else "kr" if code == world.KOREA else "land"))
            x += STEP
        rows.append((round(y, 2), dots))
        y += ROW
        row += 1
    return rows


def runs(rows, kind):
    """한 갈래의 점들을 줄마다 이어진 것끼리 묶은 선들의 글. 선의 길이는 (점의 수 - 1) × STEP에 조금 더한 것이다(마지막 점이 빠지지 않게)."""
    out = []
    for y, dots in rows:
        start, count, last = None, 0, None
        for x, what in dots + [(None, None)]:
            joined = what == kind and last is not None and abs(x - last - STEP) < 0.01
            if joined:
                count += 1
            else:
                if start is not None:
                    out.append(f"M{start:g} {y:g}h{(count - 1) * STEP + 0.1:.1f}")
                start, count = (x, 1) if what == kind else (None, 0)
            last = x if what == kind else None
    return "".join(out)


def _narrow(lon, lat):
    return any(west <= lon <= east and south <= lat <= north for west, east, south, north in NARROWS)


def _samples(routes):
    """뱃길 위의 점들: [(x, y, 경도, 위도)]"""
    lines = [routes["trunk"]] + [pieces for _, pieces in routes["branches"]]
    return [(x, y, *unproject(x, y)) for pieces in lines for x, y in sealane.along(pieces)]


def _touched(x, y, dx, dy):
    return abs(x - dx) < STEP and abs(y - dy) < STEP and math.hypot(x - dx, y - dy) < CLEAR * STEP


def carve(rows, routes):
    """좁은 물길에서 뱃길에 닿는 땅의 점을 덜어 낸 줄들."""
    inside = [(x, y) for x, y, lon, lat in _samples(routes) if _narrow(lon, lat)]
    return [(dy, [(dx, what) for dx, what in dots if not any(_touched(x, y, dx, dy) for x, y in inside)]) for dy, dots in rows]


def stepped(rows, routes):
    """뱃길이 밟은 땅의 점들: [(경도, 위도)]. 좁은 물길과 항구 언저리는 뺀다."""
    land = [(x, y) for y, dots in rows for x, _ in dots]
    ports = [unproject(x, y) for _, x, y in routes["ports"]] + [unproject(*routes["home"])]
    found = []
    for x, y, lon, lat in _samples(routes):
        if _narrow(lon, lat) or any(math.hypot(lon - px, lat - py) < NEAR_PORT for px, py in ports):
            continue
        if any(_touched(x, y, dx, dy) for dx, dy in land):
            found.append((round(lon, 1), round(lat, 1)))
    return found


def length(pieces):
    points = sealane.along(pieces, steps=24)
    return sum(math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(points, points[1:]))


def over(routes):
    """위 장: 뱃길, 그 위를 지나가는 빛, 항구의 점, 떠나는 곳의 표시."""
    hx, hy = routes["home"]
    ex, _ = project(*GLOW)
    trunk = sealane.path(routes["trunk"])
    whole = length(routes["trunk"])
    lanes = [f'<path class="map-lane-glow" pathLength="100" d="{trunk}"/>', f'<path class="map-lane" pathLength="100" d="{trunk}"/>']
    names = [name for name, _, _ in sealane.TRUNK]
    for (port, pieces), (start, _) in zip(routes["branches"], sealane.BRANCHES):
        # 가지는 줄기가 갈라지는 곳까지 그려진 뒤에 그려진다: 줄기의 길이에서 그곳까지의 비율을 적어 둔다(꾸밈이 기다리는 시간으로 쓴다)
        share = length(routes["trunk"][:names.index(start)]) / whole
        lanes.append(f'<path class="map-lane map-branch" pathLength="100" style="--at:{share:.3f}" d="{sealane.path(pieces)}"/>')
    lights = "".join(f'<path class="map-light" pathLength="100" d="{sealane.path(pieces)}"/>' for _, pieces in routes["whole"])
    ports = "".join(f'<g class="map-port"><circle class="map-port-ring" cx="{x:.1f}" cy="{y:.1f}" r="6.4"/><circle class="map-port-dot" cx="{x:.1f}" cy="{y:.1f}" r="2.9"/></g>'
                    for _, x, y in routes["ports"])
    start = (f'<circle class="map-home-pulse" cx="{hx:.1f}" cy="{hy:.1f}" r="12"/>'
             f'<circle class="map-home-ring" cx="{hx:.1f}" cy="{hy:.1f}" r="9.5"/>'
             f'<circle class="map-home" cx="{hx:.1f}" cy="{hy:.1f}" r="4.6"/>')
    return (
        f'<svg class="map map-over" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" aria-hidden="true">'
        '<defs>'
        f'<linearGradient id="map-lane" x1="{hx:.0f}" y1="0" x2="{ex:.0f}" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-lane-from"/><stop offset="0.55" class="map-lane-mid"/><stop offset="1" class="map-lane-to"/></linearGradient>'
        '</defs>'
        f'<g class="map-lanes" stroke="url(#map-lane)">{"".join(lanes)}</g>'
        f'<g class="map-lights">{lights}</g>{ports}{start}'
        '</svg>'
    )


def base(rows, routes):
    """아래 장: 점 지도와 그 뒤의 은은한 빛."""
    ex, ey = project(*GLOW)
    hx, hy = routes["home"]
    return (
        f'<svg class="map" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" '
        'aria-label="유럽에서 동아시아까지를 점으로 그린 지도. 밝은 점은 EU 회원국, 노란 점은 한국이고, 부산에서 말라카 해협과 수에즈 운하를 지나 EU의 항구로 가는 뱃길이 그려져 있다.">'
        '<defs>'
        f'<radialGradient id="map-glow" cx="{ex:.0f}" cy="{ey:.0f}" r="250" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-glow-in"/><stop offset="1" class="map-glow-out"/></radialGradient>'
        f'<radialGradient id="map-glow-kr" cx="{hx:.0f}" cy="{hy:.0f}" r="120" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-glow-kr-in"/><stop offset="1" class="map-glow-kr-out"/></radialGradient>'
        '</defs>'
        f'<rect class="map-glow" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" fill="url(#map-glow)"/>'
        f'<rect class="map-glow" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" fill="url(#map-glow-kr)"/>'
        f'<path class="map-dots map-land" d="{runs(rows, "land")}"/>'
        f'<path class="map-dots map-eu" d="{runs(rows, "eu")}"/>'
        f'<path class="map-dots map-kr" d="{runs(rows, "kr")}"/>'
        '</svg>'
    )


def pictures(countries):
    routes = sealane.routes(project)
    rows = carve(classify(countries), routes)
    trodden = stepped(rows, routes)
    if trodden:
        raise SystemExit(f"뱃길이 땅의 점을 밟습니다(경도, 위도): {trodden[:12]}. tools/art/sealane.py의 지나는 곳을 바다 쪽으로 옮겨 주세요.")
    counts = {kind: sum(1 for _, dots in rows for _, what in dots if what == kind) for kind in ("eu", "kr", "land")}
    return base(rows, routes), over(routes), counts


MODULE = """// 첫 화면의 점 지도. tools/art/dotmap.py가 만든 파일이므로 손으로 고치지 않는다.
// 나라 경계: Natural Earth(공개 자료), world-atlas(ISC)의 countries-50m.
const BASE = %s;
const OVER = %s;

// 아래 장은 점 지도, 위 장은 뱃길과 그 위를 지나가는 빛이다. 둘 다 이 파일에 든 고정된 그림이고 데이터가 아니다.
// 지도 위에는 글을 얹지 않는다. 무엇을 그린 것인지는 그림의 설명글(aria-label)에만 적혀 있다.
export function heroMap() {
  const holder = document.createElement("div");
  holder.className = "hero-map";
  holder.innerHTML = BASE + OVER;
  return holder;
}
"""


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.dotmap <countries-50m.json> [출력 파일]")
        return 1
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/js/ui/heromap.js")
    lower, upper, counts = pictures(world.countries(argv[0]))
    module = MODULE % (json.dumps(lower, ensure_ascii=False), json.dumps(upper, ensure_ascii=False))
    out.write_text(module, encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": len(module), **counts, "size": [round(WIDTH), round(HEIGHT)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

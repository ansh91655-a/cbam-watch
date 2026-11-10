"""첫 화면의 점 지도를 만든다. 유라시아를 점으로 찍고 EU 회원국과 한국을 따로 표시하고, 한국에서 EU의 항구로 가는 흐름선을 그린다.

쓰는 법: python -m tools.art.dotmap <countries-110m.json의 경로> [출력 파일]
출력은 화면 모듈(site/js/ui/heromap.js)이다. 지도를 고칠 때만 손으로 돌리고, 평소의 자동 실행은 이 프로그램을 쓰지 않는다.

그림은 두 장으로 나눈다. 아래 장은 움직이지 않는 점 지도이고, 위 장은 흐름선과 그 위를 지나가는 빛이다.
움직이는 것을 따로 두어야 화면이 점 수천 개를 되풀이해 그리지 않는다.
"""
import json
import math
import pathlib
import sys

from tools.art import world

# 그리는 범위. 서쪽은 대서양을 조금 넣어 EU가 그림의 가장자리에 걸리지 않게 하고, 동쪽은 일본까지 넣는다.
WEST, EAST, SOUTH, NORTH = -25.0, 152.0, 23.0, 70.5
WIDTH = 1117.0
SCALE = WIDTH / math.radians(EAST - WEST)   # 1라디안이 몇 px인가
STEP = 11.0     # 점 사이의 거리(px)
HOME = (129.0, 35.1)  # 흐름선이 떠나는 곳(부산)
# 흐름선이 닿는 EU의 항구(이름, 경도, 위도, 선이 북쪽으로 휘는 정도). 북쪽 선부터 적는다.
# 휘는 정도는 두 곳 사이의 거리에 대한 비율이다. 값이 거의 같아야 선들이 한 묶음으로 보이고 서로 엇갈리지 않는다.
# 항구를 바꾸면 선이 엇갈리지 않는지 이 프로그램이 확인하고, 엇갈리면 멈춘다.
PORTS = [("로테르담", 4.14, 51.95, 0.28), ("르아브르", 0.11, 49.49, 0.25), ("코페르", 13.73, 45.55, 0.25),
         ("발렌시아", -0.32, 39.44, 0.25), ("피레우스", 23.63, 37.94, 0.25)]
GLOW = (11.0, 49.0)   # EU 한가운데쯤. 뒤에 은은한 빛을 둔다.
# 지도 위에 얹는 글(경도, 위도, 글, 종류). 글자 크기가 지도와 함께 줄지 않게 그림 밖의 글자로 얹는다.
TAGS = [(13.0, 66.5, "EU 회원국", "eu"), (129.0, 29.0, "한국", "kr")]


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
    """점마다 어느 나라 위인지 본다. (EU의 점, 한국의 점, 그 밖의 땅의 점)을 돌려준다."""
    found = world.shapes(countries)
    eu, korea, land = [], [], []
    row = 0
    y = STEP / 2
    while y < HEIGHT:
        x = STEP / 2 + (STEP / 2 if row % 2 else 0)
        while x < WIDTH:
            code = world.country_at(found, *unproject(x, y))
            if code:
                (eu if code in world.EU else korea if code == world.KOREA else land).append((round(x, 1), round(y, 1)))
            x += STEP
        y += STEP * 0.866
        row += 1
    return eu, korea, land


def dots(points):
    return "".join(f"M{x:g} {y:g}h0" for x, y in points)


def curve(home, port, lift):
    """떠나는 곳에서 항구까지 북쪽으로 휜 선(2차 곡선)의 조절점."""
    (hx, hy), (px, py) = home, port
    distance = math.hypot(px - hx, py - hy)
    nx, ny = (py - hy) / distance, -(px - hx) / distance   # 두 곳을 잇는 곧은 선에 수직인 방향
    if ny > 0:
        nx, ny = -nx, -ny                                   # 위쪽(북쪽)으로
    return (hx + px) / 2 + nx * distance * lift, (hy + py) / 2 + ny * distance * lift


def trace(home, control, port, steps=160):
    """곡선 위의 점들. 선이 서로 엇갈리는지 볼 때 쓴다."""
    (hx, hy), (cx, cy), (px, py) = home, control, port
    return [((1 - t) ** 2 * hx + 2 * t * (1 - t) * cx + t * t * px, (1 - t) ** 2 * hy + 2 * t * (1 - t) * cy + t * t * py)
            for t in (step / steps for step in range(steps + 1))]


def crossing(first, second):
    """두 선이 떠나는 곳을 벗어난 뒤에 엇갈리는가."""
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    first, second = first[8:], second[8:]   # 모든 선이 한 점에서 떠나므로 그 언저리는 빼고 본다
    return any(side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0
               for a, b in zip(first, first[1:]) for c, d in zip(second, second[1:]))


def flows():
    """흐름선, 그 위를 지나가는 빛, 항구의 점, 떠나는 곳의 표시."""
    home = project(*HOME)
    hx, hy = home
    lines, lights, ports, traces = [], [], [], []
    for name, lon, lat, lift in PORTS:
        px, py = project(lon, lat)
        cx, cy = curve(home, (px, py), lift)
        traces.append((name, trace(home, (cx, cy), (px, py))))
        d = f"M{hx:.1f} {hy:.1f}Q{cx:.1f} {cy:.1f} {px:.1f} {py:.1f}"
        lines.append(f'<path class="map-arc" pathLength="100" d="{d}"/>')
        lights.append(f'<path class="map-light" pathLength="100" d="{d}"/>')
        ports.append(f'<circle class="map-port" cx="{px:.1f}" cy="{py:.1f}" r="3.6"><title>{name}</title></circle>')
    for index, (name, points) in enumerate(traces):
        for other, others in traces[index + 1:]:
            if crossing(points, others):
                raise SystemExit(f"흐름선이 엇갈립니다: {name}, {other}. 항구나 휘는 정도를 바꿔 주세요.")
    start = (f'<circle class="map-home-pulse" cx="{hx:.1f}" cy="{hy:.1f}" r="13"/>'
             f'<circle class="map-home-ring" cx="{hx:.1f}" cy="{hy:.1f}" r="13"/>'
             f'<circle class="map-home" cx="{hx:.1f}" cy="{hy:.1f}" r="5.5"/>')
    return "".join(lines), "".join(lights), "".join(ports), start, home


def pictures(countries):
    eu, korea, land = classify(countries)
    lines, lights, ports, start, (hx, hy) = flows()
    ex, ey = project(*GLOW)
    size = f'viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}"'
    base = (
        f'<svg class="map" {size} role="img" '
        'aria-label="유라시아를 점으로 그린 지도. 밝은 점은 EU 회원국, 노란 점은 한국이고, 한국에서 EU의 항구로 선이 이어진다.">'
        '<defs>'
        f'<radialGradient id="map-glow" cx="{ex:.0f}" cy="{ey:.0f}" r="250" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-glow-in"/><stop offset="1" class="map-glow-out"/></radialGradient>'
        '</defs>'
        f'<rect class="map-glow" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" fill="url(#map-glow)"/>'
        f'<path class="map-land" d="{dots(land)}"/>'
        f'<path class="map-eu" d="{dots(eu)}"/>'
        f'<path class="map-kr" d="{dots(korea)}"/>'
        '</svg>'
    )
    over = (
        f'<svg class="map map-over" {size} aria-hidden="true">'
        '<defs>'
        f'<linearGradient id="map-arc" x1="{hx:.0f}" y1="0" x2="{ex:.0f}" y2="0" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" class="map-arc-from"/><stop offset="1" class="map-arc-to"/></linearGradient>'
        '</defs>'
        f'<g class="map-arcs" stroke="url(#map-arc)">{lines}</g>'
        f'<g class="map-lights">{lights}</g>{ports}{start}'
        '</svg>'
    )
    tags = []
    for lon, lat, text, kind in TAGS:
        x, y = project(lon, lat)
        tags.append({"left": round(100 * x / WIDTH, 1), "top": round(100 * y / HEIGHT, 1), "text": text, "kind": kind})
    return base, over, tags, {"eu": len(eu), "korea": len(korea), "land": len(land)}


MODULE = """// 첫 화면의 점 지도. tools/art/dotmap.py가 만든 파일이므로 손으로 고치지 않는다.
// 나라 경계: Natural Earth(공개 자료), world-atlas(ISC)의 countries-110m.
const BASE = %s;
const OVER = %s;
const TAGS = %s;

// 아래 장은 점 지도, 위 장은 흐름선과 그 위를 지나가는 빛이다. 둘 다 이 파일에 든 고정된 그림이고 데이터가 아니다.
// 지도 위의 글은 그림 밖의 글자로 얹는다. 그림이 줄어도 글자 크기가 그대로이게 하려는 것이다.
export function heroMap({ tags = true } = {}) {
  const holder = document.createElement("div");
  holder.className = "hero-map";
  holder.innerHTML = BASE + OVER;
  if (!tags) return holder;
  for (const tag of TAGS) {
    const label = document.createElement("span");
    label.className = `map-tag map-tag-${tag.kind}`;
    label.style.left = `${tag.left}%%`;
    label.style.top = `${tag.top}%%`;
    label.textContent = tag.text;
    label.setAttribute("aria-hidden", "true"); // 그림의 설명글에 이미 들어 있다
    holder.append(label);
  }
  return holder;
}
"""


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.art.dotmap <countries-110m.json> [출력 파일]")
        return 1
    out = pathlib.Path(argv[1] if len(argv) > 1 else "site/js/ui/heromap.js")
    base, over, tags, counts = pictures(world.countries(argv[0]))
    module = MODULE % (json.dumps(base, ensure_ascii=False), json.dumps(over, ensure_ascii=False), json.dumps(tags, ensure_ascii=False))
    out.write_text(module, encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": len(module), **counts, "size": [round(WIDTH), round(HEIGHT)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

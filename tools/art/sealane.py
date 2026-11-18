"""첫 화면 지도에 그리는 뱃길: 부산에서 말라카 해협과 수에즈 운하를 지나 EU의 항구로 가는 길.

실제 항로를 따라 그린 것이 아니라, 지도의 점 사이로 지나가도록 잡은 약도다. 지나는 곳은 (경도, 위도)로 적는다.
줄기(TRUNK)는 부산에서 로테르담까지이고, 가지(BRANCHES)는 줄기의 한 곳에서 갈라져 다른 항구로 간다.
점들을 부드럽게 잇는 곡선(캣멀-롬 곡선을 3차 베지에 조각으로 바꾼 것)과, 그 곡선 위의 점들을 돌려준다.
"""

HOME = ("부산", 129.05, 35.1)

# 줄기: 지나는 곳의 이름은 갈라지는 곳을 가리킬 때만 쓴다.
TRUNK = [
    ("부산", 129.05, 35.1), ("", 126.4, 31.4), ("", 122.9, 27.6), ("", 120.3, 25.3), ("", 118.9, 23.2), ("", 115.4, 18.0), ("", 111.0, 10.6), ("", 106.4, 4.8),
    ("싱가포르", 104.1, 1.25), ("", 101.2, 2.7), ("", 98.4, 5.1), ("", 95.2, 6.3), ("", 88.0, 6.0), ("", 80.6, 5.3), ("", 76.0, 7.3),
    ("", 67.0, 11.2), ("", 57.5, 13.4), ("", 51.6, 12.9), ("", 46.6, 12.2), ("", 43.6, 12.35), ("", 42.3, 14.6), ("", 39.6, 19.2),
    ("", 36.9, 23.6), ("", 34.4, 27.2), ("", 32.7, 29.6), ("포트사이드", 32.35, 31.4), ("", 30.0, 33.0), ("동지중해", 26.6, 34.0),
    ("", 23.0, 34.6), ("이오니아해", 19.2, 35.6), ("", 14.6, 36.0), ("", 11.2, 37.6), ("", 8.0, 38.3), ("서지중해", 3.4, 37.8),
    ("", -1.2, 36.5), ("지브롤터", -5.4, 35.95), ("", -8.0, 36.2), ("", -10.0, 37.6), ("", -10.4, 40.6), ("", -10.0, 43.6),
    ("", -7.0, 47.9), ("영국해협", -4.0, 49.75), ("", -0.6, 50.2), ("", 1.5, 51.0), ("", 3.0, 51.75), ("로테르담", 4.14, 51.95),
]

# 가지: (갈라지는 곳, [그 뒤로 지나는 곳 ..., 항구])
BRANCHES = [
    ("동지중해", [("", 26.75, 35.3), ("", 25.4, 36.8), ("피레우스", 23.63, 37.94)]),
    ("이오니아해", [("", 19.0, 38.4), ("", 19.0, 40.3), ("", 17.3, 42.2), ("", 14.6, 43.8), ("코페르", 13.73, 45.55)]),
    ("서지중해", [("", 1.4, 38.5), ("발렌시아", -0.32, 39.44)]),
    ("영국해협", [("", -2.0, 50.05), ("르아브르", 0.11, 49.49)]),
]


def spline(points, before=None, after=None):
    """점들을 차례로 지나는 부드러운 곡선의 조각들: [(시작, 조절점 1, 조절점 2, 끝)].

    before와 after는 곡선의 양 끝에서 방향을 잡아 주는 바깥 점이다(없으면 끝점을 되풀이한다).
    가지는 before에 줄기의 앞 점을 주어 줄기에서 꺾이지 않고 갈라지게 한다.
    """
    all_points = [before or points[0]] + list(points) + [after or points[-1]]
    pieces = []
    for index in range(1, len(all_points) - 2):
        p0, p1, p2, p3 = all_points[index - 1], all_points[index], all_points[index + 1], all_points[index + 2]
        first = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        second = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        pieces.append((p1, first, second, p2))
    return pieces


def path(pieces):
    """조각들을 SVG 경로의 글로."""
    (x, y) = pieces[0][0]
    out = [f"M{x:.1f} {y:.1f}"]
    for _, (ax, ay), (bx, by), (ex, ey) in pieces:
        out.append(f"C{ax:.1f} {ay:.1f} {bx:.1f} {by:.1f} {ex:.1f} {ey:.1f}")
    return "".join(out)


def along(pieces, steps=12):
    """곡선 위의 점들(조각마다 steps개씩). 뱃길이 땅의 점을 밟는지 볼 때 쓴다."""
    found = []
    for (x0, y0), (x1, y1), (x2, y2), (x3, y3) in pieces:
        for step in range(steps):
            t = step / steps
            a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
            found.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
    found.append(pieces[-1][3])
    return found


def routes(project):
    """뱃길을 그림의 좌표로: {"trunk": 조각들, "branches": [(항구 이름, 조각들)], "whole": [(항구 이름, 부산에서 그 항구까지의 조각들)], "ports": [(이름, x, y)], "home": (x, y)}

    project는 (경도, 위도)를 그림의 (x, y)로 바꾸는 함수다.
    """
    names = [name for name, _, _ in TRUNK]
    spots = [project(lon, lat) for _, lon, lat in TRUNK]
    trunk = spline(spots)
    branches, whole, ports = [], [], []
    for start, rest in BRANCHES:
        at = names.index(start)
        tail = [spots[at]] + [project(lon, lat) for _, lon, lat in rest]
        pieces = spline(tail, before=spots[at - 1])
        port = rest[-1][0]
        branches.append((port, pieces))
        whole.append((port, trunk[:at] + pieces))   # 줄기의 조각 at개가 갈라지는 곳까지다
        ports.append((port, *tail[-1]))
    whole.append((names[-1], trunk))
    ports.append((names[-1], *spots[-1]))
    return {"trunk": trunk, "branches": branches, "whole": whole, "ports": ports, "home": spots[0]}

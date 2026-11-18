"""첫 화면의 점 지도(tools/art/dotmap.py, sealane.py)와 그 그림을 쓰는 꾸밈: 점을 선으로 묶기, 좁은 물길 트기, 뱃길의 짜임, 만들어 둔 그림과 꾸밈의 값이 맞는지."""
import pathlib
import re
import unittest

from tools.art import dotmap, sealane

MODULE = pathlib.Path("site/js/ui/heromap.js")


class DotsTest(unittest.TestCase):
    def test_dots_in_a_row_are_written_as_one_line(self):
        step = dotmap.STEP
        rows = [(10.0, [(5.0, "land"), (5.0 + step, "land"), (5.0 + 2 * step, "eu"), (5.0 + 3 * step, "land"), (5.0 + 5 * step, "land")]),
                (20.0, [(9.0, "eu")])]
        self.assertEqual(dotmap.runs(rows, "land"), f"M5 10h{step + 0.1:.1f}M{5 + 3 * step:g} 10h0.1M{5 + 5 * step:g} 10h0.1")   # 이어진 둘, 떨어진 하나씩
        self.assertEqual(dotmap.runs(rows, "eu"), f"M{5 + 2 * step:g} 10h0.1M9 20h0.1")
        self.assertEqual(dotmap.runs(rows, "kr"), "")

    def test_the_projection_goes_there_and_back(self):
        for lon, lat in ((129.05, 35.1), (4.14, 51.95), (104.1, 1.25)):
            back = dotmap.unproject(*dotmap.project(lon, lat))
            self.assertAlmostEqual(back[0], lon, places=6)
            self.assertAlmostEqual(back[1], lat, places=6)
        x, y = dotmap.project(dotmap.WEST, dotmap.NORTH)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(dotmap.project(dotmap.EAST, dotmap.SOUTH)[0], dotmap.WIDTH)

    def test_narrows_are_opened_and_land_elsewhere_stops_the_build(self):
        routes = sealane.routes(dotmap.project)
        # 지브롤터 해협(좁은 물길) 한가운데와, 뱃길이 지나는 아라비아해 한가운데에 땅의 점을 하나씩 놓는다
        strait = min(sealane.along(routes["trunk"]), key=lambda spot: abs(dotmap.unproject(*spot)[0] + 5.4) + abs(dotmap.unproject(*spot)[1] - 35.95))
        open_sea = min(sealane.along(routes["trunk"]), key=lambda spot: abs(dotmap.unproject(*spot)[0] - 62.0))
        rows = [(strait[1], [(strait[0], "land")]), (open_sea[1], [(open_sea[0], "land")]), (5.0, [(5.0, "land")])]
        carved = dotmap.carve(rows, routes)
        self.assertEqual([len(dots) for _, dots in carved], [0, 1, 1])                 # 좁은 물길의 점만 덜어 낸다
        trodden = dotmap.stepped(carved, routes)
        self.assertTrue(trodden and all(55 < lon < 70 for lon, _ in trodden))          # 넓은 바다에서 땅을 밟으면 알린다
        self.assertEqual(dotmap.stepped([(5.0, [(5.0, "land")])], routes), [])


class LaneTest(unittest.TestCase):
    def setUp(self):
        self.routes = sealane.routes(lambda lon, lat: (lon * 2.0, -lat * 2.0))

    def test_the_curve_passes_through_every_waypoint(self):
        pieces = self.routes["trunk"]
        self.assertEqual(len(pieces), len(sealane.TRUNK) - 1)
        for (start, _, _, end), (_, lon, lat), (_, next_lon, next_lat) in zip(pieces, sealane.TRUNK, sealane.TRUNK[1:]):
            self.assertEqual((start, end), ((lon * 2.0, -lat * 2.0), (next_lon * 2.0, -next_lat * 2.0)))
        for before, after in zip(pieces, pieces[1:]):
            self.assertEqual(before[3], after[0])                                       # 조각은 끊기지 않고 이어진다

    def test_branches_leave_the_trunk_at_a_waypoint_and_whole_routes_start_at_home(self):
        names = [name for name, _, _ in sealane.TRUNK]
        self.assertEqual(len(self.routes["branches"]), len(sealane.BRANCHES))
        for (port, pieces), (start, rest) in zip(self.routes["branches"], sealane.BRANCHES):
            at = names.index(start)
            self.assertEqual(pieces[0][0], self.routes["trunk"][at][0])                 # 갈라지는 곳은 줄기 위의 점이다
            self.assertEqual(port, rest[-1][0])
        ports = [port for port, _ in self.routes["whole"]]
        self.assertEqual(ports, ["피레우스", "코페르", "발렌시아", "르아브르", "로테르담"])
        for _, pieces in self.routes["whole"]:
            self.assertEqual(pieces[0][0], self.routes["home"])                         # 빛은 부산에서 떠난다
            for before, after in zip(pieces, pieces[1:]):
                self.assertEqual(before[3], after[0])
        self.assertEqual([name for name, _, _ in self.routes["ports"]], ports)

    def test_the_path_text_and_the_points_along_it(self):
        pieces = sealane.spline([(0.0, 0.0), (10.0, 0.0), (20.0, 10.0)])
        text = sealane.path(pieces)
        self.assertTrue(text.startswith("M0.0 0.0C") and text.count("C") == 2 and text.endswith("20.0 10.0"))
        points = sealane.along(pieces, steps=4)
        self.assertEqual((len(points), points[0], points[-1]), (9, (0.0, 0.0), (20.0, 10.0)))


class PictureTest(unittest.TestCase):
    """만들어 둔 그림(site/js/ui/heromap.js)과 꾸밈의 값이 만드는 프로그램과 맞는다."""

    @classmethod
    def setUpClass(cls):
        cls.module = MODULE.read_text(encoding="utf-8")
        cls.map = pathlib.Path("site/css/map.css").read_text(encoding="utf-8")
        cls.layout = pathlib.Path("site/css/layout.css").read_text(encoding="utf-8")

    def test_the_picture_was_made_by_this_program(self):
        size = f'viewBox=\\"0 0 {dotmap.WIDTH:.0f} {dotmap.HEIGHT:.0f}\\"'
        self.assertEqual(self.module.count(size), 2)                                    # 아래 장과 위 장
        self.assertEqual(self.module.count('class=\\"map-light\\"'), len(sealane.BRANCHES) + 1)
        self.assertEqual(self.module.count('class=\\"map-port\\"'), len(sealane.BRANCHES) + 1)
        self.assertEqual(self.module.count("map-branch"), len(sealane.BRANCHES))
        for kind in ("map-land", "map-eu", "map-kr"):
            self.assertIn(f'class=\\"map-dots {kind}\\" d=\\"M', self.module)
        self.assertNotIn("<text", self.module)                                          # 지도에는 글을 얹지 않는다
        self.assertLess(len(self.module), 40000)

    def test_the_dot_spacing_and_the_frame_match_the_style_sheets(self):
        dash, gap = re.search(r"\.map-dots \{[^}]*stroke-dasharray: ([\d.]+) ([\d.]+)", self.map).groups()
        self.assertAlmostEqual(float(dash) + float(gap), dotmap.STEP)                   # 점선의 토막과 틈을 더하면 점 사이의 거리다
        frames = re.findall(r"aspect-ratio: (\d+) / (\d+)", self.layout)
        self.assertEqual(set(frames), {(f"{dotmap.WIDTH:.0f}", f"{dotmap.HEIGHT:.0f}")})  # 첫 화면과 머리 띠의 틀이 그림의 크기와 같다

    def test_the_lanes_show_without_motion(self):
        still = self.map.split("@media (prefers-reduced-motion: reduce)")[1]
        self.assertIn("stroke-dashoffset: 0", still)                                    # 움직임을 줄인 기기에서도 뱃길은 그려져 있다
        self.assertIn(".map-light, .map-home-pulse { display: none; }", still)


if __name__ == "__main__":
    unittest.main()

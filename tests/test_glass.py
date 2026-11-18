"""유리 면(글래스모피즘)의 값이 글자를 가리지 않는지: 빛의 바탕과 반투명한 면 위에서의 대비(tools/art/glass.py), 꾸밈 파일의 짜임."""
import pathlib
import re
import unittest

from tools.art import glass

FLOOR = 4.5   # 본문 글자의 대비 기준(WCAG AA)
DARKEST, WHITE, GOLD = "#050b24", "#ffffff", "#ffcc00"   # 흐린 면 뒤로 지나갈 수 있는 것들: 짙은 남색 면, 흰 종이, 노란 단추


class MathTest(unittest.TestCase):
    def test_contrast_follows_the_wcag_formula(self):
        self.assertAlmostEqual(glass.contrast(glass.color("#000000"), glass.color("#ffffff")), 21.0, places=1)
        self.assertAlmostEqual(glass.contrast(glass.color("#777777"), glass.color("#ffffff")), 4.48, places=2)
        self.assertEqual(glass.color("rgba(43, 89, 224, 0.16)"), (43.0, 89.0, 224.0, 0.16))
        self.assertEqual(glass.over((0, 0, 0, 0.5), (255, 255, 255, 1.0)), (127.5, 127.5, 127.5, 1.0))

    def test_a_light_fades_from_its_centre_to_its_edge(self):
        spots = glass.lights("radial-gradient(50vw 50vh at 0% 0%, rgba(0, 0, 0, 0.4), transparent 80%)")
        base = (255.0, 255.0, 255.0, 1.0)
        centre = glass.field_at(base, spots, 1000, 1000, 0, 0)
        half = glass.field_at(base, spots, 1000, 1000, 200, 0)      # 반지름 500의 80%가 끝이므로 그 절반
        self.assertAlmostEqual(centre[0], 255 * 0.6, places=3)
        self.assertAlmostEqual(half[0], 255 * 0.8, places=3)
        self.assertEqual(glass.field_at(base, spots, 1000, 1000, 400, 0), base)   # 끝과 그 밖은 바탕색 그대로
        with self.assertRaises(ValueError):
            glass.lights("radial-gradient(circle at 10% 10%, red, transparent)")   # 읽을 수 없는 꼴은 조용히 넘기지 않는다


class ReadableTest(unittest.TestCase):
    """색 변형마다, 빛이 가장 짙은 곳에서도 글자가 읽힌다."""

    def test_text_straight_on_the_backdrop(self):
        for variant in glass.VARIANTS:
            found = glass.lowest(glass.tokens(variant), ("--ink", "--ink-2", "--ink-3", "--link"))
            for name, value in found.items():
                self.assertGreaterEqual(value, FLOOR, f"{variant} {name}: 빛의 바탕 위 대비 {value:.2f}")

    def test_text_on_panes(self):
        for variant in glass.VARIANTS:
            values = glass.tokens(variant)
            for surface in ("--pane", "--pane-2"):
                found = glass.lowest(values, ("--ink", "--ink-2", "--ink-3", "--link", "--ok", "--warn", "--bad", "--brand-bright"), surface)
                for name, value in found.items():
                    self.assertGreaterEqual(value, FLOOR, f"{variant} {name}: {surface} 위 대비 {value:.2f}")

    def test_text_on_frosted_surfaces_whatever_passes_behind(self):
        for variant in glass.VARIANTS:
            found = glass.frosted(glass.tokens(variant), ("--ink", "--ink-2", "--ink-3", "--link"), (WHITE, DARKEST, "#11256f", GOLD))
            for name, value in found.items():
                self.assertGreaterEqual(value, FLOOR, f"{variant} {name}: 흐린 면 위 대비 {value:.2f}")

    def test_the_header_glass_keeps_its_text_readable(self):
        for variant in glass.VARIANTS:
            values = glass.tokens(variant)
            for behind in (WHITE, DARKEST, GOLD):
                ground = glass.over(glass.color(values["--head-bg"]), glass.color(behind))
                for name in ("--on-deep", "--on-deep-2", "--on-deep-3"):
                    value = glass.contrast(glass.color(values[name]), ground)
                    self.assertGreaterEqual(value, FLOOR, f"{variant} {name}: 머리글 위 대비 {value:.2f}(뒤에 {behind})")


class SheetsTest(unittest.TestCase):
    """꾸밈 파일의 짜임: 유리 면의 값이 한곳에 있고, 뒤를 흐리게 하지 못하는 브라우저에서는 불투명한 면이 된다."""

    @classmethod
    def setUpClass(cls):
        cls.page = pathlib.Path("site/index.html").read_text(encoding="utf-8")
        cls.sheet = pathlib.Path("site/css/glass.css").read_text(encoding="utf-8")
        cls.themes = pathlib.Path("site/css/themes.css").read_text(encoding="utf-8")

    def test_the_glass_sheet_is_loaded_after_the_components_and_before_the_variants(self):
        sheets = re.findall(r'<link rel="stylesheet" href="css/([^"]+)">', self.page)
        self.assertLess(sheets.index("components.css"), sheets.index("glass.css"))
        self.assertLess(sheets.index("glass.css"), sheets.index("themes.css"))
        self.assertEqual(sheets[-1], "themes.css")
        self.assertIn("map.css", sheets)

    def test_every_variant_has_its_own_glass_values(self):
        for variant in glass.VARIANTS:
            values = glass.tokens(variant)
            for name in ("--pane", "--pane-2", "--pane-line", "--frost-bg", "--frost", "--field", "--head-bg", "--head-rest", "--glass-shine"):
                self.assertTrue(values.get(name), f"{variant}: {name}")
            self.assertEqual(len(glass.lights(values["--field"])), 4, variant)
        dark = glass.tokens("midnight")
        self.assertNotEqual(dark["--pane"], glass.tokens("navy")["--pane"])     # 어두운 변형은 어두운 유리를 쓴다

    def test_without_blur_the_floating_surfaces_are_opaque(self):
        plain, blurred = self.sheet.split("@supports", 1)
        names = re.search(r"\n([^\n{]+)\{ background: var\(--surface\); \}", plain).group(1)
        self.assertIn(names.strip(), blurred)                                    # 같은 것들이 흐리게 할 수 있을 때만 반투명해진다
        self.assertIn("backdrop-filter: var(--frost)", blurred)
        for name in (".sheet", ".pdf-bar", ".nav-drop", ".gloss-tip", ".an-nav"):
            self.assertIn(name, names)

    def test_reduced_transparency_turns_the_glass_off(self):
        block = self.themes.split("@media (prefers-reduced-transparency: reduce)")[1]
        for piece in ("--pane: var(--surface)", "--frost-bg: var(--surface)", "--field: none"):
            self.assertIn(piece, block)

    def test_the_header_blurs_on_a_layer_of_its_own(self):
        # 머리글 자체가 뒤를 흐리게 하면 그 안에서 펼쳐지는 목록이 본문을 흐리게 하지 못한다
        layout = pathlib.Path("site/css/layout.css").read_text(encoding="utf-8")
        own = re.search(r"\n\.site-head \{([^}]*)\}", layout).group(1)
        self.assertNotIn("backdrop-filter", own)
        self.assertIn("backdrop-filter", re.search(r"\n\.site-head::before \{([^}]*)\}", layout).group(1))


if __name__ == "__main__":
    unittest.main()

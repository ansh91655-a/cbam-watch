"""유리 면(글래스모피즘) 위에서 글자가 또렷한지 셈한다. 화면의 값(site/css/tokens.css, themes.css)을 읽어 대비를 낸다.

본문 뒤에는 네 귀퉁이에서 번지는 빛(--field)이 깔리고, 판과 카드는 반투명한 면(--pane)이라 그 빛이 비친다.
브라우저의 자동 검사는 이 빛을 보지 못하므로(바탕색만 본다), 빛이 가장 짙은 곳에서의 대비를 여기에서 직접 셈한다.

    python3 -m tools.art.glass        색 변형마다 가장 낮은 대비를 찍는다

값을 고칠 때 손으로 돌리고, 시험(tests/test_glass.py)이 같은 셈으로 4.5:1을 지키는지 본다.
"""
import math
import pathlib
import re
import sys

TOKENS = pathlib.Path("site/css/tokens.css")
THEMES = pathlib.Path("site/css/themes.css")
VARIANTS = ("navy", "white", "midnight")
# 빛의 바탕을 셈해 보는 화면의 크기(너비, 높이): 폰, 패드, 노트북, 모니터
SCREENS = ((390, 844), (768, 1024), (1440, 900), (1920, 1080), (2560, 1440))
GRID = 24   # 화면을 가로세로 이만큼으로 나눠 본다
GRADIENT = re.compile(r"radial-gradient\(\s*([\d.]+)vw\s+([\d.]+)vh\s+at\s+([\d.]+)%\s+([\d.]+)%\s*,\s*(rgba?\([^)]*\))\s*,\s*transparent\s+([\d.]+)%\s*\)")


def color(text):
    """'#rrggbb'나 'rgb(a)(…)'를 (r, g, b, a)로."""
    text = text.strip()
    if text.startswith("#"):
        value = text[1:]
        return tuple(int(value[at:at + 2], 16) for at in (0, 2, 4)) + (1.0,)
    numbers = [float(number) for number in re.findall(r"[\d.]+", text)]
    return (numbers[0], numbers[1], numbers[2], numbers[3] if len(numbers) > 3 else 1.0)


def over(top, base):
    """반투명한 top을 base 위에 얹은 빛깔."""
    alpha = top[3]
    return tuple(top[at] * alpha + base[at] * (1 - alpha) for at in range(3)) + (1.0,)


def luminance(rgb):
    def linear(value):
        value /= 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * linear(rgb[0]) + 0.7152 * linear(rgb[1]) + 0.0722 * linear(rgb[2])


def contrast(first, second):
    """두 빛깔의 대비(WCAG의 셈). 1에서 21 사이."""
    one, two = luminance(first), luminance(second)
    return (max(one, two) + 0.05) / (min(one, two) + 0.05)


def _declared(block):
    return {name: value.strip() for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block)}


def tokens(variant="navy"):
    """색 변형의 값들. 기본(navy)은 tokens.css의 값이고, 다른 변형은 themes.css가 덮어쓴 값을 얹는다."""
    found = _declared(TOKENS.read_text(encoding="utf-8").split("\n}")[0])
    if variant != "navy":
        body = THEMES.read_text(encoding="utf-8").split(f'html[data-theme="{variant}"] {{')[1].split("\n}")[0]
        found.update(_declared(body))
    return found


def lights(field):
    """--field에 적힌 빛들: [{"rx", "ry"(화면 너비·높이에 대한 비율), "cx", "cy", "color", "end"}]. 적힌 차례대로(앞의 것이 위에 놓인다)."""
    found = [{"rx": float(rx) / 100, "ry": float(ry) / 100, "cx": float(cx) / 100, "cy": float(cy) / 100, "color": color(tint), "end": float(end) / 100}
             for rx, ry, cx, cy, tint, end in GRADIENT.findall(field)]
    if len(found) != field.count("radial-gradient("):
        raise ValueError("--field의 꼴을 읽지 못함: radial-gradient(<가로>vw <세로>vh at <x>% <y>%, <빛깔>, transparent <끝>%)로 적어야 한다")
    return found


def field_at(base, spots, width, height, x, y):
    """화면(width × height)의 (x, y)에서 빛의 바탕이 내는 빛깔. base는 바탕색."""
    shown = base
    for spot in reversed(spots):   # 뒤에 적힌 빛이 아래에 깔린다
        reach = math.hypot((x - spot["cx"] * width) / (spot["rx"] * width), (y - spot["cy"] * height) / (spot["ry"] * height))
        if reach >= spot["end"]:
            continue
        red, green, blue, alpha = spot["color"]
        shown = over((red, green, blue, alpha * (1 - reach / spot["end"])), shown)
    return shown


def backdrops(values):
    """바탕색 위에 빛이 번진 빛깔들: 여러 화면 크기에서 촘촘히 본 것."""
    base = color(values["--bg"])
    spots = lights(values.get("--field", ""))
    return [field_at(base, spots, width, height, width * column / GRID, height * row / GRID)
            for width, height in SCREENS for row in range(GRID + 1) for column in range(GRID + 1)]


def lowest(values, names, surface=None):
    """글자 빛깔(names의 값)마다, 빛의 바탕 어디에서든 나올 수 있는 가장 낮은 대비: {이름: 대비}.

    surface를 주면 그 반투명한 면(--pane 따위)을 빛의 바탕 위에 얹고 그 위의 글자로 셈한다.
    """
    grounds = backdrops(values)
    if surface:
        grounds = [over(color(values[surface]), ground) for ground in grounds]
    return {name: min(contrast(color(values[name]), ground) for ground in grounds) for name in names}


def frosted(values, names, behind):
    """뒤를 흐리게 하는 면(--frost-bg) 위의 글자: 뒤에 behind 빛깔들이 지나갈 때의 가장 낮은 대비."""
    grounds = [over(color(values["--frost-bg"]), color(shade)) for shade in behind]
    return {name: min(contrast(color(values[name]), ground) for ground in grounds) for name in names}


def main():
    for variant in VARIANTS:
        values = tokens(variant)
        bare = lowest(values, ("--ink", "--ink-2", "--ink-3", "--link"))
        pane = lowest(values, ("--ink-3", "--link", "--ok", "--warn", "--bad", "--brand-bright"), "--pane")
        print(variant)
        print("  빛의 바탕 위: " + ", ".join(f"{name} {value:.2f}" for name, value in bare.items()))
        print("  판 위: " + ", ".join(f"{name} {value:.2f}" for name, value in pane.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

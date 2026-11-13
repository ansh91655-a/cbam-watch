"""국문 PDF에 쓰는 글꼴: 원문의 글꼴에 맞추어 고르고, 글자마다 찍을 글꼴을 정하고, 폭을 잰다.

글꼴 파일은 assets/fonts에 있다(모두 SIL Open Font License 1.1, 허락글이 같은 폴더에 있다).
- 민글꼴 문서(Arial, Calibri, EC Square Sans 등): Pretendard
- 부리글꼴 문서(Times New Roman 등): 한글은 나눔명조, 로마자·숫자·문장부호는 Tinos(Times New Roman과 폭이 같은 글꼴)
어느 글꼴에도 없는 글자는 뜻이 같은 흔한 글자로 바꾸고, 그래도 없으면 빼고 알린다.
"""

import functools
import pathlib
import re
import unicodedata

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HOME = pathlib.Path(__file__).resolve().parents[2] / "assets" / "fonts"
FACES = {
    ("sans", False): "Pretendard-Regular", ("sans", True): "Pretendard-Bold",
    ("serif", False): "NanumMyeongjo-Regular", ("serif", True): "NanumMyeongjo-Bold",
    ("roman", False): "Tinos-Regular", ("roman", True): "Tinos-Bold",
}
ORDER = {"sans": ("sans", "serif", "roman"), "serif": ("serif", "sans", "roman")}
SERIF = re.compile(r"times|cambria|georgia|garamond|palatino|serif|antiqua|minion|century|tinos|myeongjo|batang", re.I)
BOLD = re.compile(r"bold|black|heavy|demi", re.I)
SWAPS = {"⚫": "●", "∙": "·", "∗": "*", "­": "", "​": "", "﻿": "", "\t": " ", "\n": " ", "\r": " "}
EMPTY = re.compile(r"\(\s*\)|\[\s*\]")      # 글자가 빠져 속이 빈 괄호
missing = set()     # 어느 글꼴에도 없어 빼 버린 글자(만든 뒤에 알린다)


def family(name):
    """원문 글꼴 이름에 맞는 갈래: "serif" 또는 "sans"."""
    return "serif" if SERIF.search(name or "") else "sans"


def bold(name):
    return bool(BOLD.search(name or ""))


@functools.lru_cache(maxsize=None)
def _widths():
    """{(갈래, 굵기): {글자 번호: 폭(1000분의 1 em)}}. 처음 부를 때 글꼴을 등록한다."""
    widths = {}
    for role, name in FACES.items():
        pdfmetrics.registerFont(TTFont(name, str(HOME / f"{name}.ttf")))
        widths[role] = pdfmetrics.getFont(name).face.charWidths
    return widths


def _latin(code):
    return code < 0x0250 or 0x2000 <= code <= 0x206F or 0x20A0 <= code <= 0x20CF


@functools.lru_cache(maxsize=None)
def face(char, kind, heavy):
    """이 글자를 찍을 (글꼴 이름, 폭). 어느 글꼴에도 없으면 (None, 0)."""
    widths = _widths()
    code = ord(char)
    roles = ORDER[kind]
    if kind == "serif" and _latin(code):
        roles = ("roman",) + roles
    for role in roles:
        width = widths[(role, heavy)].get(code)
        if width is not None:
            return FACES[(role, heavy)], width
    return None, 0


def tidy(text, kind="sans", heavy=False):
    """찍을 수 있는 글자로만 된 글. 빈칸은 하나로 줄인다."""
    out = []
    for char in text:
        char = SWAPS.get(char, char)
        for one in char:
            if face(one, kind, heavy)[0]:
                out.append(one)
                continue
            plain = unicodedata.normalize("NFKC", one)
            if plain != one and all(face(each, kind, heavy)[0] for each in plain):
                out.append(plain)
            else:
                missing.add(one)
    return " ".join(EMPTY.sub("", "".join(out)).split())


def width(text, kind, heavy, size):
    return sum(face(char, kind, heavy)[1] for char in text) * size / 1000.0


def pieces(text, kind, heavy):
    """[(글꼴 이름, 글)] — 같은 글꼴로 찍는 글자끼리 묶는다."""
    out = []
    for char in text:
        name = face(char, kind, heavy)[0]
        if not name:
            continue
        if out and out[-1][0] == name:
            out[-1][1].append(char)
        else:
            out.append((name, [char]))
    return [(name, "".join(chars)) for name, chars in out]

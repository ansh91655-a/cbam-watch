"""국문 PDF에 쓰는 글꼴: 번역은 모두 Pretendard로 찍는다(원문이 굵은 글씨면 굵게). 폭을 재고, 찍을 수 없는 글자를 가린다.

글꼴 파일은 assets/fonts에 있다(SIL Open Font License 1.1, 허락글이 같은 폴더에 있다).
글꼴에 없는 글자는 뜻이 같은 흔한 글자로 바꾸고(수식 글자 → 여느 글자), 그래도 없으면 빼고 알린다(missing).
"""

import functools
import pathlib
import re
import unicodedata

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HOME = pathlib.Path(__file__).resolve().parents[2] / "assets" / "fonts"
FACES = {False: "Pretendard-Regular", True: "Pretendard-Bold"}     # 굵기 → 글꼴 이름
BOLD = re.compile(r"bold|black|heavy|demi", re.I)
SWAPS = {"⚫": "●", "∙": "·", "∗": "*", "­": "", "​": "", "﻿": "", "\t": " ", "\n": " ", "\r": " "}
EMPTY = re.compile(r"\(\s*\)|\[\s*\]")      # 글자가 빠져 속이 빈 괄호
missing = set()     # 글꼴에 없어 빼 버린 글자(만든 뒤에 알린다)


def bold(name):
    """원문 글꼴의 이름으로 굵은 글씨인지 안다."""
    return bool(BOLD.search(name or ""))


@functools.lru_cache(maxsize=None)
def _widths():
    """{굵기: {글자 번호: 폭(1000분의 1 em)}}. 처음 부를 때 글꼴을 등록한다."""
    widths = {}
    for heavy, name in FACES.items():
        pdfmetrics.registerFont(TTFont(name, str(HOME / f"{name}.ttf")))
        widths[heavy] = pdfmetrics.getFont(name).face.charWidths
    return widths


def has(char, heavy=False):
    return ord(char) in _widths()[heavy]


def tidy(text, heavy=False):
    """찍을 수 있는 글자로만 된 글. 빈칸은 하나로 줄인다."""
    out = []
    for char in text:
        for one in SWAPS.get(char, char):
            if has(one, heavy):
                out.append(one)
                continue
            plain = unicodedata.normalize("NFKC", one)
            if plain != one and all(has(each, heavy) for each in plain):
                out.append(plain)
            else:
                missing.add(one)
    return " ".join(EMPTY.sub("", "".join(out)).split())


def width(text, heavy, size):
    widths = _widths()[heavy]
    return sum(widths.get(ord(char), 0) for char in text) * size / 1000.0


def face(heavy):
    """찍을 글꼴의 이름(등록되어 있게 한다)."""
    _widths()
    return FACES[heavy]

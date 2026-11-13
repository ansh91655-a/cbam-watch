"""원문 PDF에서 줄과 낱말의 자리를 읽는다. 받기와 쓰기는 하지 않는다.

pdftotext -bbox-layout이 내는 것(쪽 > 흐름 > 덩이 > 줄 > 낱말, 자리는 쪽의 왼쪽 위에서 잰 포인트)을 읽는다.
규정 원문 화면의 글도 같은 프로그램(pdftotext)이 뽑은 것이라, 줄의 글자가 그대로 맞는다.
"""
import html
import re
import subprocess

PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
BLOCK = re.compile(r'<block xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" yMax="([\d.-]+)">(.*?)</block>', re.S)
LINE = re.compile(r'<line xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" yMax="([\d.-]+)">(.*?)</line>', re.S)
WORD = re.compile(r'<word xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" yMax="([\d.-]+)">(.*?)</word>', re.S)


def _box(values):
    return tuple(round(float(value), 2) for value in values)


def parse(xhtml):
    """[{"width", "height", "lines": [{"box": (x0, y0, x1, y1), "text", "words": [{"box", "text"}], "block": 덩이의 차례}]}]"""
    pages = []
    for width, height, body in PAGE.findall(xhtml):
        lines = []
        for order, block in enumerate(BLOCK.finditer(body)):
            for line in LINE.finditer(block.group(5)):
                words = [{"box": _box(word.groups()[:4]), "text": html.unescape(word.group(5))} for word in WORD.finditer(line.group(5))]
                if words:
                    lines.append({"box": _box(line.groups()[:4]), "text": " ".join(word["text"] for word in words), "words": words, "block": order})
        pages.append({"width": float(width), "height": float(height), "lines": lines})
    return pages


def read(path):
    """PDF 파일의 쪽들. pdftotext가 없거나 실패하면 RuntimeError."""
    done = subprocess.run(["pdftotext", "-bbox-layout", str(path), "-"], capture_output=True, timeout=600)
    if done.returncode != 0:
        raise RuntimeError(f"pdftotext 실패: {done.stderr.decode('utf-8', 'replace')[:200]}")
    return parse(done.stdout.decode("utf-8", "replace"))

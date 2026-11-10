"""찍은 그림을 줄여 site/assets/thumbs/에 쓰고, 실패한 것은 기록해 둔다.

쓰는 법: python -m tools.thumbs.finish <할 일 파일> <그림을 둔 폴더>
화면 그림(가로 960)은 그대로 줄이고, PDF 첫 장은 머리 띠(기관 이름과 로고가 있는 맨 위 덩어리)를 찾아 그 아래부터 가로 16 : 세로 10으로 잘라 줄인다.
거의 비어 있는 그림은 쓰지 않는다. 실패는 collected/thumbs/state.json에 횟수와 사유를 적고, 세 번 실패한 원문은 다시 시도하지 않는다.
"""
import pathlib
import sys

from PIL import Image

from tools.common.jsonio import read_json, stamp, write_json
from tools.publish import thumbs
from tools.thumbs.plan import STATE

SIZE = (480, 300)
PDF_TOP = 0.14      # 머리 띠를 찾지 못한 PDF 첫 장에서 건너뛰는 윗부분
BLANK = 0.992       # 흰 점이 이 비율을 넘으면 빈 그림으로 본다


def letterhead_end(image):
    """PDF 첫 장에서 머리 띠(기관의 로고와 이름이 있는 맨 위 덩어리)가 끝나는 높이를 0~1로 돌려준다.

    위에서부터 글이나 그림이 있는 첫 덩어리를 찾고, 그 아래에 처음 나오는 넓은 빈 띠까지를 머리 띠로 본다.
    첫 덩어리가 쪽의 위쪽 4분의 1을 넘어가면(머리 띠가 따로 없는 문서) 정해 둔 값(PDF_TOP)을 쓴다.
    """
    gray = image.convert("L").resize((200, 800))
    rows = [sum(1 for value in gray.crop((0, y, 200, y + 1)).getdata() if value < 225) > 1 for y in range(800)]
    start = next((y for y, ink in enumerate(rows) if ink), None)
    if start is None:
        return PDF_TOP
    gap, need = 0, 10  # 빈 줄이 10줄(쪽 높이의 1.25%) 이어지면 덩어리가 끝난 것으로 본다
    for y in range(start, 800):
        gap = 0 if rows[y] else gap + 1
        if gap >= need:
            end = (y - need + 1) / 800
            return end + 0.006 if end <= 0.25 else PDF_TOP
    return PDF_TOP


def window(image, kind):
    """그림에서 쓸 부분(가로 16 : 세로 10)을 잘라 낸다. PDF 첫 장은 머리 띠 아래부터 쓴다."""
    width, height = image.size
    top = int(height * letterhead_end(image)) if kind == "pdf" else 0
    return image.crop((0, top, width, min(height, top + int(width * SIZE[1] / SIZE[0]))))


def blank(image):
    small = image.convert("L").resize((96, 60))
    pixels = list(small.getdata())
    return sum(1 for value in pixels if value > 244) / len(pixels) > BLANK


def make(source, kind, target):
    """source 그림을 줄여 target에 쓴다. 됐으면 빈 글, 아니면 사유."""
    try:
        image = Image.open(source).convert("RGB")
    except Exception as error:
        return f"그림을 열지 못함: {type(error).__name__}"
    part = window(image, kind)
    if part.height < part.width * 0.4:
        return "그림이 너무 낮음"
    if blank(part):
        return "빈 그림"
    canvas = Image.new("RGB", (part.width, int(part.width * SIZE[1] / SIZE[0])), "white")
    canvas.paste(part, (0, 0))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize(SIZE, Image.LANCZOS).save(target, "WEBP", quality=82, method=6)
    return ""


def main(argv):
    jobs, raw = read_json(argv[0], []), pathlib.Path(argv[1])
    reported = {row["name"]: row for name in ("pages.json", "pdfs.json") for row in read_json(raw / name, [])}
    state = read_json(STATE, {"failed": {}})
    failed, made = state.setdefault("failed", {}), 0
    for job in jobs:
        row = reported.get(job["name"], {"ok": False, "why": "결과가 없음"})
        why = row.get("why", "") if not row.get("ok") else make(raw / f"{job['name']}.png", job["kind"], thumbs.path_of(job["name"]))
        if why:
            entry = failed.setdefault(job["name"], {"url": job["url"], "tries": 0})
            entry.update({"tries": entry["tries"] + 1, "why": why, "at": stamp()})
        else:
            failed.pop(job["name"], None)
            made += 1
    state["updatedAt"] = stamp()
    write_json(STATE, state)
    print(f"그림 {made}건을 만듦, 실패 {len(jobs) - made}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

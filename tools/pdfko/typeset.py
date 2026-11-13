"""앉힐 자리가 정해진 국문을 원문과 같은 크기의 빈 쪽들에 찍는다(reportlab). 이 쪽들을 원문 위에 겹친다.

쪽마다 맨 위에 비공식 번역임을 알리는 글을 넣고(첫 쪽에는 띠를 둘러 굵게), 기관의 표장은 가린다. 같은 입력이면 같은 파일이 나오도록 만든 때는 적지 않는다.
"""

import io

from reportlab.pdfgen import canvas

from tools.pdfko import fonts

NOTICE = "비공식 국문 번역입니다. 유럽연합 집행위원회의 공식 문서가 아니며, 원문과 다를 때에는 원문이 우선합니다."
NOTICE_SIZE = 6.5
NOTICE_TOP = 13.0       # 쪽 위 끝에서 알림 글의 밑금까지
NOTICE_INK = (0.35, 0.35, 0.35)
BANNER = "비공식 국문 번역본 — 유럽연합 집행위원회의 공식 문서가 아닙니다. 원문과 다를 때에는 원문이 우선합니다."
BAND_HEIGHT, BAND_SIZE = 22.0, 8.5
BAND_FILL, BAND_INK = (0.93, 0.93, 0.93), (0.15, 0.15, 0.15)
MARK = "비공식 국문 번역본"      # 기관 표장을 가린 자리에 적는 글
MARK_SIZE = 10.5


def _line(sheet, x, y, text, heavy, size, color):
    writer = sheet.beginText(x, y)
    writer.setFillColorRGB(*color)
    writer.setFont(fonts.face(heavy), size)
    writer.textOut(text)
    sheet.drawText(writer)


def overlay(sizes, jobs, masks=None):
    """겹칠 쪽들을 PDF 바이트로 돌려준다.

    sizes는 쪽마다의 (너비, 높이), jobs는 {쪽: [그릴 줄, …]}(layout.place가 주는 꼴, 좌표는 왼쪽 위가 원점),
    masks는 {쪽: [(x0, 위, x1, 아래), …]} — 흰 네모로 가리고 비공식 번역본임을 적을 자리(기관의 표장).
    """
    buffer = io.BytesIO()
    notice, banner = fonts.tidy(NOTICE), fonts.tidy(BANNER, True)
    sheet = canvas.Canvas(buffer, pagesize=sizes[0], invariant=1, pageCompression=1, initialFontName=fonts.face(False))
    for number, (width, height) in enumerate(sizes):
        sheet.setPageSize((width, height))
        for x0, top, x1, bottom in (masks or {}).get(number, []):
            sheet.setFillColorRGB(1, 1, 1)
            sheet.rect(x0, height - bottom, x1 - x0, bottom - top, stroke=0, fill=1)
            _line(sheet, x0, height - (top + bottom) / 2 - MARK_SIZE * 0.35, MARK, True, MARK_SIZE, NOTICE_INK)
        for job in jobs.get(number, []):
            _line(sheet, job["x"], height - job["base"], job["text"], job["heavy"], job["size"], job["color"])
        if number == 0:     # 첫 쪽에는 띠를 두르고 굵게 적는다(표지가 기관의 공식 문서로 보이지 않게)
            sheet.setFillColorRGB(*BAND_FILL)
            sheet.rect(0, height - BAND_HEIGHT, width, BAND_HEIGHT, stroke=0, fill=1)
            size = min(BAND_SIZE, BAND_SIZE * (width - 24) / max(fonts.width(banner, True, BAND_SIZE), 1))
            _line(sheet, (width - fonts.width(banner, True, size)) / 2, height - BAND_HEIGHT / 2 - size * 0.35, banner, True, size, BAND_INK)
        else:
            wide = fonts.width(notice, False, NOTICE_SIZE)
            _line(sheet, (width - wide) / 2, height - NOTICE_TOP, notice, False, NOTICE_SIZE, NOTICE_INK)
        sheet.showPage()
    sheet.save()
    return buffer.getvalue()

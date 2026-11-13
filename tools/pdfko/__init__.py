"""PDF로 받은 문서의 국문 PDF를 만든다: 원문과 같은 쪽, 같은 자리에 번역을 앉힌다.

- geometry: 원문 PDF에서 줄과 낱말의 자리를 읽는다(pdftotext -bbox-layout).
- match: 규정 원문 화면의 문단(tools.laws.corpus)이 원문의 어느 줄들인지 찾는다.
- style: 줄마다의 글자 크기, 굵기, 빛깔을 읽는다(pdfminer).
- erase: 번역으로 바꿀 줄의 원문 글자를 보이지 않게 한다(pikepdf).
- typeset: 그 자리에 국문을 앉힌다(reportlab).
- build: 문서 하나의 국문 PDF를 만들고 얼마나 앉혔는지 알린다.
"""

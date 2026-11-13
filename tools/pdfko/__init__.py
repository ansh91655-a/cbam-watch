"""PDF로 받은 문서를 다룬다: PDF에 적힌 짜임에서 뜻 단위를 읽고, 원문과 같은 쪽·같은 자리에 번역을 앉힌 국문 PDF를 만든다.

읽기
- geometry: 줄과 낱말의 자리(pdftotext -bbox-layout)
- glyphs: 글자 하나하나의 자리·글꼴·빛깔, 그 글자를 찍은 연산자의 차례와 내용 조각 번호(pdfminer)
- tags: 구조 꼬리표(구조 트리)
- units: 뜻 단위(제목, 문단, 목록 항목, 표의 칸, 각주 …). 규정 원문 화면이 이것으로 문단을 나눈다(originals/units)

국문 PDF 만들기
- bind: 단위를 원문의 글자와 줄에 잇는다
- match: 꼬리표가 없는 PDF에서는 문단의 글을 원문의 낱말에 맞추어 자리를 찾는다
- layout: 번역을 앉힐 자리(줄 칸, 너비, 글자 크기)를 정한다
- erase: 번역으로 바꿀 자리의 원문 글자를 들어낸다(pikepdf)
- fonts, typeset: 그 자리에 국문을 찍는다(reportlab, assets/fonts의 Pretendard)
- build: 문서 하나의 국문 PDF를 만들고 얼마나 앉혔는지 알린다
"""

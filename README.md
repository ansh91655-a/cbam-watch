# cbam-watch

EU 탄소국경조정제도(CBAM)의 규제 동향을 원문과 함께 정리해 보여 주는 사이트의 저장소입니다.

- 사이트: https://ansh91655-a.github.io/cbam-watch/
- 사이트의 정리와 번역은 자동으로 수집하고 작성한 것이며, 게시 전에 사람이 검수하지 않습니다. 정확한 내용은 반드시 원문에서 확인하세요. 법률 자문이 아닙니다.

## 하루의 흐름

| 때(한국 시각) | 누가 | 하는 일 |
| --- | --- | --- |
| 평일 06:10 | 이 저장소의 자동 실행(`.github/workflows/collect.yml`) | 출처 화면을 받아 새로 보인 링크, 날짜로 시작하는 소식, 표의 행, 문장을 `collected/feed/`에 적는다. 인증서 가격표를 읽어 `data/prices.json`을 만든다. EU 집행위원회 문서를 다시 받아 판이 바뀌었는지 보고, 바뀌면 이전 판과 문단 단위로 비교한다 |
| 평일 07:05 | 예약된 작성 실행 | 목록에서 소식을 골라 국문 초안을 쓴다. EU 공식 자료는 근거가 된 원문 대목을 함께 남긴다 |
| 평일 08:20 | 예약된 검증 실행 | 초안을 원문과 다시 대조하고, 통과한 것만 `data/`에 더한다. 이어서 공식 기록에 새로 생긴 사건을 규제별 진행 상황(`data/regulations.json`)에 반영한다 |
| 바뀔 때마다 | 이 저장소의 자동 실행(`.github/workflows/pages.yml`) | 사이트를 다시 만들어 배포한다 |
| 평일 10:05 | 예약된 보고 실행 | 그날의 실행과 사이트 상태를 확인하고 보고 파일을 `reports/`에 올린다 |
| 보고 파일이 올라올 때, 평일 11:10 | 이 저장소의 자동 실행(`.github/workflows/notify.yml`) | 문제가 있는 보고와 주간 보고를 '운영 보고' 이슈에 댓글로 적는다(GitHub가 저장소 주인에게 메일로 알린다). 11:10까지 그날의 보고 파일이 없으면 그것도 알린다 |
| 월요일 09:10 | 예약된 주간 실행 | 주간 요약을 쓰고, 게시한 항목 일부를 지금의 원문과 다시 대조한다. 어긋나면 그 항목의 요약을 내린다. 규제별 진행 상황에서 날짜가 지난 일정과 언론 보도에 기댄 줄을 다시 확인한다 |

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `sources/registry.json` | 출처 대장. 어디를 어떤 방법으로 보는지 적혀 있다 |
| `collected/` | 수집 결과. `feed/`(그날 새로 보인 것), `state/`(이미 본 것의 열쇠), `pages/`(EU 공식 화면의 글), `status.json`(출처별 확인 결과), `archive/`(지난 소식을 한꺼번에 모은 것. 아래 '지난 소식 채우기' 참조) |
| `originals/` | EU 집행위원회 문서의 사본(`files/<문서 id>/<해시>/<원래 파일 이름>`), 뽑아 낸 본문(`text/`), 판 사이의 비교 결과(`diffs/`), 대장(`state.json`) |
| `data/` | 사이트에 게시한 데이터. 소식(`items.json`), 주제 목록(`topics.json`), 인증서 가격(`prices.json`, 프로그램이 가격표에서 만든다), 일정(`events.json`), 주간 요약(`digests.json`), 용어집(`terms.json`) |
| `reports/` | 보고 실행이 올리는 그날과 그 주의 보고 파일. 알림의 근거다 |
| `language/` | 국문 표기 기준(용어집) |
| `site/` | 공개 사이트의 화면 파일. 화면마다 모듈 하나(`js/views/`), 그림과 달력 같은 부품(`js/ui/`), 디자인 값(`css/tokens.css`)과 색 변형(`css/themes.css`), 파비콘과 공유 미리보기 그림과 라이선스 고지(`assets/`). 아래 '사이트의 디자인' 참조 |
| `console/` | 운영 화면의 파일 |
| `tools/` | 정해진 일을 하는 프로그램. 아래 표 참조 |
| `tests/` | 도구의 자동 시험. 올릴 때마다 돈다(`.github/workflows/tests.yml`) |

### tools

| 묶음 | 하는 일 |
| --- | --- |
| `tools/common` | 웹에서 받기, HTML에서 글 뽑기, JSON 읽고 쓰기 |
| `tools/collect` | 출처 화면에서 새 항목 찾기(`extract`), JSON 목록 보기(`jsonwatch`), 그날 목록 만들기(`feed`), 실행(`run`) |
| `tools/originals` | 문서 링크 찾기(`discover`), 받을 차례 정하기(`queue`), 판 남기기와 비교(`versions`, `diff`), 본문 뽑기(`textify`), 실행(`run`) |
| `tools/check` | 국문 글 검사: 용어(`term_check`, `term_lookup`), 표기(`style_check`), 수치와 날짜 대조(`fact_check`), 원문 발췌 확인(`excerpt_check`) |
| `tools/prices` | 인증서 가격표 읽기: 적용 기간 읽기(`periods`), 표의 행 읽기(`parse`), 가격 자료 만들기(`run`) |
| `tools/publish` | 게시 데이터에 더하기(`add_items`, `add_digest`), 요약 내리기(`withdraw`), 주제 목록(`topics`), 사이트와 운영 화면의 폴더 만들기(`build_site`, `build_console`) |
| `tools/notify` | 보고 파일에서 알릴 것을 골라 '운영 보고' 이슈에 적기(`reports`, `messages`, `github`, `run`) |
| `tools/run` | 예약 실행이 쓰는 보조 도구: 후보 고르기, 검증 대기 고르기, 원문 발췌 자르기, 상태 점검, 하루와 한 주의 요약, 보고 파일 만들기(`write_report`) |
| `tools/archive` | 공식 기록을 모으는 프로그램. 지난 소식을 한꺼번에 채울 때 손으로 돌리고, 규제 진행 상황에 쓰는 기록은 평일마다 자동으로 돈다: 출처별 모으기(`ecnews`, `newsletter`, `eurlex`, `cellar`, `docs`, `oeil`, `hys`, `presscorner`, `council`, `govuk`, `ukleg`, `fedreg`, `boards`)와 실행(`crawl`), 새 자료를 그날의 후보로 넘기기(`tofeed`), 화면의 짜임 살펴보기(`dump`), 싣기 전 검사(`gate`), 싣기(`publish`) |
| `tools/art` | 사이트의 그림을 만드는 프로그램. 손으로 돌린다: 점 지도(`dotmap`), 아이콘(`icons`), 라이선스 고지(`notices`), 공유 미리보기 그림의 원본(`social.html`) |

프로그램은 저장소 맨 위에서 `python3 -m tools.<묶음>.<이름>` 꼴로 돌립니다. 표준 라이브러리만 쓰고, PDF 본문을 뽑을 때만 `pdftotext`가 필요합니다. 시험은 `python3 -m unittest discover -s tests -t .`로 돌립니다.

## 규제별 진행 상황

사이트의 '규제' 화면은 `data/regulations.json` 하나로 그린다. 규제마다 지금의 단계, 현재 상황, 다음 단계, 연혁(사건마다 원문 주소)을 가진다.

- 연혁의 근거는 세 가지다. `stored`는 `collected/archive/`에 모아 둔 공식 기록과 맞는 사건이고 프로그램이 실제로 맞춰 본다. `web`은 자동으로 받을 수 없는 공식 화면을 읽고 확인한 사건, `press`는 언론 보도로만 아는 사건이다(화면에 '언론 보도'로 표시된다).
- 검사: `python -m tools.publish.regulations`(꼴, 높임말, 용어, 근거). 사이트를 만들 때는 꼴과 표기만 막고, 근거가 공식 기록과 달라진 것은 알리기만 한다(공식 기록은 날마다 바뀐다).
- 고치기: `python -m tools.publish.rule_edit`(연혁에 한 줄 더하기와 빼기, 단계와 설명 고치기, 새 규제 더하기). 고친 뒤 자료 전체를 검사하고, 걸리면 고치지 않는다.
- 달라진 것 찾기: `python -m tools.run.rules_watch`가 모아 둔 공식 기록이 지난번에 본 뒤로 달라졌는지 알려 준다. 본 것은 `data/rules-seen.json`에 적는다.
- 상태 점검: `tools/run/rules_health.py`가 근거 어긋남, 지난 일정, 반영되지 않은 변화, 기록 갱신 누락을 일일 보고의 문제로 올린다.

## 지난 소식 채우기

사이트를 연 날보다 앞선 소식(2025년 1월부터)은 평소의 자동 실행과 따로 한 번에 채웠습니다. 같은 일을 다시 할 때의 차례입니다.

1. 모으기. 워크플로 '소급 수집'(`.github/workflows/archive.yml`)을 손으로 돌립니다. `mode`를 `crawl`로 두고 `steps`에 출처 이름을 띄어 적으면 그 출처만 돕니다(비우면 모두). 결과는 `collected/archive/`에 쌓입니다. 출처마다 목록(`<출처>.json`), 재이용이 허용된 자료의 원문 글(`pages/`), 실행 결과(`report/`)가 있습니다.
   - `ec-news`: EU 집행위원회 조세·관세총국 소식. 사이트 지도에서 소식 주소를 얻어 본문에 CBAM이 나오는 것만 남깁니다.
   - `ec-newsletter`: EU 집행위원회가 보내는 CBAM Newsletter의 보관함. `eur-lex`: CBAM 법령의 제목, 채택일, 관보 게재일, 시행과 적용에 관한 조문(EU 출판국의 자료 창구에서 받습니다).
   - `ep-oeil`: 유럽의회 입법 관측소의 절차 기록. `ec-hys`: 의견수렴 목록. `uk-govuk`: 영국 정부 CBAM 문서의 변경 기록.
   - `kr-boards`: 국내 기관 게시판의 제목, 날짜, 주소. 본문은 받아 두지 않습니다(산업통상부 보도자료만 부제와 첫 문단을 짧게 남깁니다).
2. 쓰기. 모아 둔 글을 읽고 국문 초안을 만듭니다. 초안 파일은 저장소에 올리지 않습니다.
3. 싣기. `python3 -m tools.archive.publish --drafts <초안 파일> [--dry-run]`. 형식, 문체, 용어, 원문 대조(수치와 날짜, 게시일), 링크, 원문 발췌를 검사해 통과한 것만 `data/items.json`에 더하고 `backfill` 표시를 붙입니다. 이 표시가 있는 소식은 주간 요약의 대상에서 빠지고, 주간 작업이 주마다 10건씩 원문과 다시 대조합니다.

## 사이트의 디자인

- 색은 EU 깃발의 파랑(#003399)과 노랑(#FFCC00)을 빌렸습니다. 깃발(별 열두 개)과 EU 기관의 로고는 쓰지 않습니다. 개인이 운영하는 비공식 사이트입니다.
- 색 변형은 세 가지입니다: 네이비(기본), 화이트, 미드나잇. 주소에 `?theme=white`처럼 붙이면 바꿔 볼 수 있고, 기본값은 `site/js/theme.js`의 `DEFAULT`입니다. 변형마다 달라지는 값은 `site/css/themes.css`에만 있습니다.
- CSS는 쓰임새로 나눴습니다: 값(`tokens`), 바탕(`base`), 틀과 큰 머리와 지도(`layout`), 여러 화면이 함께 쓰는 부품(`components`), 첫 화면(`home`), 화면마다 따로 쓰는 것(`views`), 가격 그림(`chart`), 일정(`calendar`), 색 변형(`themes`).
- 그림은 사진 없이 직접 만든 것과 자유롭게 쓸 수 있는 것만 씁니다.

| 그림 | 어디서 왔나 | 만드는 법 |
| --- | --- | --- |
| 점 지도(`site/js/ui/heromap.js`) | 나라 경계는 Natural Earth(공개 자료)를 묶은 world-atlas(ISC) | `python3 -m tools.art.dotmap <countries-110m.json>` |
| 아이콘(`site/js/ui/icons.js`) | Lucide(ISC, 일부는 Feather에서 온 것으로 MIT) | `python3 -m tools.art.icons <lucide-static/icons>` |
| 글꼴 | Pretendard(SIL OFL). jsDelivr에서 불러 쓰고 저장소에 두지 않는다 | `site/js/theme.js` |
| 공유 미리보기 그림(`site/assets/og.jpg`) | 사이트의 색과 점 지도로 만든 것 | `tools/art/social.html`을 1200x630 창으로 열어 화면 그림을 찍는다 |
| 라이선스 고지(`site/assets/third-party.txt`) | 위 꾸러미의 LICENSE 파일 | `python3 -m tools.art.notices <node_modules>` |

world-atlas, lucide-static, pretendard는 npm에서 받습니다. 그림을 고칠 때만 필요하고, 평소의 자동 실행은 `tools/art`를 쓰지 않습니다.

## 게시하기 전에 거치는 것

1. 작성 실행의 자체 검사: 용어, 표기, 수치와 날짜.
2. 작성과 분리된 검증 실행이 원문을 다시 읽고 대조한다. 확인하지 못한 것은 통과시키지 않는다.
3. 게시 프로그램(`tools/publish/add_items`)이 제목, 요약, 실무 영향에 나온 수치와 날짜가 저장소의 원문 글에 있는지 한 번 더 본다. 원문 발췌는 원문에 그대로 있을 때만 싣는다.
4. 게시한 뒤에도 주마다 일부를 골라 지금의 원문과 다시 대조한다.

## 자료의 재이용

- EU 기관의 공식 자료는 출처를 밝히고 재이용합니다. `originals/`의 사본과 `collected/pages/`의 화면 글이 여기에 해당합니다.
- 공공기관 자료는 짧게 요약하고, 민간 기업과 협회와 유료 매체의 자료는 제목이 알려 주는 사실과 링크만 다룹니다. 본문을 저장하지 않습니다.
- 원문의 저작권과 재이용 조건은 각 출처를 따릅니다.

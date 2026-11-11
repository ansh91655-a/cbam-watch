# cbam-watch

EU 탄소국경조정제도(CBAM)의 규제 동향을 원문과 함께 정리해 보여 주는 사이트의 저장소입니다.

- 사이트: https://ansh91655-a.github.io/cbam-watch/
- 사이트의 정리와 번역은 자동으로 수집하고 작성한 것이며, 게시 전에 사람이 검수하지 않습니다. 정확한 내용은 반드시 원문에서 확인하세요. 법률 자문이 아닙니다.

## 하루의 흐름

| 때(한국 시각) | 누가 | 하는 일 |
| --- | --- | --- |
| 평일 05:20 | 이 저장소의 자동 실행(`.github/workflows/collect.yml`) | 출처 화면을 받아 새로 보인 링크, 날짜로 시작하는 소식, 표의 행, 문장을 `collected/feed/`에 적는다. 인증서 가격표를 읽어 `data/prices.json`을 만든다. EU 집행위원회 문서를 다시 받아 판이 바뀌었는지 보고, 바뀌면 이전 판과 문단 단위로 비교한다 |
| 평일 07:05 | 예약된 작성 실행 | 목록에서 소식을 골라 국문 초안을 쓴다. EU 공식 자료는 근거가 된 원문 대목을 함께 남긴다 |
| 평일 08:20 | 예약된 검증 실행 | 초안을 원문과 다시 대조하고, 통과한 것만 `data/`에 더한다. 이어서 공식 기록에 새로 생긴 사건을 규제별 진행 상황(`data/regulations.json`)에 반영한다 |
| 바뀔 때마다 | 이 저장소의 자동 실행(`.github/workflows/pages.yml`) | 사이트를 다시 만들어 배포한다 |
| 소식이 더해질 때 | 이 저장소의 자동 실행(`.github/workflows/thumbs.yml`) | 그림이 없는 소식의 미리보기 그림을 만들어 `site/assets/thumbs/`에 싣는다. 끝나면 사이트가 다시 배포된다 |
| 평일 10:05 | 예약된 보고 실행 | 그날의 실행과 사이트 상태를 확인하고 보고 파일을 `reports/`에 올린다 |
| 보고 파일이 올라올 때, 평일 11:10 | 이 저장소의 자동 실행(`.github/workflows/notify.yml`) | 문제가 있는 보고와 주간 보고를 '운영 보고' 이슈에 댓글로 적는다(GitHub가 저장소 주인에게 메일로 알린다). 11:10까지 그날의 보고 파일이 없으면 그것도 알린다 |
| 손으로 돌릴 때 | 예약된 임시 실행 | 제목만 옮겨 실은 국내 소식의 요약을 원문을 읽고 다시 쓴다(한 번에 12건) |
| 월요일 09:10 | 예약된 주간 실행 | 주간 요약을 쓰고, 게시한 항목 일부를 지금의 원문과 다시 대조한다. 어긋나면 그 항목의 요약을 내린다. 규제별 진행 상황에서 날짜가 지난 일정과 언론 보도에 기댄 줄을 다시 확인한다 |

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `sources/registry.json` | 출처 대장. 어디를 어떤 방법으로 보는지 적혀 있다 |
| `collected/` | 수집 결과. `feed/`(그날 새로 보인 것), `state/`(이미 본 것의 열쇠), `pages/`(EU 공식 화면의 글), `status.json`(출처별 확인 결과), `archive/`(지난 소식을 한꺼번에 모은 것. 아래 '지난 소식 채우기' 참조) |
| `originals/` | EU 집행위원회 문서의 사본(`files/<문서 id>/<해시>/<원래 파일 이름>`), 뽑아 낸 본문(`text/`), 판 사이의 비교 결과(`diffs/`), 대장(`state.json`) |
| `data/` | 사이트에 게시한 데이터. 소식(`items.json`), 주제 목록(`topics.json`), 인증서 가격(`prices.json`, 프로그램이 가격표에서 만든다), 일정(`events.json`), 주간 요약(`digests.json`), 용어집(`terms.json`), 하나로 묶은 소식의 기록(`merged.json`), 규제별 진행 상황(`regulations.json`), 품목 코드 조회의 목록(`cn.json`), 법령에서 옮겨 온 참고 자료(`factor.json`, `duties.json`, `calc.json`, `calc-goods.json`) |
| `reports/` | 보고 실행이 올리는 그날과 그 주의 보고 파일. 알림의 근거다 |
| `language/` | 국문 표기 기준(용어집) |
| `site/` | 공개 사이트의 화면 파일. 화면마다 모듈 하나(`js/views/`), 그림과 달력 같은 부품(`js/ui/`), 디자인 값(`css/tokens.css`)과 색 변형(`css/themes.css`), 파비콘과 공유 미리보기 그림과 라이선스 고지(`assets/`). 아래 '사이트의 디자인' 참조 |
| `console/` | 운영 화면의 파일 |
| `tools/` | 정해진 일을 하는 프로그램. 아래 표 참조 |
| `tests/` | 도구의 자동 시험. 도구나 시험, 시험이 읽는 화면의 셈과 참고 자료가 바뀌면 돈다(`.github/workflows/tests.yml`) |

### tools

| 묶음 | 하는 일 |
| --- | --- |
| `tools/common` | 웹에서 받기, HTML에서 글 뽑기, JSON 읽고 쓰기, 사이트 주소와 배포하는 곳 읽기(`siteinfo`: 주소는 `site/site.config.json`의 `url`, 사이트만 싣는 저장소를 따로 둘 때의 이름은 `deploy.json`의 `siteRepo`) |
| `tools/collect` | 출처 화면에서 새 항목 찾기(`extract`), JSON 목록 보기(`jsonwatch`), 그날 목록 만들기(`feed`), 실행(`run`) |
| `tools/originals` | 문서 링크 찾기(`discover`), 받을 차례 정하기(`queue`), 판 남기기와 비교(`versions`, `diff`), 본문 뽑기(`textify`), 실행(`run`) |
| `tools/check` | 국문 글 검사: 용어(`term_check`, `term_lookup`), 표기(`style_check`), 수치와 날짜 대조(`fact_check`), 원문 발췌 확인(`excerpt_check`) |
| `tools/prices` | 인증서 가격표 읽기: 적용 기간 읽기(`periods`), 표의 행 읽기(`parse`), 가격 자료 만들기(`run`) |
| `tools/publish` | 게시 데이터에 더하기(`add_items`, `add_digest`), 요약 내리기(`withdraw`), 같은 일을 두 번 실은 소식을 하나로 묶기(`merge`: 묶인 소식은 `data/merged.json`에 남고, 옛 주소는 남긴 소식으로 넘어간다), 주제 목록(`topics`), 사이트와 운영 화면의 폴더 만들기(`build_site`, `build_console`). 사이트 폴더를 만들 때 규제 자료의 공개용 사본(`regulations`), 소식의 미리보기 그림 주소(`thumbs`), 구독 피드 `feed.xml`과 `rules.xml`(`feed`. 새 소식 받아 보기를 열어 둔 동안에만), 화면에서 바로 보는 문서 사본 `files/`(`derive`)도 함께 만든다. 규제 자료 고치기(`rule_edit`), 제목만 옮겨 실은 소식의 요약을 원문을 읽고 다시 쓴 것으로 바꾸기(`revise`)도 여기에 있다 |
| `tools/notify` | 보고 파일에서 알릴 것을 골라 '운영 보고' 이슈에 적기(`reports`, `messages`, `github`, `run`) |
| `tools/run` | 예약 실행이 쓰는 보조 도구: 후보 고르기, 검증 대기 고르기, 원문 발췌 자르기, 상태 점검(`health`, 규제 자료는 `rules_health`, 품목 코드 목록과 기관별 입장 비교표는 `cn_health`), 하루와 한 주의 요약, 보고 파일 만들기(`write_report`) |
| `tools/archive` | 공식 기록을 모으는 프로그램. 지난 소식을 한꺼번에 채울 때 손으로 돌리고, 규제 진행 상황에 쓰는 기록은 평일마다 자동으로 돈다: 출처별 모으기(`ecnews`, `newsletter`, `eurlex`, `cellar`, `docs`, `oeil`, `hys`, `presscorner`, `council`, `govuk`, `ukleg`, `fedreg`, `boards`)와 실행(`crawl`), 새 자료를 그날의 후보로 넘기기(`tofeed`), 화면의 짜임 살펴보기(`dump`), 싣기 전 검사(`gate`), 싣기(`publish`) |
| `tools/cn` | 품목 코드 조회의 목록을 법령 원문에서 만드는 프로그램: 부속서의 품목 표 읽기(`annex`), `data/cn.json` 만들기(`build`), 통합본의 판 다루기(`versions`), 새 통합본이 나오면 본문을 받아 목록을 다시 만들기(`refresh`, 평일 수집이 돌린다. 부속서를 제대로 읽었는지의 확인에 걸리면 아무것도 바꾸지 않고 사유를 `collected/cn/refresh.json`에 남긴다). 원문은 `collected/archive/pages/eu-fulltext/`에 있다. 코드를 견주는 셈은 사이트의 `site/js/cn/match.js`, 개정안의 단계에 따라 안내의 말을 바꾸는 기준은 `site/js/cn/stage.js`에 있다 |
| `tools/thumbs` | 소식 카드의 미리보기 그림을 만드는 프로그램: 만들 것 고르기(`plan`), 원문 화면의 제목 부분 찍기(`shots.mjs`), 법령 PDF의 첫 장 받기(`pdfcover`), 줄여서 싣기(`finish`). 재이용이 허용된 공식 출처만 다루고, 화면을 여는 브라우저는 자동으로 여는 것임을 숨기지 않는다 |
| `tools/common` | 여러 프로그램이 함께 쓰는 것: 웹에서 받기(`net`), robots.txt 지키기(`robots`), 화면의 글 뽑기(`htmltext`), JSON 읽고 쓰기(`jsonio`), 사이트 주소와 배포 저장소(`siteinfo`) |
| `tools/calc` | 인증서 비용 추정의 품목 자료를 법령의 표에서 만드는 프로그램: 받아 둔 표 읽기(`source`), 품목마다 기본값과 벤치마크를 짝지어 `data/calc-goods.json` 만들기(`build`) |
| `tools/sitecheck` | 만든 사이트를 브라우저로 열어 가로 넘침, 화면 오류, 접근성을 검사하는 프로그램(Node). 아래 '화면 점검' 참조 |
| `tools/art` | 사이트의 그림을 만드는 프로그램. 손으로 돌린다: 점 지도(`dotmap`, 나라 경계 읽기는 `world`), 아이콘(`icons`), 라이선스 고지(`notices`), 공유 미리보기 그림의 원본(`social.html`) |

자동으로 받는 것은 모두 `tools/common/net.py`를 거치고, 이 함수는 주소를 열기 전에 그 사이트의 robots.txt를 봅니다(`tools/common/robots.py`). 사이트가 자동 읽기를 막은 주소는 받지 않고, 막힌 주소는 `collected/robots.json`에 남아 그날의 상태 점검이 알립니다. 이 수집기의 이름(cbam-watch)을 적은 규칙과 함께 Claude의 수집기 이름을 적은 규칙도 따릅니다(받은 글을 Claude가 읽고 요약하기 때문입니다). 사이트가 확인 요청이나 접근 거부 화면을 내면 넘어서려 하지 않습니다. 주소 하나를 손으로 확인하려면 `python3 -m tools.common.robots <주소>`를 씁니다.

프로그램은 저장소 맨 위에서 `python3 -m tools.<묶음>.<이름>` 꼴로 돌립니다. 표준 라이브러리만 쓰고, PDF 본문을 뽑을 때만 `pdftotext`가 필요합니다. 시험은 `python3 -m unittest discover -s tests -t .`로 돌리고, 올리기 전에는 `sh tools/dev/check.sh`(자동 실행과 같은 꾸러미만 깐 깨끗한 환경에서 시험과 사이트 만들기)를 돌립니다. 자동 실행은 결과를 `sh tools/dev/push.sh`로 올립니다(올리기가 응답 없이 멈추면 끊고 세 번까지 다시 해 보고, 끝내 안 되면 그 실행이 실패로 남습니다).

## 규제별 진행 상황

사이트의 '규제' 화면은 `data/regulations.json` 하나로 그린다. 규제마다 지금의 단계, 현재 상황, 다음 단계, 연혁(사건마다 원문 주소)을 가진다.

- 연혁의 근거는 세 가지다. `stored`는 `collected/archive/`에 모아 둔 공식 기록과 맞는 사건이고 프로그램이 실제로 맞춰 본다. `web`은 자동으로 받을 수 없는 공식 화면을 읽고 확인한 사건, `press`는 언론 보도로만 아는 사건이다(화면에 '언론 보도'로 표시된다).
- 검사: `python -m tools.publish.regulations`(꼴, 높임말, 용어, 근거). 사이트를 만들 때는 꼴과 표기만 막고, 근거가 공식 기록과 달라진 것은 알리기만 한다(공식 기록은 날마다 바뀐다).
- 고치기: `python -m tools.publish.rule_edit`(연혁에 한 줄 더하기와 빼기, 단계와 설명 고치기, 새 규제 더하기). 고친 뒤 자료 전체를 검사하고, 걸리면 고치지 않는다.
- 기관별 입장 비교표: 규제에 `positions`가 있으면 화면에 '기관별 입장 비교'가 실린다(지금은 하류제품 확대 개정안과 임시 탈탄소화 기금 규정안). 칸마다 저장소에 받아 둔 원문 글에서 근거를 대고(`contains`, 그 문서에 없는 조항은 `lacks`) 프로그램이 맞춰 본다. `python -m tools.publish.rule_edit positions --id <규제> --file <표 파일>`로 넣고, 공개용 사본에는 칸의 글만 실린다.
- 분석 글: 규제에 `analysis`가 있으면 '무엇을 정하는 규제인가요' 아래에 배경, 주요 내용, 쟁점과 정세, 실무에서 볼 점이 실린다(검사와 변환은 `tools/publish/analysis.py`, 화면은 `site/js/views/rules/analysis.js`). 문단마다 근거 자료를 가리켜야 하고, 모아 둔 공식 자료만 가리키는 문단은 그 안의 날짜와 수를 자료의 글과 프로그램이 대조한다. 언론 보도에 기댄 문단은 글에서 그렇다고 밝혀야 한다. `python -m tools.publish.rule_edit analysis --id <규제> --file <분석 파일>`로 넣고 `analysis-show`로 꺼낸다. 규제의 단계나 연혁이 달라지면 화면이 '분석을 쓴 뒤에 달라졌다'고 스스로 밝히고, 사흘이 지나도록 그대로면 상태 점검이 알린다. 근거로 쓰는 글은 워크플로 '소급 수집'으로 받아 둔다. `steps`에 `eu-acts`를 적으면 시행 중인 법령의 본문을, `eu-fulltext`를 적으면 심의 중인 제안의 본문과 부속서, EU 배출권거래제 지침 통합본, 유럽의회 입법 관측소의 문서별 요약을, `uk-legislation`을 적으면 영국 CBAM 법령의 온전한 글을, `eur-lex-docs`를 적으면 CBAM 규정과 이어진 문서(계류 중인 소송의 공고 포함)를 받는다. `eu-tables`를 적으면 법령 부속서의 값 표를 칸의 자리를 살려 받는다(인증서 비용 추정의 자료). 규제를 고칠 때 다른 규제의 근거가 받아 둔 글과 달라진 것은 알리기만 하고 막지 않으며(`rule_edit.blocking`), 그 어긋남은 상태 점검이 따로 알린다.
- 달라진 것 찾기: `python -m tools.run.rules_watch`가 모아 둔 공식 기록이 지난번에 본 뒤로 달라졌는지 알려 준다. 본 것은 `data/rules-seen.json`에 적는다.
- 상태 점검: `tools/run/rules_health.py`가 근거 어긋남, 지난 일정, 반영되지 않은 변화, 기록 갱신 누락을 일일 보고의 문제로 올린다.
- 공식 기록을 읽지 못한 날: 사이트가 점검 중이거나 답이 끊겨도 모아 둔 목록은 줄어들지 않는다. 읽지 못한 것이 있는 실행은 앞의 목록에서 빠진 기록을 그대로 남기고(`tools/archive/store.py`의 `save_index`), EU 법령 데이터베이스의 연관 문서는 빠진 문서와 관계를 되살린다(`tools/archive/cellar.py`의 `restore`). 무엇을 읽지 못했는지는 `collected/archive/report/`에 남는다.

## 법령에서 옮겨 온 참고 자료

소식이나 규제의 연혁과 달리, 법령에 적힌 값을 그대로 옮겨 화면의 그림과 계산에 쓰는 자료가 있다. 모두 같은 틀을 따른다: 원본은 `data/`에 있고 항목마다 그 값이 적힌 법령 글(`collected/archive/pages/` 아래)을 가리키며, 검사 프로그램(`tools/publish/`)이 값과 대목을 그 글과 대조한다. 꼴이 깨지면 사이트 만들기가 멈추고, 받아 둔 글과 달라진 것('근거 어긋남')은 알리기만 한다. 공개용 사본에서는 저장소 안의 경로와 대조용 대목을 뺀다. 어긋남은 상태 점검(`tools/run/reference_health.py`)이 일일 보고의 문제로 올린다.

- CBAM 계수(`data/factor.json`, 검사 `python -m tools.publish.factor`): 현행 지침과 개정안의 해마다의 값. 규제 자료에 `figure: cbam-factor`가 적힌 규제의 화면에 그림으로 실리고(`site/js/ui/factorchart.js`), 인증서 비용 추정이 쓴다.
- 실무 달력(`data/duties.json`, 검사 `python -m tools.publish.duties`): 법령에 날짜가 적힌 EU CBAM과 영국 CBAM의 의무. 일정 화면의 '의무 일정'에 실리고 일정에도 합쳐진다(같은 일을 가리키는 게시 데이터의 일정은 의무 쪽을 남긴다).
- 인증서 비용 추정(`data/calc.json`과 `data/calc-goods.json`, 검사 `python -m tools.publish.calc`): 사이트의 '가격 > 비용 추정' 화면(`#calc`)이 쓴다.
  - `calc-goods.json`은 손으로 고치지 않는다. 받아 둔 법령의 표(`collected/archive/pages/eu-tables/`)에서 `python -m tools.calc.build`가 만든다: 무상할당 조정 이행규정 (EU) 2025/2620 부속서 5의 CBAM 벤치마크(품목 570개)와, 기본값 이행규정 (EU) 2025/2621 부속서 I(정정 규정 (EU) 2026/1740이 갈아 끼운 표)의 대한민국 표, 대한민국의 값이 없는 품목에 쓰는 '그 밖의 나라와 지역' 표. 법령이 정하지 않은 경우를 만나면 어림하지 않고 멈춘다.
  - `calc.json`은 손으로 적는 규칙이다: 마크업, 부문 간 보정계수, 벤치마크의 연도 구간, 생산경로의 이름, 계산식, 화면에 싣는 설명 글. 수식은 받아 둔 글에 그림으로만 있어 유럽연합 관보의 PDF에서 확인했고(확인한 날을 적어 둔다), 식의 항이 무엇인지는 받아 둔 글과 대조한다.
  - 셈은 `site/js/calc/compute.js`가 한다(시험은 `tests/test_calc.py`가 node로 돌린다). 정해지지 않아 가정한 값(2031년 이후의 벤치마크와 부문 간 보정계수)과 참고용인 값(2027년 수입분부터 갱신될 벤치마크)은 화면이 그렇다고 밝힌다.
  - 근거 법령을 고치거나 바로잡는 새 문서가 법령 데이터베이스 목록에 보이면 상태 점검이 알린다(`calc.json`의 `watch`). 그때는 `tools/archive/tables.py`의 대상을 새 법령으로 바꿔 표를 다시 받고(워크플로 '소급 수집', `steps`에 `eu-tables`), `python -m tools.calc.build`로 자료를 다시 만들어 달라진 것을 확인한 뒤, 반영한 문서를 `watch.known`에 적는다.
- 규제 화면에서 추정 화면으로 이어 주려면 규제 자료에 `tool: calc`를 적는다(`python -m tools.publish.rule_edit set --id <규제> --tool calc`).

## 화면 점검

`tools/sitecheck`는 만든 사이트를 브라우저(이미 깔려 있는 크롬)로 열어 검사한다. 화면 파일이나 게시 데이터가 바뀌면 워크플로 '화면 점검'(`.github/workflows/sitecheck.yml`)이 돌린다. 사이트 배포는 이 검사를 기다리지 않고, 문제가 나오면 '운영 보고' 이슈에 어느 화면이 왜 걸렸는지 적힌다(`python -m tools.notify.run --event sitecheck`).

- `layout`: 모든 화면을 다섯 너비(360~1440)로, 규제 화면을 규제마다 세 너비로 열어 가로 넘침, 화면 밖으로 나간 글, 그려지지 않은 화면, 본문에 찍힌 깨진 값(undefined, NaN), 화면 오류와 받지 못한 파일을 본다.
- `axe`: 주요 화면에 접근성 자동 검사(axe-core)를 색 변형 셋, 너비 둘로 돌린다.
- `calc`: 인증서 비용 추정 화면을 실제로 다뤄 본다(품목 찾기와 고르기, 신고 방법과 연도 바꾸기, 초점이 제자리로 가는지, 결과에 깨진 값이 없는지).
- 화면의 목록은 만든 사이트의 데이터에서 뽑으므로(`plan.mjs`) 규제나 주제가 늘어도 따라간다.
- 손으로 돌리기: `python3 -m tools.publish.build_site /tmp/_site && npm ci --prefix tools/sitecheck && node tools/sitecheck/run.mjs /tmp/_site` (일부만 돌리려면 `--only layout,axe,calc`, 결과 파일은 `--report <파일>`). 크롬이 다른 곳에 있으면 `CHROME_PATH`에 적는다.

## 지난 소식 채우기

사이트를 연 날보다 앞선 소식(2025년 1월부터)은 평소의 자동 실행과 따로 한 번에 채웠습니다. 같은 일을 다시 할 때의 차례입니다.

1. 모으기. 워크플로 '소급 수집'(`.github/workflows/archive.yml`)을 손으로 돌립니다. `mode`를 `crawl`로 두고 `steps`에 출처 이름을 띄어 적으면 그 출처만 돕니다(비우면 모두). 결과는 `collected/archive/`에 쌓입니다. 출처마다 목록(`<출처>.json`), 재이용이 허용된 자료의 원문 글(`pages/`), 실행 결과(`report/`)가 있습니다.
   - `ec-news`: EU 집행위원회 조세·관세총국 소식. 사이트 지도에서 소식 주소를 얻어 본문에 CBAM이 나오는 것만 남깁니다.
   - `ec-newsletter`: EU 집행위원회가 보내는 CBAM Newsletter의 보관함. `eur-lex`: CBAM 법령의 제목, 채택일, 관보 게재일, 시행과 적용에 관한 조문(EU 출판국의 자료 창구에서 받습니다).
   - `ep-oeil`: 유럽의회 입법 관측소의 절차 기록. `ec-hys`: 의견수렴 목록. `uk-govuk`: 영국 정부 CBAM 문서의 변경 기록.
   - `kr-boards`: 국내 기관 게시판의 제목, 날짜, 주소. 본문은 받아 두지 않습니다(산업통상부 보도자료만 부제와 첫 문단을 짧게 남깁니다).
2. 쓰기. 모아 둔 글을 읽고 국문 초안을 만듭니다. 초안 파일은 저장소에 올리지 않습니다.
3. 싣기. `python3 -m tools.archive.publish --drafts <초안 파일> [--dry-run]`. 형식, 문체, 용어, 원문 대조(수치와 날짜, 게시일), 링크, 원문 발췌를 검사해 통과한 것만 `data/items.json`에 더하고 `backfill` 표시를 붙입니다. 이 표시가 있는 소식은 원문이 그 주에 나온 것이 아니면 주간 요약의 대상에서 빠지고(`tools/run/week_items.py`), 주간 작업이 주마다 10건씩 원문과 다시 대조합니다.

제목만 옮겨 실은 소식. 국내 기관 게시판의 지난 글은 본문을 받아 두지 않아 제목만으로 한 문장을 썼습니다. 이런 소식에는 `brief` 표시가 있고 사이트에서 요약 없이 한 줄로 보입니다. 원문을 읽고 요약을 쓴 뒤 `python3 -m tools.publish.revise`로 바꾸면(문체, 용어, 길이, 수치와 날짜를 검사합니다) 표시가 떨어지고 카드로 보입니다. 쓰는 법은 그 파일 머리에 있습니다.

## 사이트의 디자인

- 방향: 짙은 남색의 큰 머리(점 지도, 지금 알아 둘 수치 세 칸)와 밝은 본문입니다. 본문의 칸은 모서리가 둥근 카드에 옅은 그림자를 두고, 단추는 알약 모양입니다. 값은 모두 `site/css/tokens.css`에 있습니다.
- 색은 EU 깃발의 파랑(#003399)과 노랑(#FFCC00)을 빌렸습니다. 깃발(별 열두 개)과 EU 기관의 로고는 쓰지 않습니다. 개인이 운영하는 비공식 사이트입니다.
- 글꼴은 Pretendard 하나입니다.
- 이름표는 글자입니다: 'CBAM' 뒤에 노란 세로선(국경선)과 '규제동향'. 네모난 표지(`site/assets/favicon.svg`, CB와 AM 사이에 노란 선)는 탭 아이콘에만 씁니다.
- 첫 화면(`site/js/views/home.js`가 `home/` 폴더의 칸들을 차례로 놓습니다): 큰 머리(`hero`, `facts`. 수치 칸 위에 새 소식 한 줄), 가장 최근의 요약(`digest`. 기간에 따라 '이번 주 요약', '지난주 요약', '주간 요약'으로 부르고, 여러 주를 묶은 요약은 '최근 동향 요약'이라고 부릅니다), 가장 중요한 소식(`feature`), 다가오는 일정·인증서 가격 추세·주제별 소식·규제 진행 상황(`panels`), 품목 코드 조회(`lookup`), 최근 소식, 품목별 가이던스(`sectors`).
- 점 지도(`site/js/ui/heromap.js`)는 두 장을 겹친 것입니다. 아래 장은 유라시아를 점으로 찍은 지도(EU 회원국은 밝게, 한국은 노랗게)이고, 위 장은 한국에서 EU의 항구 다섯 곳으로 가는 선입니다. 선은 화면이 열릴 때 한국에서 EU 쪽으로 한 번 그려지고, 그 뒤로는 작은 빛이 같은 쪽으로 천천히 지나갑니다(움직임을 줄이도록 설정한 기기에서는 멈춘 그림). 선은 실제 뱃길이 아니라 방향을 나타낸 그림입니다. 지도 위와 아래에는 이름이나 설명글을 두지 않습니다(무엇을 그린 것인지는 화면 낭독기용 글에만 적혀 있습니다).
- 움직임은 `site/css/motion.css`와 `site/js/ui/motion.js`에 모아 두었습니다. 본문의 칸은 화면에 들어올 때 한 번 차례로 올라오고, 가격 그림의 선과 규제 단계의 선은 그때 그려지며, 큰 수치는 올라갑니다(`ui/countup.js`). 지금 진행 중인 것(갱신 시각, 진행 중인 규제, 지금 가격, 일정선의 오늘)은 점이 천천히 번집니다. 첫 화면의 큰 머리에는 가장 최근 소식의 제목이 한 줄씩 돌아가고(`ui/ticker.js`), 품목 코드 조회 칸의 예시가 번갈아 바뀌며(`ui/typehint.js`), 주 메뉴의 밑줄은 메뉴 사이를 미끄러져 옮겨 갑니다(`ui/navink.js`). 긴 글 화면(규제 하나)에서는 머리글 아래에 읽은 만큼 선이 차고, 한참 내려오면 맨 위로 가는 단추가 보입니다(`ui/scrollcue.js`). 움직임을 줄이도록 설정한 기기에서는 모두 멈추고 아무것도 숨기지 않습니다. 새로 만든 칸이 화면에 들어올 때 나타나게 하려면 `ui/motion.js`의 목록에 그 칸의 이름을 더합니다.
- 소식의 제목이나 미리보기 그림을 누르면 원문으로 가기 전에 국문 요약 화면(`#item-<소식 번호>`, `site/js/views/item.js`)을 먼저 보여 줍니다. 제목이 곧 내용인 한 줄 소식만 원문으로 바로 갑니다(`site/js/ui/itemlink.js`). 뒤로 가면 보던 자리로 돌아옵니다(`site/js/router.js`).
- 닫아 둔 기능: 새 소식 받아 보기(구독 피드와 안내 창, `site/js/ui/subscribe.js`, `tools/publish/feed.py`)와 의견 보내기(`site/js/ui/feedback.js`)는 만들어 두었지만 지금은 닫혀 있습니다. `site/site.config.json`의 `features`에서 `subscribe`, `feedback`을 `true`로 바꾸면 다시 열립니다. 닫혀 있는 동안에는 화면에 단추가 없고 구독 피드 파일(`feed.xml`, `rules.xml`)도 만들지 않습니다.
- 색 변형은 세 가지입니다: 네이비(기본), 화이트, 미드나잇. 주소에 `?theme=white`처럼 붙이면 바꿔 볼 수 있고, 기본값은 `site/js/theme.js`의 `DEFAULT`입니다. 변형마다 달라지는 값은 `site/css/themes.css`에만 있습니다.
- CSS는 쓰임새로 나눴습니다: 값(`tokens`), 바탕(`base`), 틀과 큰 머리와 지도(`layout`), 여러 화면이 함께 쓰는 부품(`components`), 첫 화면(`home`), 소식 요약 화면(`item`), 뜨는 창과 여백의 탭(`overlay`), 화면마다 따로 쓰는 것(`views`), 가격 그림(`chart`), 일정(`calendar`), 규제(`rules`), 품목 코드 조회(`cn`), 움직임(`motion`), 색 변형(`themes`).
- 그림은 사진 없이 직접 만든 것과 자유롭게 쓸 수 있는 것만 씁니다.

| 그림 | 어디서 왔나 | 만드는 법 |
| --- | --- | --- |
| 점 지도(`site/js/ui/heromap.js`) | 직접 그린 것. 나라 경계는 Natural Earth(공개 자료)를 묶은 world-atlas(ISC) | `python3 -m tools.art.dotmap <countries-110m.json>`. 항구를 바꿔 선이 서로 엇갈리면 프로그램이 멈춘다. 나라 경계 읽기는 `tools/art/world.py` |
| 아이콘(`site/js/ui/icons.js`) | Lucide(ISC, 일부는 Feather에서 온 것으로 MIT) | `python3 -m tools.art.icons <lucide-static/icons>` |
| 글꼴(`site/assets/fonts/pretendard/`) | Pretendard(SIL OFL) 1.3.9의 가변 글꼴 조각 파일. 사이트에 직접 싣는다 | npm의 `pretendard` 꾸러미에서 `dist/web/variable/`의 CSS와 `woff2-dynamic-subset/`을 복사한다 |
| 공유 미리보기 그림(`site/assets/og.jpg`) | 사이트의 색, 글꼴, 이름표, 점 지도로 만든 것 | `tools/art/social.html`을 1200x630 창으로 열어 화면 그림을 찍는다 |
| 표지(`site/assets/favicon.svg`) | 직접 그린 것: 파란 네모에 CB와 AM, 그 사이에 노란 선 | 파일의 SVG를 고친다. 머리글의 이름표는 글자라서 `site/index.html`과 `site/css/layout.css`의 `.brand`를 고친다 |
| 소식 카드의 미리보기 그림(`site/assets/thumbs/`) | 재이용이 허용된 공식 출처(EU 기관, 영국 정부)의 원문 화면에서 제목부터의 글 부분, 법령 PDF 첫 장의 머리 띠 아래. 화면의 사진과 삽화, 기관 로고는 넣지 않는다. 그 밖의 소식은 사이트가 주제 색과 아이콘으로 그린다(`site/js/ui/thumb.js`) | 워크플로 '썸네일 만들기'가 만든다. 실패는 `collected/thumbs/state.json`에 남고 세 번까지 다시 시도한다 |
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
- 소식 카드의 미리보기 그림은 EU 기관과 영국 정부(Open Government Licence v3.0)의 자료만 줄여 싣습니다. 재이용 조건을 확인하지 못한 출처의 화면은 그림으로 만들지 않습니다.
- 원문의 저작권과 재이용 조건은 각 출처를 따릅니다.

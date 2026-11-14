# PDF.js

원문과 번역 PDF를 나란히 보는 화면(`site/js/views/pdf.js`)이 쪽을 그리는 데 씁니다. Mozilla의 PDF.js를 고치지 않고 그대로 두었습니다.

- 받은 곳: npm `pdfjs-dist` 6.5.438 (legacy 빌드: 조금 오래된 브라우저에서도 돕니다)
- 허락글: `LICENSE`(Apache License 2.0). `wasm/`의 그림 풀이 도구와 `standard_fonts/`의 글꼴은 그 폴더의 허락글을 따릅니다.
- `pdf.min.js`(화면 쪽. 받은 파일의 이름은 pdf.min.mjs이며, 어느 서버에서나 스크립트로 읽히도록 확장자만 바꾸었습니다), `pdf.worker.min.js`(풀이 쪽), `wasm/`(JPEG 2000, JBIG2, 빛깔 풀이), `standard_fonts/`(PDF에 글꼴이 들어 있지 않을 때 쓰는 글꼴)

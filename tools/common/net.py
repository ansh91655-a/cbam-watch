"""웹에서 파일을 받아 오는 공통 함수. 표준 라이브러리만 쓴다."""
import hashlib
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 cbam-watch/0.1 (+https://github.com/ansh91655-a/cbam-watch)"
)


def fetch(url, timeout=60, retries=2, pause=5):
    """주소를 열어 (상태 코드, 머리글, 본문 바이트, 오류 글)을 돌려준다. 예외를 던지지 않는다."""
    last_error = ""
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
                "Accept-Language": "en,ko;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, dict(response.headers.items()), response.read(), ""
        except urllib.error.HTTPError as error:
            body = b""
            try:
                body = error.read()
            except Exception:
                pass
            return error.code, dict(error.headers.items()) if error.headers else {}, body, str(error)
        except Exception as error:  # 접속 실패, 시간 초과 등
            last_error = f"{type(error).__name__}: {error}"
            if attempt < retries:
                time.sleep(pause)
    return 0, {}, b"", last_error


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()

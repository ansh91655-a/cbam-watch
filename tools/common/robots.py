"""robots.txt를 지킨다. 사이트가 자동 읽기를 막아 둔 주소는 받지 않는다.

웹에서 파일을 받는 공통 함수(tools.common.net.fetch)가 주소를 열기 전에 여기에 묻는다(check).
규칙은 RFC 9309를 따른다.
- 우리 이름을 적은 묶음이 있으면 그 묶음을, 없으면 모두(*)에게 적용되는 묶음을 따른다.
  우리 이름은 이 수집기의 이름(cbam-watch)과 Claude의 수집기 이름들이다. 이 수집기가 받은 글은 Claude가 읽고 요약하므로,
  사이트가 Claude에게 읽지 말라고 한 주소는 이 수집기도 받지 않는다.
- 주소에 맞는 줄이 여럿이면 가장 길게 맞는 줄을 따르고, 길이가 같으면 허용이 이긴다. 맞는 줄이 없으면 허용이다.
- robots.txt가 없으면(4xx) 모두 허용이다. 서버 오류나 접속 실패로 읽지 못하면 전에 받아 둔 것을 쓰고,
  받아 둔 것도 없으면 그 사이트는 받지 않는다.
받은 robots.txt와 막힌 주소는 collected/robots.json에 적어 둔다. 같은 실행 안에서는 다시 받지 않고,
막힌 주소의 기록은 실행 확인(tools.run.health)이 읽어 알린다.

쓰는 법(손으로 확인할 때): python -m tools.common.robots <주소> [<주소> ...]
"""
import datetime
import json
import re
import sys
import urllib.parse

from tools.common.jsonio import now_kst, read_json, stamp, write_json

# robots.txt에서 우리를 가리키는 이름들. 첫 이름은 tools.common.net의 User-Agent에 들어 있는 이 수집기의 이름이고,
# 나머지는 받은 글을 읽는 Claude의 수집기 이름이다.
AGENTS = ("cbam-watch", "claudebot", "claude-user", "claude-searchbot", "claude-web", "anthropic-ai")
CACHE = "collected/robots.json"
FRESH_HOURS = 12      # 받아 둔 것이 이보다 새것이면 다시 받지 않는다(한 번의 자동 실행 안에서 여러 프로그램이 함께 쓴다)
MAX_BYTES = 500_000   # robots.txt에서 읽는 양의 한도(RFC 9309는 적어도 500KiB를 읽게 한다)
BLOCKED_KEPT = 200    # 막힌 주소의 기록을 이만큼만 남긴다
ALLOW_ALL = "allow-all"
BLOCK_ALL = "block-all"


def parse(text):
    """robots.txt의 글을 묶음의 목록으로 읽는다. 묶음은 {"agents": [이름], "rules": [(허용인가, 경로 무늬)]}이다."""
    groups, current, in_rules = [], None, False
    for raw in str(text).splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or in_rules:  # 규칙 뒤에 다시 이름이 나오면 새 묶음이다
                current = {"agents": [], "rules": []}
                groups.append(current)
                in_rules = False
            current["agents"].append(value.lower())
        elif key in ("allow", "disallow") and current is not None:
            in_rules = True
            if value:  # 빈 Disallow는 아무것도 막지 않는다
                current["rules"].append((key == "allow", value))
    return groups


def rules_for(groups, agents=AGENTS):
    """우리에게 적용되는 규칙들. 우리 이름을 적은 묶음이 하나라도 있으면 그 묶음들만, 없으면 '*' 묶음들을 합친다."""
    names = {name.lower() for name in agents}
    mine = [group for group in groups if names & set(group["agents"])]
    chosen = mine or [group for group in groups if "*" in group["agents"]]
    return [rule for group in chosen for rule in group["rules"]]


def _matches(pattern, target):
    """경로 무늬가 주소에 맞는가. '*'는 어떤 글자든 몇 개든, 끝의 '$'는 주소의 끝을 뜻한다."""
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = ".*".join(re.escape(part) for part in body.split("*"))
    return re.match(regex + ("$" if anchored else ""), target) is not None


def permits(rules, target):
    """규칙들이 그 주소(경로와 물음표 뒤)를 허용하는가. 가장 길게 맞는 줄을 따르고, 길이가 같으면 허용이 이긴다."""
    best_length, best_allow = -1, True
    for allow, pattern in rules:
        if not _matches(pattern, target):
            continue
        if len(pattern) > best_length or (len(pattern) == best_length and allow):
            best_length, best_allow = len(pattern), allow
    return best_allow


def _target(parts):
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path


def _load(address):
    """robots.txt를 받는다. (상태 코드, 글)을 돌려준다. 자기 자신에게 묻지 않도록 점검 없이 받는다."""
    from tools.common.net import fetch  # 서로를 부르는 모듈이라 여기에서 들여온다
    status, _, body, _ = fetch(address, timeout=20, retries=1, pause=2, robots=False)
    return status, body[:MAX_BYTES].decode("utf-8", "replace")


class Gate:
    """사이트마다 robots.txt를 한 번 받아 두고 주소를 열어도 되는지 답한다."""

    def __init__(self, load=None, cache=CACHE, now=None):
        self.load = load or _load
        self.cache = cache
        self.now = now or now_kst
        self.known = {}  # 사이트 → 규칙의 목록, ALLOW_ALL, BLOCK_ALL

    def _book(self):
        book = read_json(self.cache, {}) if self.cache else {}
        book = book if isinstance(book, dict) else {}
        book.setdefault("hosts", {})
        book.setdefault("blocked", {})
        return book

    def _fresh(self, row):
        try:
            age = self.now() - datetime.datetime.fromisoformat(row["fetchedAt"])
        except Exception:
            return False
        return datetime.timedelta(0) <= age < datetime.timedelta(hours=FRESH_HOURS)

    @staticmethod
    def _policy(row):
        if 400 <= int(row.get("status", 0)) < 500:
            return ALLOW_ALL
        return rules_for(parse(row.get("text", "")))

    def _learn(self, origin):
        book = self._book()
        kept = book["hosts"].get(origin)
        if kept and self._fresh(kept):
            return self._policy(kept), ""
        status, text = self.load(origin + "/robots.txt")
        readable = 200 <= status < 300 or (400 <= status < 500 and status != 429)
        if readable:
            row = {"status": status, "fetchedAt": stamp(self.now()), "text": text if status < 300 else ""}
            if self.cache:
                book["hosts"][origin] = row
                write_json(self.cache, book)
            return self._policy(row), ""
        if kept:  # 오늘은 읽지 못했다. 전에 받아 둔 것을 쓴다.
            return self._policy(kept), ""
        return BLOCK_ALL, f"robots.txt를 읽지 못해 받지 않음(응답 {status})"

    def _remember_block(self, url, why):
        if not self.cache:
            return
        book = self._book()
        book["blocked"][url] = {"why": why, "seenAt": stamp(self.now())}
        if len(book["blocked"]) > BLOCKED_KEPT:  # 오래된 것부터 지운다
            latest = sorted(book["blocked"].items(), key=lambda pair: pair[1].get("seenAt", ""))[-BLOCKED_KEPT:]
            book["blocked"] = dict(latest)
        write_json(self.cache, book)

    def check(self, url):
        """(열어도 되는가, 안 되는 까닭)을 돌려준다."""
        parts = urllib.parse.urlsplit(str(url))
        if parts.scheme not in ("http", "https") or not parts.netloc:
            return True, ""
        if parts.path == "/robots.txt":
            return True, ""
        origin = f"{parts.scheme}://{parts.netloc.lower()}"
        if origin not in self.known:
            self.known[origin] = self._learn(origin)
        policy, why = self.known[origin]
        if policy == ALLOW_ALL:
            return True, ""
        if policy != BLOCK_ALL and permits(policy, _target(parts)):
            return True, ""
        why = why or "robots.txt가 자동 읽기를 막음"
        self._remember_block(str(url), why)
        return False, why


_gate = None


def check(url):
    """주소를 열어도 되는지 묻는다. 한 프로그램이 도는 동안 사이트마다 robots.txt를 한 번만 받는다."""
    global _gate
    if _gate is None:
        _gate = Gate()
    return _gate.check(url)


def blocked_today(day, cache=CACHE):
    """그 날(YYYY-MM-DD)에 막힌 주소의 목록: [(주소, 까닭)]."""
    book = read_json(cache, {}) or {}
    return sorted((url, row.get("why", "")) for url, row in (book.get("blocked") or {}).items() if str(row.get("seenAt", "")).startswith(day))


def main(argv):
    if not argv:
        print("쓰는 법: python -m tools.common.robots <주소> [<주소> ...]")
        return 1
    gate = Gate(cache="")  # 손으로 확인할 때는 기록을 남기지 않는다
    for url in argv:
        ok, why = gate.check(url)
        print(json.dumps({"url": url, "allowed": ok, "why": why}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

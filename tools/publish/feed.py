"""구독 피드(Atom)를 만든다. 새 소식은 feed.xml, 규제 연혁의 변화는 rules.xml이다.

RSS 리더가 읽는 파일이다. 본문은 이 사이트의 국문 요약(규제는 연혁의 한 줄)이다.
항목을 누르면 이 사이트의 국문 요약 화면(#item-…, 규제는 #rules-…)이 먼저 열리고, 원문 주소는 related 링크로 함께 싣는다.
국문 요약이 따로 없는 한 줄 소식은 원문으로 바로 간다.
내린 소식은 넣지 않는다. 언론 보도로만 아는 규제 연혁에는 '[언론 보도]'를 붙인다.
"""
import hashlib
from xml.sax.saxutils import escape

LIMIT = 40


def _stamp(day):
    """날짜(YYYY-MM-DD)를 피드가 쓰는 시각 꼴로 바꾼다. 날짜가 아니면 빈 글."""
    day = str(day or "")[:10]
    return f"{day}T00:00:00+09:00" if len(day) == 10 and day[4] == "-" and day[7] == "-" else ""


def _day(item):
    """소식의 날짜. 화면(site/js/data.js의 dateOf)과 같은 기준이다: 원문의 게시일, 없으면 이 사이트에 실린 날.

    한꺼번에 채운 지난 소식(backfill)은 실린 날이 소식의 날짜가 아니므로, 게시일이 없으면 날짜가 없는 것으로 본다.
    """
    return str(item.get("published") or ("" if item.get("backfill") else item.get("listed")) or "")[:10]


def _entry(key, title, link, updated, summary, label, related=""):
    """항목 하나. link는 눌렀을 때 열리는 주소, related는 함께 싣는 원문 주소(link와 같으면 싣지 않는다)."""
    quote = {chr(34): "&quot;"}
    lines = ["  <entry>", f"    <id>{escape(key)}</id>", f"    <title>{escape(title)}</title>", f"    <updated>{updated}</updated>"]
    if link:
        lines.append(f'    <link rel="alternate" href="{escape(link, quote)}"/>')
    if related and related != link:
        lines.append(f'    <link rel="related" href="{escape(related, quote)}"/>')
    if label:
        lines.append(f'    <category term="{escape(label, {chr(34): "&quot;"})}"/>')
    lines += [f"    <summary>{escape(summary)}</summary>", "  </entry>"]
    return lines


def _feed(site_url, name, title, subtitle, built, entries):
    quote = {chr(34): "&quot;"}
    lines = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="ko">',
             f"  <id>{escape(site_url + name)}</id>", f"  <title>{escape(title)}</title>", f"  <subtitle>{escape(subtitle)}</subtitle>",
             f"  <updated>{built}</updated>", f'  <link rel="self" href="{escape(site_url + name, quote)}"/>',
             f'  <link rel="alternate" href="{escape(site_url, quote)}"/>', "  <author><name>CBAM 규제동향</name></author>"]
    for entry in entries:
        lines += entry
    return "\n".join(lines + ["</feed>", ""])


def news(items, topics, site_url, built):
    """새 소식 피드의 글. 날짜(_day)가 가까운 것부터 LIMIT건. 날짜가 없는 소식(날짜 없이 실은 제도 안내)은 넣지 않는다."""
    names = {topic.get("code"): topic.get("name", "") for topic in topics}
    rows = [item for item in items if not item.get("withdrawn") and _stamp(_day(item))]
    rows.sort(key=lambda item: (_day(item), str(item.get("id", ""))), reverse=True)
    entries = []
    for item in rows[:LIMIT]:
        summary = " ".join(part for part in (item.get("summary", ""), f"실무 영향: {item['impact']}" if item.get("impact") else "", f"출처: {item['sourceName']}" if item.get("sourceName") else "") if part)
        page = f"{site_url}#item-{item.get('id', '')}"
        has_page = bool(item.get("id")) and not item.get("brief")  # 화면의 ui/itemlink.js와 같은 기준
        original = item.get("link", "")
        entries.append(_entry(page, item.get("title", ""), page if has_page else original,
                              _stamp(_day(item)), summary, names.get(item.get("topic"), ""),
                              related=original if has_page else ""))
    return _feed(site_url, "feed.xml", "CBAM 규제동향: 새 소식", "EU 탄소국경조정제도(CBAM) 소식을 원문 링크와 함께 국문으로 정리합니다.", built, entries)


def rules(body, site_url, built):
    """규제 연혁 피드의 글. 날짜가 가까운 사건부터 LIMIT건."""
    events = []
    for rule in body.get("regulations", []):
        for event in rule.get("timeline", []):
            if _stamp(event.get("date")):
                events.append((event["date"], rule, event))
    events.sort(key=lambda row: (row[0], row[1].get("id", "")), reverse=True)
    entries = []
    for date, rule, event in events[:LIMIT]:
        mark = "[언론 보도] " if event.get("basis") == "press" or event.get("press") else ""
        digest = hashlib.sha1(f"{rule.get('id')}|{date}|{event.get('text', '')}".encode("utf-8")).hexdigest()[:10]
        summary = f"{mark}{event.get('text', '')} 출처: {event.get('source', '')}"
        page = f"{site_url}#rules-{rule.get('id', '')}"
        entries.append(_entry(f"{page}/{digest}", f"{rule.get('name', '')} ({date})", page, _stamp(date), summary, rule.get("stage", ""),
                              related=event.get("link", "")))
    return _feed(site_url, "rules.xml", "CBAM 규제동향: 규제 변화", "CBAM 규제별 진행 상황에 더해진 연혁입니다.", built, entries)

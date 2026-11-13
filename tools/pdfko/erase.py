"""번역으로 바꿀 자리의 원문 글자를 PDF에서 들어낸다.

글자 찍기 연산자에서 그 글자만 빼고 뺀 폭만큼의 걸음을 넣는다. 그래서 같은 줄에 남는 글자(번호, 수식, 그대로 두는 낱말)는 제자리에 있다.
쪽에 바로 놓인 내용 흐름과, 문서에서 한 번만 그려지는 양식(Form XObject) 안의 흐름을 고친다. 여러 번 그려지는 양식은 건드리지 않는다.
"""

import decimal

import pikepdf

from tools.pdfko import glyphs

SHOWS = ("Tj", "TJ", "'", '"')


def _number(value):
    return decimal.Decimal(f"{value:.3f}")


def _pieces(items, show, gone):
    """글자를 뺀 TJ 배열. 원문의 짜임이 읽은 것과 다르거나 글자 경계를 알 수 없으면 None."""
    counts, unit, marks = show["counts"], show["unit"], show["glyphs"]
    if counts is None or len(counts) != len(items):
        return None
    out, cursor, pending = [], 0, 0.0
    for item, count in zip(items, counts):
        text = isinstance(item, pikepdf.String)
        if count is None:
            if text:
                return None
            pending += float(item)
            continue
        if not text:
            return None
        raw = bytes(item)
        drop = [cursor + offset in gone for offset in range(count)]
        steps = [marks[cursor + offset]["step"] for offset in range(count)]
        cursor += count
        if all(drop):
            pending += sum(steps)
            continue
        if any(drop) and (unit is None or len(raw) != count * unit):
            return None
        begin = 0
        for offset in range(1, count + 1):
            if offset < count and drop[offset] == drop[begin]:
                continue
            if drop[begin]:
                pending += sum(steps[begin:offset])
            else:
                if pending:
                    out.append(_number(pending))
                    pending = 0.0
                out.append(item if (begin, offset) == (0, count) else pikepdf.String(raw[begin * unit:offset * unit]))
            begin = offset
    if pending:
        out.append(_number(pending))
    return out


def _rewrite(instructions, wanted):
    """글자 찍기 연산자들을 고친 목록과 (들어낸 글자 수, 고치지 못한 차례들)."""
    out, index, removed, failed = [], -1, 0, []
    for instruction in instructions:
        operator = str(instruction.operator)
        if operator not in SHOWS:
            out.append(instruction)
            continue
        index += 1
        if index not in wanted:
            out.append(instruction)
            continue
        order, show, marks = wanted[index]
        operands = list(instruction.operands)
        items = list(operands[-1]) if operator == "TJ" else [operands[-1]]
        pieces = _pieces(items, show, marks)
        if pieces is None:
            failed.append(order)
            out.append(instruction)
            continue
        if operator == '"':
            out.append(pikepdf.ContentStreamInstruction([operands[0]], pikepdf.Operator("Tw")))
            out.append(pikepdf.ContentStreamInstruction([operands[1]], pikepdf.Operator("Tc")))
        if operator in ("'", '"'):
            out.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("T*")))
        out.append(pikepdf.ContentStreamInstruction([pikepdf.Array(pieces)], pikepdf.Operator("TJ")))
        removed += len(marks)
    return out, removed, failed


def strip(pdf, page, sheet, gone):
    """쪽에서 글자를 들어낸다.

    gone은 {sheet.shows에서의 차례: {그 안의 글자 차례, …}}. 돌려주는 것은 (들어낸 글자 수, 고치지 못한 연산의 차례들).
    쪽에 바로 놓인 내용과, 문서에서 한 번만 그려지는 양식(Form XObject) 안의 내용을 고친다.
    연산자의 수가 읽은 것과 다른 흐름은 건드리지 않고 그 안의 것을 모두 고치지 못한 것으로 알린다.
    """
    streams, failed = {}, []
    for order, marks in gone.items():
        show = sheet.shows[order]
        if not marks:
            continue
        if show["stream"] == glyphs.PAGE or show["stream"] in sheet.once:
            streams.setdefault(show["stream"], {})[show["index"]] = (order, show, marks)
        else:
            failed.append(order)
    removed = 0
    for name, wanted in streams.items():
        try:
            holder = page if name == glyphs.PAGE else pdf.get_object((name, 0))
            instructions = pikepdf.parse_content_stream(holder)
        except Exception:
            instructions = None
        if instructions is None or sum(1 for instruction in instructions if str(instruction.operator) in SHOWS) != sheet.totals.get(name):
            failed += [order for order, _, _ in wanted.values()]
            continue
        out, done, bad = _rewrite(instructions, wanted)
        removed += done
        failed += bad
        body = pikepdf.unparse_content_stream(out)
        if name == glyphs.PAGE:
            page.obj.Contents = pdf.make_stream(body)
        else:
            holder.write(body)
    return removed, failed


def able(show, marks, once=()):
    """이 찍기 연산에서 marks의 글자를 들어낼 수 있는가(쪽에 바로 놓였거나 한 번만 그려지는 양식 안에 있고, 글자 경계를 아는가)."""
    counts = show["counts"]
    if (show["stream"] != glyphs.PAGE and show["stream"] not in once) or counts is None:
        return False
    if show["unit"] is not None:
        return True
    cursor = 0
    for count in counts:
        if count:
            inside = sum(1 for offset in range(count) if cursor + offset in marks)
            if 0 < inside < count:
                return False
            cursor += count
    return True


def sound(page, sheet):
    """쪽의 글자 찍기 연산자 수가 읽은 것과 같은가. 다르면 그 쪽은 고칠 수 없다."""
    try:
        instructions = pikepdf.parse_content_stream(page)
    except Exception:
        return False
    return sum(1 for instruction in instructions if str(instruction.operator) in SHOWS) == sheet.totals.get(glyphs.PAGE)

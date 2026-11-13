"""PDF에 든 짜임 꼬리표(구조 트리)를 읽는다: 내용 조각(쪽, MCID)이 문단인지, 목록인지, 표의 칸인지, 그림인지.

집행위원회 문서는 거의 모두 꼬리표가 있다. 꼬리표가 없는 PDF에서는 빈 것을 돌려준다.
"""

import pikepdf

STANDARD = frozenset("""Document Part Art Sect Div BlockQuote Caption TOC TOCI Index NonStruct Private P H H1 H2 H3 H4 H5 H6
L LI Lbl LBody Table TR TH TD THead TBody TFoot Span Quote Note Reference BibEntry Code Link Annot Ruby Warichu
Figure Formula Form Footnote Title Aside DocumentFragment""".split())


class Tree:
    """elements는 문서의 차례대로 놓인 요소들: {"type", "parent", "marks": [(쪽, MCID), …]}. where는 {(쪽, MCID): 요소의 차례}."""

    def __init__(self):
        self.elements, self.where = [], {}

    def path(self, index):
        """뿌리에서 이 요소까지의 종류들."""
        out = []
        while index is not None:
            out.append(self.elements[index]["type"])
            index = self.elements[index]["parent"]
        return out[::-1]

    def kinds(self, page, mcid):
        """내용 조각이 속한 요소의 종류들(뿌리에서부터). 꼬리표가 없으면 빈 것."""
        index = self.where.get((page, mcid))
        return self.path(index) if index is not None else []


def _role(name, roles):
    for _ in range(6):
        if name in STANDARD or name not in roles:
            break
        name = roles[name]
    return name


def read(pdf):
    """pikepdf로 연 문서의 구조 트리."""
    tree = Tree()
    root = pdf.Root.get("/StructTreeRoot")
    if root is None or "/K" not in root:
        return tree
    roles = {str(key)[1:]: str(value)[1:] for key, value in (root.get("/RoleMap") or {}).items()}
    numbers = {page.objgen: number for number, page in enumerate(pdf.pages)}
    seen, stack = set(), [(root.K, None, None)]
    while stack:
        node, parent, page = stack.pop()
        if isinstance(node, pikepdf.Array):
            stack.extend((kid, parent, page) for kid in reversed(list(node)))
            continue
        if isinstance(node, int):
            if parent is not None and page is not None:
                tree.elements[parent]["marks"].append((page, node))
                tree.where.setdefault((page, node), parent)
            continue
        if not isinstance(node, pikepdf.Dictionary):
            continue
        if "/Pg" in node:
            page = numbers.get(node.Pg.objgen, page)
        kind = node.get("/Type")
        if kind == pikepdf.Name("/MCR"):
            if parent is not None and page is not None and "/MCID" in node and "/Stm" not in node:
                tree.elements[parent]["marks"].append((page, int(node.MCID)))
                tree.where.setdefault((page, int(node.MCID)), parent)
            continue
        if kind == pikepdf.Name("/OBJR") or "/S" not in node:
            continue
        if node.is_indirect:
            if node.objgen in seen:
                continue
            seen.add(node.objgen)
        tree.elements.append({"type": _role(str(node.S)[1:], roles), "parent": parent, "marks": []})
        if "/K" in node:
            stack.append((node.K, len(tree.elements) - 1, page))
    return tree

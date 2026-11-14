// 두 글을 낱말 단위로 견줘 달라진 낱말을 찾는다. '달라진 곳 보기'가 옛 문단과 새 문단에서 달라진 말에 표시를 하는 데 쓴다.
// 화면 요소를 다루지 않으므로 node로 시험한다(tests/test_sitejs.py).
//
// wordDiff(옛 글, 새 글) → { old: [[글, 달라졌는가]], new: [[글, 달라졌는가]] }
//   조각을 차례대로 이으면 원래 글이 된다. 달라진 낱말이 이웃해 있으면 그 사이의 띄어쓰기까지 한 조각으로 묶는다.
//   글이 너무 길어 셈이 무거우면 견주지 않고 통째로 '달라지지 않은 조각'으로 돌려준다(표시 없이 나란히 보여 주게 된다).

const LIMIT = 600000;  // (옛 낱말 수 × 새 낱말 수)가 이보다 크면 견주지 않는다

const words = (text) => String(text || "").split(/(\s+)/).filter((piece) => piece !== "");
const isSpace = (piece) => /^\s+$/.test(piece);

// 두 낱말 줄에서 가장 긴 공통 부분열에 든 낱말의 자리를 찾는다: [옛 줄에서 남는 자리들, 새 줄에서 남는 자리들]
function kept(a, b) {
  const n = a.length;
  const m = b.length;
  const table = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }
  const inA = new Set();
  const inB = new Set();
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      inA.add(i);
      inB.add(j);
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) i += 1;
    else j += 1;
  }
  return [inA, inB];
}

// 낱말과 띄어쓰기의 조각들을 [글, 달라졌는가]의 줄로 묶는다. same은 달라지지 않은 낱말의 차례(낱말만 센 것)다.
function runs(pieces, same) {
  const found = [];
  let at = 0;          // 낱말만 센 차례
  let gap = "";        // 아직 붙이지 않은 띄어쓰기
  for (const piece of pieces) {
    if (isSpace(piece)) {
      gap += piece;
      continue;
    }
    const changed = !same.has(at);
    at += 1;
    const last = found[found.length - 1];
    if (last && last[1] === changed) last[0] += gap + piece;   // 같은 갈래가 이어지면 띄어쓰기까지 한 조각으로
    else if (gap && last && !last[1]) {                        // 갈래가 바뀌는 곳의 띄어쓰기는 달라지지 않은 쪽에 붙인다
      last[0] += gap;
      found.push([piece, changed]);
    } else if (gap && !changed) found.push([gap + piece, false]);
    else {
      if (gap) found.push([gap, false]);
      found.push([piece, changed]);
    }
    gap = "";
  }
  if (gap) {
    if (found.length) found[found.length - 1][0] += gap; else found.push([gap, false]);
  }
  return found;
}

export function wordDiff(before, after) {
  const a = words(before);
  const b = words(after);
  const wordsA = a.filter((piece) => !isSpace(piece));
  const wordsB = b.filter((piece) => !isSpace(piece));
  if (!wordsA.length || !wordsB.length || wordsA.length * wordsB.length > LIMIT) {
    return { old: before ? [[String(before), false]] : [], new: after ? [[String(after), false]] : [], skipped: Boolean(wordsA.length && wordsB.length) };
  }
  const [sameA, sameB] = kept(wordsA, wordsB);
  return { old: runs(a, sameA), new: runs(b, sameB), skipped: false };
}

// 📄 src/utils/circledOptions.js
// question_with_options에 ①②③④⑤(⑥⑦⑧⑨⑩) 객관식 선택지가 2개 이상 있으면 파싱해서
// [{ label: '①', text: '...' }, ...] 로 반환. 없으면 null.
// (채점은 백엔드가 이 라벨 문자 그대로 비교하므로 절대 다른 값으로 바꾸면 안 됨)
const CIRCLED_MARKER = /[①②③④⑤⑥⑦⑧⑨⑩]/g
const CANON_ORDER = '①②③④⑤⑥⑦⑧⑨⑩'

/**
 * ① 이전에 나오는 수식·조건 텍스트를 추출. 없거나 중복이면 null.
 * questionText를 넘기면 두 가지 중복을 방어한다:
 *   1) questionText에 display math($$, \[)가 있으면 수식이 QuizStem에서 이미 보임 → null
 *   2) 프리앰블이 questionText로 시작하면 그 부분을 제거해 순수 수식만 반환
 */
export function parseOptionPreamble(text, questionText = '') {
  if (!text) return null
  // question_text에 display math가 있으면 수식이 이미 렌더링됨 → 중복 방지
  if (questionText && (/\$\$/.test(questionText) || /\\\[/.test(questionText))) return null
  const m = text.match(/[①②③④⑤⑥⑦⑧⑨⑩]/)
  if (!m || m.index === 0) return null
  let preamble = text.slice(0, m.index).trim()
  if (!preamble) return null
  // question_text와 동일한 앞부분 제거 (question_with_options가 question_text를 포함하는 경우)
  const qt = questionText.trim()
  if (qt && preamble.startsWith(qt)) {
    preamble = preamble.slice(qt.length).trim()
  }
  return preamble || null
}

export function parseCircledOptions(text) {
  if (!text) return null

  const raw = [...text.matchAll(CIRCLED_MARKER)].map((m, i, arr) => {
    const label = m[0]
    const start = m.index + label.length
    const end = i + 1 < arr.length ? arr[i + 1].index : text.length
    return { label, text: text.slice(start, end).trim(), pos: m.index }
  })
  if (raw.length < 2) return null

  // 데이터 복구 과정에서 정답 라벨이 한 번 더 끼어들어 같은 라벨이 중복되는 경우가 있음
  // (예: "① ② ③ ④ ⑤ ④" 처럼 끝에 정답이 다시 붙음). 라벨별로 후보를 모아두고,
  // 정상적인 ①②③④⑤ 순서를 깨지 않는 후보 중 텍스트가 있는 쪽을 채택해서 중복을 제거한다.
  const byLabel = new Map()
  for (const item of raw) {
    if (!byLabel.has(item.label)) byLabel.set(item.label, [])
    byLabel.get(item.label).push(item)
  }

  const labelsPresent = [...byLabel.keys()].sort(
    (a, b) => CANON_ORDER.indexOf(a) - CANON_ORDER.indexOf(b),
  )

  const result = []
  let lastPos = -1
  for (const label of labelsPresent) {
    const candidates = byLabel.get(label)
    const inOrder = candidates.filter((c) => c.pos > lastPos)
    const pick = inOrder.find((c) => c.text) || inOrder[0] || candidates.find((c) => c.text) || candidates[0]
    result.push({ label: pick.label, text: pick.text })
    lastPos = pick.pos
  }
  return result
}

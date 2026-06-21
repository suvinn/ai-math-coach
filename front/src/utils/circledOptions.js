// 📄 src/utils/circledOptions.js
// question_with_options에 ①②③④⑤(⑥⑦⑧⑨⑩) 객관식 선택지가 2개 이상 있으면 파싱해서
// [{ label: '①', text: '...' }, ...] 로 반환. 없으면 null.
// (채점은 백엔드가 이 라벨 문자 그대로 비교하므로 절대 다른 값으로 바꾸면 안 됨)
const CIRCLED_MARKER = /[①②③④⑤⑥⑦⑧⑨⑩]/g

export function parseCircledOptions(text) {
  if (!text) return null
  const markers = [...text.matchAll(CIRCLED_MARKER)]
  if (markers.length < 2) return null
  return markers.map((m, i) => {
    const label = m[0]
    const start = m.index + label.length
    const end = i + 1 < markers.length ? markers[i + 1].index : text.length
    return { label, text: text.slice(start, end).trim() }
  })
}

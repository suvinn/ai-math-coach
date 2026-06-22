// 📄 src/utils/difficulty.js
// 난이도 배지 색 톤. 하=positive(녹색) 중=cautionary(주황) 상=negative(빨강)
const TONE_BY_DIFFICULTY = { 하: 'positive', 중: 'cautionary', 상: 'negative' }

export function difficultyTone(difficulty) {
  return TONE_BY_DIFFICULTY[difficulty] || 'neutral'
}

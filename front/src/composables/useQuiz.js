// 📄 src/composables/useQuiz.js
import { ref, computed } from 'vue'

// proto-core.jsx의 useQuiz 훅을 Vue composable로 변환.
// 한 문항의 select → 제출(reveal) → 다음(onNext) 2단계 상태를 관리.
//
// 사용 예:
//   const q = useQuiz()
//   q.pick(i)        // 선택지 선택
//   q.reveal()       // 제출 (정답 공개)
//   q.stateFor(i, answerIndex)  // 선택지 i의 상태 클래스
//   q.reset()        // 다음 문항으로 넘어갈 때 초기화
export function useQuiz() {
  const picked = ref(null)
  const revealed = ref(false)

  function pick(i) {
    if (!revealed.value) picked.value = i
  }

  function reveal() {
    if (picked.value !== null) revealed.value = true
  }

  function reset() {
    picked.value = null
    revealed.value = false
  }

  // 선택지 i가 가져야 할 상태: '' | 'selected' | 'correct' | 'wrong'
  // answerIndex: 정답 선택지 index
  function stateFor(i, answerIndex) {
    if (revealed.value) {
      if (i === answerIndex) return 'correct'
      if (i === picked.value) return 'wrong'
      return ''
    }
    return picked.value === i ? 'selected' : ''
  }

  // 정답 여부 (answerIndex 기준)
  function isCorrect(answerIndex) {
    return picked.value === answerIndex
  }

  const hasPicked = computed(() => picked.value !== null)

  return { picked, revealed, hasPicked, pick, reveal, reset, stateFor, isCorrect }
}
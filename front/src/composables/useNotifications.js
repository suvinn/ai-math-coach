// 📄 src/composables/useNotifications.js
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useQuizStore } from '@/stores/quiz'

const STORAGE_KEY = 'suql_notification_read'

// 읽음 상태 localStorage 헬퍼
function loadRead() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

function saveRead(set) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]))
}

export function useNotifications() {
  const auth = useAuthStore()
  const quiz = useQuizStore()

  // 읽음 ID 셋 (reactive ref로 감싸서 변경 감지 가능하게)
  const readIds = ref(loadRead())

  // ── 알림 목록 생성 ──────────────────────────────────────────
  // 각 알림은 { id, type, message, actionLabel?, actionRoute? }
  const notifications = computed(() => {
    const list = []

    // 1. 오답 루프 중단 알림
    //    reviewSubtypes가 있고 아직 완료하지 않은 경우
    const hasUnfinishedReview =
      quiz.reviewSubtypes.length > 0 &&
      quiz.reviewSubtypeIdx < quiz.reviewSubtypes.length

    if (hasUnfinishedReview) {
      list.push({
        id:          'review_loop',
        type:        'review',
        icon:        '📝',
        message:     '현재 오답 루프를 풀다 중단됐어요. 다시 이어서 풀어볼까요?',
        actionLabel: '이어서 풀기',
        actionRoute: '/quiz/review',
      })
    }

    // 2. 연속 학습일 (streak) 알림
    //    auth.user에 streak 필드가 있으면 사용, 없으면 숨김
    const streak = auth.user?.streak ?? auth.user?.consecutive_days ?? null
    if (streak != null && streak > 0) {
      list.push({
        id:      `streak_${streak}`,
        type:    'streak',
        icon:    '🔥',
        message: `오늘은 ${streak}일째 연속 학습 중! 오늘도 힘내봅시다.`,
      })
    }

    // 3. 오늘의 추천 유형 알림
    //    quiz.reviewSubtypes[0] 이 있으면 첫 번째 약점 유형을 추천으로 표시
    //    (세션이 아직 없어도 recommendedSubtype 필드가 있으면 활용)
    const topSubtype =
      quiz.reviewSubtypes[0]?.problemSubtype ??
      auth.user?.recommended_subtype ??
      null

    if (topSubtype) {
      list.push({
        id:          `rec_${topSubtype}`,
        type:        'recommendation',
        icon:        '✨',
        message:     `오늘의 추천 유형은 [${topSubtype}]입니다.`,
        actionLabel: '바로 풀기',
        actionRoute: '/quiz/setup',
      })
    }

    return list
  })

  // ── 읽음 처리 ───────────────────────────────────────────────
  function markRead(id) {
    const next = new Set(readIds.value)
    next.add(id)
    readIds.value = next
    saveRead(next)
  }

  function markAllRead() {
    const next = new Set(notifications.value.map((n) => n.id))
    readIds.value = next
    saveRead(next)
  }

  // ── 파생 상태 ───────────────────────────────────────────────
  const unreadNotifications = computed(() =>
    notifications.value.filter((n) => !readIds.value.has(n.id))
  )

  const hasUnread = computed(() => unreadNotifications.value.length > 0)

  function isRead(id) {
    return readIds.value.has(id)
  }

  // quiz store가 초기화되거나 사용자가 바뀌면 읽음 목록도 새로 로드
  watch(() => auth.user?.username, () => {
    readIds.value = loadRead()
  })

  return {
    notifications,
    unreadNotifications,
    hasUnread,
    isRead,
    markRead,
    markAllRead,
  }
}
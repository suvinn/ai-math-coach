<!-- 📄 src/views/quiz/QuizResultView.vue -->
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import api, { unwrap } from '@/api'
import FocusShell from '@/components/common/FocusShell.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import WeakRow from '@/components/common/WeakRow.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import InlineTex from '@/components/common/InlineTex.vue'

const router = useRouter()
const quiz = useQuizStore()

if (!quiz.submitResult) {
  router.replace('/')
}

const result = computed(() => quiz.submitResult)
const pct = computed(() => Math.round((result.value?.accuracy || 0) * 100))
const allCorrect = computed(() => result.value && result.value.score === result.value.total)

const tones = ['var(--status-negative)', 'var(--status-cautionary)', 'var(--label-assistive)']

const weakSubtypes = computed(() => {
  if (!result.value || allCorrect.value) return []
  const stats = {}
  for (const r of result.value.results) {
    const s = (stats[r.problem_subtype] ||= { wrong: 0, total: 0 })
    s.total += 1
    if (!r.is_correct) s.wrong += 1
  }
  return Object.entries(stats)
    .filter(([, s]) => s.wrong > 0)
    .sort((a, b) => b[1].wrong / b[1].total - a[1].wrong / a[1].total)
    .slice(0, 3)
    .map(([subtype, s], i) => ({
      rank: i + 1,
      name: subtype,
      pct: Math.round(((s.total - s.wrong) / s.total) * 100),
      tone: tones[i],
    }))
})

// 모달
const modalOpen = ref(false)
const modalProblem = ref(null)
const modalResult = ref(null)

async function openModal(r) {
  modalResult.value = r
  modalOpen.value = true
  modalProblem.value = null
  try {
    const data = unwrap(await api.get(`/problems/${r.problem_id}`))
    modalProblem.value = data
  } catch {
    // 실패해도 모달은 열림
  }
}

function closeModal() {
  modalOpen.value = false
  modalResult.value = null
  modalProblem.value = null
}
</script>

<template>
  <FocusShell title="결과" :back="false">
    <div v-if="result" class="stack-16 result-body">
      <div class="result-hero">
        <ScoreRing :pct="pct" :label="`${result.score} / ${result.total} 문제`" />
      </div>

      <div v-if="allCorrect" class="verdict" data-ok="true">
        🎉 전부 맞혔어요! 다음 단계로 넘어가볼까요?
      </div>

      <div v-else class="stack-12">
        <div class="wds-label-1" style="font-weight: 700">놓친 유형</div>
        <div class="stack-16">
          <WeakRow
            v-for="w in weakSubtypes"
            :key="w.name"
            :rank="w.rank"
            :name="w.name"
            :pct="w.pct"
            :tone="w.tone"
          />
        </div>

        <div class="wds-label-1" style="font-weight: 700; margin-top: 8px">틀린 문제</div>
        <div class="stack-8">
          <div
            v-for="r in result.results.filter(r => !r.is_correct)"
            :key="r.problem_id"
            class="wrong-item"
          >
            <span class="wds-body-2 wrong-text">{{ r.problem_subtype }}</span>
            <div style="display:flex; gap:8px;">
              <button class="comment-btn" @click="openModal(r)">
                <WdsIcon name="message" :size="13" color="var(--suql-accent)" />
                해설 보기
              </button>
              <button class="comment-btn" @click="router.push(`/problems/${r.problem_id}/posts`)">
                <WdsIcon name="nav-mypage" :size="13" color="var(--suql-accent)" />
                토론
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #foot>
      <div class="play-foot">
        <WdsButton variant="secondary" size="large" @click="router.push('/')">
          홈으로
        </WdsButton>
        <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="router.push('/quiz/coaching')">
          AI 코칭 보러가기
        </WdsButton>
      </div>
    </template>
  </FocusShell>

  <!-- 해설 모달 -->
  <Teleport to="body">
    <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
      <div class="modal-sheet">
        <div class="modal-head">
          <span class="wds-label-1" style="font-weight:700">해설 보기</span>
          <button class="modal-close" @click="closeModal">
            <WdsIcon name="close" :size="18" />
          </button>
        </div>

        <div class="modal-body">
          <!-- 문제 본문 -->
          <div class="modal-section">
            <div class="modal-label">문제</div>
            <div v-if="modalProblem" class="modal-text">
              <InlineTex :text="modalProblem.question_text" />
            </div>
            <div v-else class="assistive" style="text-align:center; padding:8px 0">불러오는 중…</div>
          </div>

          <!-- 내 답 / 정답 -->
          <div class="modal-row">
            <div class="modal-section">
              <div class="modal-label">내 답</div>
              <div class="modal-answer wrong-color">{{ modalResult?.user_answer }}</div>
            </div>
            <div class="modal-section">
              <div class="modal-label">정답</div>
              <div class="modal-answer correct-color">{{ modalResult?.grading_answer }}</div>
            </div>
          </div>

          <!-- 해설 -->
          <div class="modal-section">
            <div class="modal-label">해설</div>
            <div class="modal-explain">
              <InlineTex :text="modalResult?.explanation" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.result-body {
  align-items: center;
  text-align: center;
}
.result-hero {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.result-body .stack-12 {
  width: 100%;
  text-align: left;
}
.play-foot {
  display: flex;
  gap: 10px;
}
.wrong-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--fill-alternative);
}
.wrong-text {
  color: var(--label-normal);
  flex: 1;
}
.comment-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  color: var(--suql-accent);
  cursor: pointer;
  white-space: nowrap;
}

/* 모달 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}
.modal-sheet {
  width: 100%;
  max-width: 480px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--background-normal-normal, #fff);
  border-radius: 20px;
  padding: 20px 20px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--label-alternative);
  padding: 4px;
}
.modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.modal-row {
  display: flex;
  gap: 12px;
}
.modal-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.modal-label {
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  color: var(--label-assistive);
}
.modal-text {
  font: var(--weight-regular) 14px/1.6 var(--font-sans);
  color: var(--label-normal);
}
.modal-answer {
  font: var(--weight-bold) 16px/1 var(--font-sans);
}
.modal-explain {
  padding: 12px;
  border-radius: 12px;
  background: var(--fill-alternative);
  font: var(--weight-regular) 14px/1.7 var(--font-sans);
  color: var(--label-normal);
  white-space: pre-wrap;
}
.wrong-color { color: var(--status-negative); }
.correct-color { color: var(--status-positive); }
</style>
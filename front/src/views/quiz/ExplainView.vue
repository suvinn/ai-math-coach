<!-- 📄 src/views/review/ExplainView.vue -->
<!-- 해설 (B2): 보완 풀이 제출 후 틀린 문제의 해설을 보여준다.
     하단 CTA: "재도전하기" → RedoView  |  "질문하기" → ChatView -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import api, { unwrap } from '@/api'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import InlineTex from '@/components/common/InlineTex.vue'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

if (!quiz.sessionId) router.replace('/')

const loading      = ref(true)
const wrongProblems = ref([])   // [{ problem_id, question_text, user_answer, correct_answer, explanation, ... }]
const expanded     = ref({})    // { [problem_id]: boolean } — 해설 펼침 상태

onMounted(async () => {
  try {
    const data = unwrap(await api.get(`/quiz/sessions/${quiz.sessionId}/wrong-answers`))
    wrongProblems.value = data.wrong_problems || []
    // 첫 문제는 기본으로 펼쳐두기
    if (wrongProblems.value.length) {
      expanded.value[wrongProblems.value[0].problem_id] = true
    }
  } catch {
    showToast('해설을 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
})

const allCorrect = computed(() => !loading.value && wrongProblems.value.length === 0)

function toggle(id) {
  expanded.value[id] = !expanded.value[id]
}

function goChat(problem) {
  // ChatView에서 쓸 수 있도록 quiz store에 문제 정보 저장
  quiz.chatContext = { sessionId: quiz.sessionId, problem }
  router.push('/review/chat')
}

function goRedo() {
  router.push('/review/redo')
}
</script>

<template>
  <FocusShell title="해설" :toast="toast" @back="router.push('/review/play')">

    <div v-if="loading" class="center-msg assistive">해설을 불러오는 중…</div>

    <div v-else-if="allCorrect" class="center-msg">
      <div class="all-correct-ico">🎉</div>
      <div class="wds-headline-2" style="font-weight:700">보완 풀이 완료!</div>
      <div class="wds-body-2 assistive">이번엔 모두 맞혔어요. 재도전으로 마무리해볼까요?</div>
    </div>

    <div v-else class="stack-16">
      <div class="wds-body-2 assistive">
        틀린 <strong style="color:var(--label-normal)">{{ wrongProblems.length }}문제</strong>의 해설이에요.
        꼼꼼히 읽고 재도전해보세요.
      </div>

      <div v-for="p in wrongProblems" :key="p.problem_id" class="explain-card">
        <!-- 문제 헤더 (항상 표시) -->
        <button class="explain-header" @click="toggle(p.problem_id)">
          <div style="flex:1; text-align:left">
            <div class="wds-caption-2 assistive" style="margin-bottom:4px">{{ p.problem_subtype }}</div>
            <div class="wds-label-1 explain-q"><InlineTex :text="p.question_text" /></div>
          </div>
          <WdsIcon
            :name="expanded[p.problem_id] ? 'chevron-up' : 'chevron-down'"
            :size="18"
            color="var(--label-assistive)"
            style="flex:none"
          />
        </button>

        <!-- 정오답 + 해설 (펼쳤을 때) -->
        <div v-if="expanded[p.problem_id]" class="explain-body stack-12">
          <div class="answer-row">
            <span class="answer-chip wrong">내 답 {{ p.user_answer || '미제출' }}</span>
            <span class="answer-chip correct">정답 {{ p.correct_answer }}</span>
          </div>
          <div class="explain-text wds-body-2">
            <InlineTex :text="p.explanation" />
          </div>
          <button class="chat-btn" @click="goChat(p)">
            <WdsIcon name="sparkle" :size="15" color="var(--suql-accent)" />
            <span class="wds-caption-1" style="color:var(--suql-accent); font-weight:600">AI에게 질문하기</span>
          </button>
        </div>
      </div>
    </div>

    <template #foot>
      <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="goRedo">
        재도전하기
      </WdsButton>
    </template>
  </FocusShell>
</template>

<style scoped>
.center-msg {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 60px 0; text-align: center;
}
.all-correct-ico { font-size: 48px; }

.explain-card {
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
  overflow: hidden;
}
.explain-header {
  width: 100%; display: flex; align-items: flex-start; gap: 12px;
  padding: 16px; background: none; border: none; cursor: pointer;
}
.explain-header:hover { background: var(--fill-alternative); }
.explain-q {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; line-height: 1.5;
}
.explain-body {
  padding: 0 16px 16px;
  border-top: 1px solid var(--line-normal-normal);
}
.answer-row { display: flex; gap: 8px; padding-top: 12px; }
.answer-chip {
  padding: 4px 10px; border-radius: 99px;
  font: var(--weight-semibold) 12px/1 var(--font-sans);
}
.answer-chip.wrong   { background: var(--red-99,#fff0f0);   color: var(--status-negative); }
.answer-chip.correct { background: var(--green-99,#f0fff4); color: var(--status-positive); }
.explain-text {
  padding: 12px; background: var(--fill-alternative); border-radius: 12px;
  line-height: 1.7; white-space: pre-wrap;
}
.chat-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-radius: 10px; border: none; background: var(--blue-99);
  cursor: pointer; align-self: flex-start;
}
.chat-btn:hover { background: var(--blue-95, #e8f0ff); }
</style>